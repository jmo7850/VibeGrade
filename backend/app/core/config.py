"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./vibegrade.db", alias="DATABASE_URL"
    )

    # GitHub API
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    # Rubric
    rubric_version: str = Field(default="v1", alias="RUBRIC_VERSION")
    rubric_path: Path = Field(default=Path("../rubric/v1.yaml"), alias="RUBRIC_PATH")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars", alias="SECRET_KEY"
    )
    session_cookie_name: str = Field(default="vibegrade_session", alias="SESSION_COOKIE_NAME")
    session_max_age: int = Field(default=86400, alias="SESSION_MAX_AGE")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")

    # Scan Limits
    max_repo_size_mb: int = Field(default=500, alias="MAX_REPO_SIZE_MB")
    max_clone_depth: int = Field(default=1, alias="MAX_CLONE_DEPTH")
    scan_timeout_seconds: int = Field(default=300, alias="SCAN_TIMEOUT_SECONDS")

    # Sandbox (Phase 2)
    sandbox_enabled: bool = Field(default=False, alias="SANDBOX_ENABLED")
    sandbox_docker_image: str = Field(
        default="vibegrade/sandbox:latest", alias="SANDBOX_DOCKER_IMAGE"
    )
    sandbox_cpu_limit: float = Field(default=2.0, alias="SANDBOX_CPU_LIMIT")
    sandbox_memory_limit: str = Field(default="2g", alias="SANDBOX_MEMORY_LIMIT")
    sandbox_pids_limit: int = Field(default=100, alias="SANDBOX_PIDS_LIMIT")
    sandbox_timeout_seconds: int = Field(default=120, alias="SANDBOX_TIMEOUT_SECONDS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"], alias="CORS_ORIGINS"
    )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
