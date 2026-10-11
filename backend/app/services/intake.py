"""Repository intake and cloning."""

import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from githubkit import GitHub
from githubkit.exception import GitHubException

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GITHUB_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$"
)


class RepositoryIntakeError(Exception):
    """Raised when repository intake fails."""
    pass


class RepositoryIntake:
    """Handles repository URL validation, cloning, and metadata extraction."""

    def __init__(self):
        self.settings = get_settings()
        self.github = GitHub(self.settings.github_token) if self.settings.github_token else None

    def parse_github_url(self, url: str) -> tuple[str, str, str | None, str | None]:
        """
        Parse a GitHub URL.
        Returns: (owner, repo, branch, commit_sha)
        """
        match = GITHUB_URL_PATTERN.match(url.rstrip("/"))
        if not match:
            raise RepositoryIntakeError(f"Invalid GitHub URL: {url}")

        owner, repo = match.groups()
        repo = repo.removesuffix(".git")

        # Extract branch/commit from path if present
        branch = None
        commit_sha = None
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 4 and path_parts[2] in ("tree", "blob"):
            branch = path_parts[3]
        elif len(path_parts) >= 3 and path_parts[2] == "commit":
            commit_sha = path_parts[3]

        return owner, repo, branch, commit_sha

    async def validate_repository(self, owner: str, repo: str) -> dict:
        """Validate repository exists and is public. Returns repo metadata."""
        if self.github:
            try:
                response = await self.github.rest.repos.async_get(owner=owner, repo=repo)
                repo_data = response.parsed_data
                if repo_data.private:
                    raise RepositoryIntakeError("Private repositories require authentication")
                return {
                    "default_branch": repo_data.default_branch,
                    "size_kb": repo_data.size,
                    "language": repo_data.language,
                    "description": repo_data.description,
                }
            except GitHubException as e:
                if e.response.status_code == 404:
                    raise RepositoryIntakeError(f"Repository not found: {owner}/{repo}") from e
                raise RepositoryIntakeError(f"GitHub API error: {e}") from e
        else:
            # Fallback: use public API without auth (rate limited)
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
                if response.status_code == 404:
                    raise RepositoryIntakeError(f"Repository not found: {owner}/{repo}")
                if response.status_code == 403:
                    raise RepositoryIntakeError("GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher limits.")
                response.raise_for_status()
                repo_data = response.json()
                if repo_data.get("private"):
                    raise RepositoryIntakeError("Private repositories require authentication")
                return {
                    "default_branch": repo_data.get("default_branch", "main"),
                    "size_kb": repo_data.get("size", 0),
                    "language": repo_data.get("language"),
                    "description": repo_data.get("description"),
                }

    async def clone_repository(
        self,
        owner: str,
        repo: str,
        commit_sha: str | None = None,
        branch: str | None = None,
    ) -> tuple[Path, str]:
        """
        Clone repository at specific commit.
        Returns: (workspace_path, resolved_commit_sha)
        """
        import subprocess

        # Create temporary workspace
        workspace = Path(tempfile.mkdtemp(prefix="vibegrade_"))
        logger.info("Cloning repository", workspace=str(workspace), owner=owner, repo=repo)

        try:
            # Build clone URL
            clone_url = f"https://github.com/{owner}/{repo}.git"
            if self.settings.github_token:
                clone_url = f"https://{self.settings.github_token}@github.com/{owner}/{repo}.git"

            # Shallow clone
            clone_cmd = [
                "git", "clone",
                "--depth", str(self.settings.max_clone_depth),
                clone_url,
                str(workspace),
            ]
            if branch:
                clone_cmd.extend(["--branch", branch])

            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RepositoryIntakeError(f"Git clone failed: {result.stderr}")

            # If commit_sha specified, checkout that commit
            if commit_sha:
                checkout_result = subprocess.run(
                    ["git", "checkout", commit_sha],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if checkout_result.returncode != 0:
                    raise RepositoryIntakeError(f"Git checkout failed: {checkout_result.stderr}")
                resolved_sha = commit_sha
            else:
                # Get current commit SHA
                rev_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if rev_result.returncode != 0:
                    raise RepositoryIntakeError("Failed to get commit SHA")
                resolved_sha = rev_result.stdout.strip()

            # Verify size
            size_mb = self._get_dir_size(workspace) / (1024 * 1024)
            if size_mb > self.settings.max_repo_size_mb:
                shutil.rmtree(workspace, ignore_errors=True)
                raise RepositoryIntakeError(
                    f"Repository size ({size_mb:.1f}MB) exceeds limit ({self.settings.max_repo_size_mb}MB)"
                )

            logger.info("Repository cloned successfully", workspace=str(workspace), commit_sha=resolved_sha)
            return workspace, resolved_sha

        except Exception:
            # Cleanup on failure
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def _get_dir_size(self, path: Path) -> int:
        """Get directory size in bytes."""
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
        return total

    def cleanup_workspace(self, workspace: Path) -> None:
        """Clean up workspace directory."""
        shutil.rmtree(workspace, ignore_errors=True)
        logger.info("Workspace cleaned up", workspace=str(workspace))
