"""Verification engine for build and test execution."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.services.profiler import ProjectProfile

logger = get_logger(__name__)


class VerificationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class VerificationResult:
    name: str
    command: str
    status: VerificationStatus
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    parsed_output: dict[str, Any] = None


class VerificationEngine:
    """Runs build, test, and verification commands."""

    def __init__(self, workspace: Path, profile: ProjectProfile, timeout: int = 300):
        self.workspace = workspace
        self.profile = profile
        self.timeout = timeout

    async def run_all(self) -> list[VerificationResult]:
        """Run all verification steps."""
        results = []

        # Install
        for cmd in self.profile.install_commands:
            result = await self._run_command(f"install: {cmd}", cmd)
            results.append(result)
            if result.status == VerificationStatus.FAILED:
                logger.warning("Install failed, stopping", command=cmd)
                break

        # Build
        for cmd in self.profile.build_commands:
            result = await self._run_command(f"build: {cmd}", cmd)
            results.append(result)
            if result.status == VerificationStatus.FAILED:
                logger.warning("Build failed", command=cmd)
                # Continue to tests anyway

        # Test
        for cmd in self.profile.test_commands:
            result = await self._run_command(f"test: {cmd}", cmd)
            results.append(result)

        return results

    async def _run_command(self, name: str, command: str) -> VerificationResult:
        """Run a single command."""
        start = time.time()
        logger.info("Running verification command", name=name, command=command)

        try:
            # Use shell for complex commands
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self.workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            duration_ms = int((time.time() - start) * 1000)

            stdout_str = stdout.decode("utf-8", errors="ignore")
            stderr_str = stderr.decode("utf-8", errors="ignore")

            if process.returncode == 0:
                status = VerificationStatus.PASSED
            else:
                status = VerificationStatus.FAILED

            # Parse test output
            parsed = self._parse_test_output(stdout_str, stderr_str, command)

            return VerificationResult(
                name=name,
                command=command,
                status=status,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                parsed_output=parsed,
            )

        except TimeoutError:
            return VerificationResult(
                name=name,
                command=command,
                status=VerificationStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                duration_ms=self.timeout * 1000,
            )
        except Exception as e:
            return VerificationResult(
                name=name,
                command=command,
                status=VerificationStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    def _parse_test_output(self, stdout: str, stderr: str, command: str) -> dict[str, Any]:
        """Parse test output for summary statistics."""
        parsed = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "coverage_percent": None,
        }

        output = stdout + "\n" + stderr

        # Jest/Vitest
        if "test" in command and ("jest" in command or "vitest" in command or "npm test" in command):
            # Look for: Tests: 5 passed, 1 failed, 2 skipped
            import re
            match = re.search(r"Tests:\s+(\d+)\s+passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+skipped", output)
            if match:
                parsed["tests_skipped"] = int(match.group(1))

        # Pytest
        if "pytest" in command:
            import re
            # ===== 5 passed, 1 failed, 2 skipped in 1.23s =====
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+skipped", output)
            if match:
                parsed["tests_skipped"] = int(match.group(1))
            # Coverage
            match = re.search(r"TOTAL.*?(\d+)%", output)
            if match:
                parsed["coverage_percent"] = float(match.group(1))

        # Cargo test
        if "cargo test" in command:
            import re
            # test result: ok. 5 passed; 0 failed; 0 ignored
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))

        # Go test
        if "go test" in command:
            import re
            # PASS/FAIL lines
            pass_count = len(re.findall(r"^--- PASS:", output, re.MULTILINE))
            fail_count = len(re.findall(r"^--- FAIL:", output, re.MULTILINE))
            parsed["tests_passed"] = pass_count
            parsed["tests_failed"] = fail_count

        parsed["tests_run"] = parsed["tests_passed"] + parsed["tests_failed"] + parsed["tests_skipped"]
        return parsed
