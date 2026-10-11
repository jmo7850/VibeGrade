"""Docker sandbox for secure runtime verification.

This service orchestrates Docker containers to run untrusted build/test commands
with strict resource limits and isolation.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.profiler import ProjectProfile
from app.services.verification import VerificationResult, VerificationStatus

logger = get_logger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    image: str = "vibegrade/sandbox:latest"
    cpu_limit: float = 2.0
    memory_limit: str = "2g"
    pids_limit: int = 100
    timeout_seconds: int = 120
    network_disabled: bool = True
    read_only_rootfs: bool = True
    user: str = "10001:10001"  # non-root user
    cap_drop: list[str] = None

    def __post_init__(self):
        if self.cap_drop is None:
            self.cap_drop = ["ALL"]


@dataclass
class SandboxExecutionResult:
    """Result of a sandbox command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    oom_killed: bool = False


class DockerSandbox:
    """Manages Docker containers for secure command execution."""

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.settings = get_settings()
        self._client: docker.DockerClient | None = None
        self._container = None
        self._docker_available: bool | None = None

    @classmethod
    def is_docker_available(cls) -> bool:
        """Check if Docker daemon is available."""
        try:
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def _get_client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def _check_docker_available(self) -> bool:
        """Check if Docker is available, cache result."""
        if self._docker_available is None:
            self._docker_available = self.is_docker_available()
            if not self._docker_available:
                logger.warning("Docker daemon not available; sandbox execution will fail")
        return self._docker_available

    def _ensure_image(self) -> None:
        """Ensure the sandbox image exists, build if needed."""
        if not self._check_docker_available():
            raise RuntimeError("Docker daemon not available")

        client = self._get_client()
        try:
            client.images.get(self.config.image)
        except ImageNotFound:
            logger.info("Building sandbox image", image=self.config.image)
            self._build_image()

    def _build_image(self) -> None:
        """Build the sandbox Docker image."""
        client = self._get_client()
        sandbox_dir = Path(__file__).parent.parent / "sandbox"
        dockerfile = sandbox_dir / "Dockerfile"

        if not dockerfile.exists():
            raise RuntimeError(f"Dockerfile not found at {dockerfile}")

        try:
            client.images.build(
                path=str(sandbox_dir),
                tag=self.config.image,
                rm=True,
                forcerm=True,
            )
            logger.info("Sandbox image built successfully", image=self.config.image)
        except DockerException as e:
            logger.error("Failed to build sandbox image", error=str(e))
            raise

    def _create_container(self, workspace_path: Path, env: dict[str, str] | None = None):
        """Create a sandbox container with security configuration."""
        client = self._get_client()

        # Prepare environment
        container_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/home/scanner",
            "LANG": "C.UTF-8",
        }
        if env:
            container_env.update(env)

        # Security options
        security_opt = ["no-new-privileges:true"]

        # Resource limits
        host_config = client.api.create_host_config(
            cpu_quota=int(self.config.cpu_limit * 100000),
            cpu_period=100000,
            mem_limit=self.config.memory_limit,
            memswap_limit=self.config.memory_limit,  # Disable swap
            pids_limit=self.config.pids_limit,
            read_only=self.config.read_only_rootfs,
            user=self.config.user,
            cap_drop=self.config.cap_drop,
            security_opt=security_opt,
            network_mode="none" if self.config.network_disabled else "bridge",
            tmpfs={"/tmp": "rw,noexec,nosuid,size=100m"},
            ulimits=[
                docker.types.Ulimit(name="cpu", soft=120, hard=120),
                docker.types.Ulimit(name="fsize", soft=10*1024*1024, hard=10*1024*1024),
                docker.types.Ulimit(name="nproc", soft=self.config.pids_limit, hard=self.config.pids_limit),
            ],
        )

        # Volume mount for workspace (read-write for build artifacts)
        volumes = {
            str(workspace_path): {"bind": "/workspace", "mode": "rw"},
        }

        container = client.api.create_container(
            image=self.config.image,
            command=["sleep", "infinity"],  # Keep container running
            environment=container_env,
            host_config=host_config,
            volumes=volumes,
            working_dir="/workspace",
            user=self.config.user,
        )

        return container

    async def start(self, workspace_path: Path, env: dict[str, str] | None = None) -> None:
        """Start the sandbox container."""
        self._ensure_image()
        client = self._get_client()

        container_obj = self._create_container(workspace_path, env)
        self._container = client.api.start(container_obj["Id"])
        logger.info("Sandbox container started", container_id=self._container["Id"][:12])

    async def stop(self) -> None:
        """Stop and remove the sandbox container."""
        if self._container:
            client = self._get_client()
            try:
                container = client.api
                container.stop(self._container["Id"], timeout=5)
                container.remove_container(self._container["Id"], force=True)
                logger.info("Sandbox container stopped", container_id=self._container["Id"][:12])
            except DockerException as e:
                logger.warning("Error stopping sandbox container", error=str(e))
            finally:
                self._container = None

    async def execute(
        self,
        command: list[str],
        workspace_path: Path,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxExecutionResult:
        """Execute a command in the sandbox container."""
        if self._container is None:
            await self.start(workspace_path, env)

        timeout = timeout or self.config.timeout_seconds
        start = time.time()
        client = self._get_client()

        try:
            # Create exec instance
            exec_instance = client.api.exec_create(
                self._container["Id"],
                command,
                environment=env or {},
                user=self.config.user,
                workdir="/workspace",
            )

            # Start exec with timeout
            exec_id = exec_instance["Id"]
            output = []

            async def read_output():
                for chunk in client.api.exec_start(exec_id, stream=True, demux=True):
                    if chunk[0]:  # stdout
                        output.append(("stdout", chunk[0]))
                    if chunk[1]:  # stderr
                        output.append(("stderr", chunk[1]))

            # Wait for completion with timeout
            try:
                await asyncio.wait_for(read_output(), timeout=timeout)
            except TimeoutError:
                # Kill the exec process
                try:
                    client.api.exec_resize(exec_id, height=0, width=0)  # Signal termination
                except DockerException:
                    pass
                duration_ms = int((time.time() - start) * 1000)
                stdout = b"".join(o[1] for o in output if o[0] == "stdout").decode("utf-8", errors="ignore")
                stderr = b"".join(o[1] for o in output if o[0] == "stderr").decode("utf-8", errors="ignore")
                return SandboxExecutionResult(
                    command=" ".join(command),
                    exit_code=-1,
                    stdout=stdout,
                    stderr=stderr + f"\nCommand timed out after {timeout}s",
                    duration_ms=duration_ms,
                    timed_out=True,
                )

            # Get exit code
            exec_inspect = client.api.exec_inspect(exec_id)
            exit_code = exec_inspect.get("ExitCode", -1)

            duration_ms = int((time.time() - start) * 1000)
            stdout = b"".join(o[1] for o in output if o[0] == "stdout").decode("utf-8", errors="ignore")
            stderr = b"".join(o[1] for o in output if o[0] == "stderr").decode("utf-8", errors="ignore")

            return SandboxExecutionResult(
                command=" ".join(command),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except DockerException as e:
            logger.error("Docker execution error", error=str(e))
            duration_ms = int((time.time() - start) * 1000)
            return SandboxExecutionResult(
                command=" ".join(command),
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )


class SandboxVerificationEngine:
    """Verification engine that runs commands in Docker sandbox."""

    def __init__(
        self,
        workspace: Path,
        profile: ProjectProfile,
        config: SandboxConfig | None = None,
    ):
        self.workspace = workspace
        self.profile = profile
        self.config = config or SandboxConfig()
        self.sandbox = DockerSandbox(self.config)

    async def run_all(self) -> list[VerificationResult]:
        """Run all verification steps in the sandbox."""
        results = []

        # Check if Docker is available
        if not self.sandbox._check_docker_available():
            logger.warning("Docker not available; skipping sandbox verification")
            return self._create_skipped_results()

        try:
            # Start sandbox
            await self.sandbox.start(self.workspace)

            # Install dependencies
            for cmd in self.profile.install_commands:
                result = await self._run_command(f"install: {cmd}", cmd)
                results.append(result)
                if result.exit_code != 0:
                    logger.warning("Install failed, stopping", command=cmd)
                    break

            # Build
            for cmd in self.profile.build_commands:
                result = await self._run_command(f"build: {cmd}", cmd)
                results.append(result)
                if result.exit_code != 0:
                    logger.warning("Build failed", command=cmd)
                    # Continue to tests anyway

            # Test
            for cmd in self.profile.test_commands:
                result = await self._run_command(f"test: {cmd}", cmd)
                results.append(result)

        except RuntimeError as e:
            if "Docker daemon not available" in str(e):
                logger.warning("Docker not available during execution; marking remaining as skipped")
                results.extend(self._create_skipped_results(len(results)))
            else:
                raise
        finally:
            await self.sandbox.stop()

        return results

    def _create_skipped_results(self, start_index: int = 0) -> list[VerificationResult]:
        """Create skipped results for all verification commands."""
        results = []
        all_commands = []
        all_commands.extend(self.profile.install_commands)
        all_commands.extend(self.profile.build_commands)
        all_commands.extend(self.profile.test_commands)

        for i, cmd in enumerate(all_commands[start_index:], start=start_index):
            prefix = ""
            if i < len(self.profile.install_commands):
                prefix = "install: "
            elif i < len(self.profile.install_commands) + len(self.profile.build_commands):
                prefix = "build: "
            else:
                prefix = "test: "

            results.append(VerificationResult(
                name=f"{prefix}{cmd}",
                command=cmd,
                status=VerificationStatus.SKIPPED,
                exit_code=None,
                stdout="",
                stderr="Docker daemon not available; sandbox execution skipped",
                duration_ms=0,
                parsed_output=None,
            ))
        return results

    async def _run_command(self, name: str, command: str) -> VerificationResult:
        """Run a single command in the sandbox."""
        start = time.time()
        logger.info("Running sandbox command", name=name, command=command)

        # Parse command into list for exec
        cmd_list = command.split()

        result = await self.sandbox.execute(cmd_list, self.workspace, timeout=self.config.timeout_seconds)

        duration_ms = int((time.time() - start) * 1000)

        status = VerificationStatus.PASSED if result.exit_code == 0 else VerificationStatus.FAILED
        if result.timed_out:
            status = VerificationStatus.ERROR

        # Parse test output
        parsed = self._parse_test_output(result.stdout, result.stderr, command)

        return VerificationResult(
            name=name,
            command=command,
            status=status,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            parsed_output=parsed,
        )

    def _parse_test_output(self, stdout: str, stderr: str, command: str) -> dict[str, Any]:
        """Parse test output for summary statistics."""
        import re

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
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+skipped", output)
            if match:
                parsed["tests_skipped"] = int(match.group(1))
            match = re.search(r"TOTAL.*?(\d+)%", output)
            if match:
                parsed["coverage_percent"] = float(match.group(1))

        # Cargo test
        if "cargo test" in command:
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))

        # Go test
        if "go test" in command:
            pass_count = len(re.findall(r"^--- PASS:", output, re.MULTILINE))
            fail_count = len(re.findall(r"^--- FAIL:", output, re.MULTILINE))
            parsed["tests_passed"] = pass_count
            parsed["tests_failed"] = fail_count

        parsed["tests_run"] = parsed["tests_passed"] + parsed["tests_failed"] + parsed["tests_skipped"]
        return parsed


async def create_sandbox_verification_engine(
    workspace: Path,
    profile: ProjectProfile,
) -> SandboxVerificationEngine:
    """Factory function to create sandbox verification engine."""
    settings = get_settings()
    config = SandboxConfig(
        image=settings.sandbox_docker_image,
        cpu_limit=settings.sandbox_cpu_limit,
        memory_limit=settings.sandbox_memory_limit,
        pids_limit=settings.sandbox_pids_limit,
        timeout_seconds=settings.sandbox_timeout_seconds,
    )
    return SandboxVerificationEngine(workspace, profile, config)
