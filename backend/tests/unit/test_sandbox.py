"""Tests for the Docker sandbox service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.profiler import ProjectProfile
from app.services.sandbox import (
    DockerSandbox,
    SandboxConfig,
    SandboxExecutionResult,
    SandboxVerificationEngine,
)
from app.services.verification import VerificationStatus


class TestDockerSandbox:
    """Test Docker sandbox service."""

    def test_is_docker_available_false_when_no_docker(self):
        """Test that is_docker_available returns False when Docker is not available."""
        with patch("docker.from_env") as mock_from_env:
            mock_from_env.side_effect = Exception("Docker not found")
            assert DockerSandbox.is_docker_available() is False

    def test_is_docker_available_true_when_docker_works(self):
        """Test that is_docker_available returns True when Docker is available."""
        with patch("docker.from_env") as mock_from_env:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_from_env.return_value = mock_client
            assert DockerSandbox.is_docker_available() is True

    def test_check_docker_available_caches_result(self):
        """Test that _check_docker_available caches the result."""
        sandbox = DockerSandbox()
        with patch.object(DockerSandbox, "is_docker_available", return_value=False) as mock_check:
            result1 = sandbox._check_docker_available()
            result2 = sandbox._check_docker_available()
            assert result1 is False
            assert result2 is False
            mock_check.assert_called_once()


class TestSandboxVerificationEngine:
    """Test sandbox verification engine."""

    @pytest.fixture
    def profile(self):
        """Create a test project profile."""
        return ProjectProfile(
            project_type="web_app",
            languages=["typescript"],
            package_managers=["npm"],
            install_commands=["npm ci"],
            build_commands=["npm run build"],
            test_commands=["npm test"],
        )

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a temporary workspace."""
        return tmp_path / "test_workspace"

    async def test_run_all_returns_skipped_when_docker_unavailable(
        self, temp_workspace, profile
    ):
        """Test that run_all returns skipped results when Docker is unavailable."""
        engine = SandboxVerificationEngine(temp_workspace, profile)

        # Mock Docker as unavailable
        with patch.object(DockerSandbox, "_check_docker_available", return_value=False):
            results = await engine.run_all()

        # Should return skipped results for all commands
        assert len(results) == 3  # install, build, test
        for result in results:
            assert result.status == VerificationStatus.SKIPPED
            assert "Docker daemon not available" in result.stderr

    async def test_create_skipped_results(self, temp_workspace, profile):
        """Test _create_skipped_results creates correct results."""
        engine = SandboxVerificationEngine(temp_workspace, profile)

        results = engine._create_skipped_results()

        assert len(results) == 3
        assert results[0].name == "install: npm ci"
        assert results[1].name == "build: npm run build"
        assert results[2].name == "test: npm test"
        for result in results:
            assert result.status == VerificationStatus.SKIPPED
            assert result.exit_code is None
            assert "Docker daemon not available" in result.stderr

    async def test_create_skipped_results_partial(self, temp_workspace, profile):
        """Test _create_skipped_results with start_index."""
        engine = SandboxVerificationEngine(temp_workspace, profile)

        results = engine._create_skipped_results(start_index=1)

        assert len(results) == 2
        assert results[0].name == "build: npm run build"
        assert results[1].name == "test: npm test"

    async def test_run_all_calls_sandbox_start_stop(self, temp_workspace, profile):
        """Test run_all calls sandbox start and stop."""
        engine = SandboxVerificationEngine(temp_workspace, profile)

        with patch.object(DockerSandbox, "_check_docker_available", return_value=True):
            engine.sandbox.start = AsyncMock()
            engine.sandbox.stop = AsyncMock()
            engine.sandbox.execute = AsyncMock(return_value=SandboxExecutionResult(
                command="npm ci",
                exit_code=0,
                stdout="",
                stderr="",
                duration_ms=100,
                timed_out=False,
            ))

            await engine.run_all()

            engine.sandbox.start.assert_called_once()
            engine.sandbox.stop.assert_called_once()


class TestSandboxConfig:
    """Test sandbox configuration."""

    def test_default_config(self):
        """Test default sandbox configuration."""
        config = SandboxConfig()
        assert config.image == "vibegrade/sandbox:latest"
        assert config.cpu_limit == 2.0
        assert config.memory_limit == "2g"
        assert config.pids_limit == 100
        assert config.timeout_seconds == 120
        assert config.network_disabled is True
        assert config.read_only_rootfs is True
        assert config.cap_drop == ["ALL"]

    def test_custom_config(self):
        """Test custom sandbox configuration."""
        config = SandboxConfig(
            image="custom/sandbox:latest",
            cpu_limit=4.0,
            memory_limit="4g",
            pids_limit=200,
            timeout_seconds=300,
            network_disabled=False,
        )
        assert config.image == "custom/sandbox:latest"
        assert config.cpu_limit == 4.0
        assert config.memory_limit == "4g"
        assert config.pids_limit == 200
        assert config.timeout_seconds == 300
        assert config.network_disabled is False


class TestSandboxExecutionResult:
    """Test sandbox execution result."""

    def test_execution_result_creation(self):
        """Test creating an execution result."""
        result = SandboxExecutionResult(
            command="npm test",
            exit_code=0,
            stdout="Tests passed",
            stderr="",
            duration_ms=5000,
            timed_out=False,
        )
        assert result.command == "npm test"
        assert result.exit_code == 0
        assert result.stdout == "Tests passed"
        assert result.timed_out is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
