"""Sandbox runner for secure runtime verification.

This script runs inside the sandbox container and executes
build, test, and verification commands with resource limits.
"""

import asyncio
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

# Resource limits
MAX_CPU_SECONDS = 120
MAX_MEMORY_MB = 2048
MAX_PROCESSES = 100
MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB


def set_resource_limits() -> None:
    """Set strict resource limits for the sandbox."""
    # CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
    # Memory limit (bytes)
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_MB * 1024 * 1024, MAX_MEMORY_MB * 1024 * 1024))
    # Process limit
    resource.setrlimit(resource.RLIMIT_NPROC, (MAX_PROCESSES, MAX_PROCESSES))
    # File size limit
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    # Disable core dumps
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


async def run_command(
    cmd: list[str],
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command in the sandbox with resource limits."""
    start = time.time()

    # Clean environment
    clean_env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": "/home/scanner",
        "LANG": "C.UTF-8",
    }
    if env:
        clean_env.update(env)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=clean_env,
            preexec_fn=lambda: set_resource_limits(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "duration_ms": int((time.time() - start) * 1000),
                "timed_out": True,
            }

        duration_ms = int((time.time() - start) * 1000)

        return {
            "command": " ".join(cmd),
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="ignore")[:MAX_OUTPUT_SIZE],
            "stderr": stderr.decode("utf-8", errors="ignore")[:MAX_OUTPUT_SIZE],
            "duration_ms": duration_ms,
            "timed_out": False,
        }

    except Exception as e:
        return {
            "command": " ".join(cmd),
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_ms": int((time.time() - start) * 1000),
            "timed_out": False,
        }


async def main() -> None:
    """Main entry point for the sandbox runner."""
    if len(sys.argv) < 2:
        print("Usage: sandbox_runner.py <command_json>", file=sys.stderr)
        sys.exit(1)

    # Parse command from JSON
    try:
        command_spec = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    cmd = command_spec.get("command", [])
    cwd = Path(command_spec.get("cwd", "/workspace"))
    timeout = command_spec.get("timeout", 120)
    env = command_spec.get("env", {})

    if not cmd:
        print("No command specified", file=sys.stderr)
        sys.exit(1)

    # Run the command
    result = await run_command(cmd, cwd, timeout, env)

    # Output result as JSON
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
