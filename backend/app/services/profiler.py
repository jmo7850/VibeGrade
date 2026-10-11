"""Project profiling and detection."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from app.core.logging import get_logger
from app.models import ProjectType

logger = get_logger(__name__)


@dataclass
class ProjectProfile:
    """Detected project profile."""
    project_type: ProjectType = ProjectType.UNKNOWN
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    install_commands: list[str] = field(default_factory=list)
    config_files: dict[str, str] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)
    has_database: bool = False
    has_dockerfile: bool = False
    has_ci: bool = False


class ProjectProfiler:
    """Detects project type, languages, frameworks, and commands."""

    # Language detection by file extension
    LANGUAGE_EXTENSIONS: ClassVar[dict[str, str]] = {
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".py": "python",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".dart": "dart",
        ".lua": "lua",
        ".r": "r",
        ".scala": "scala",
        ".clj": "clojure",
        ".ex": "elixir",
        ".exs": "elixir",
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS: ClassVar[dict[str, dict[str, list[str]]]] = {
        "web_app": {
            "nextjs": ["next.config.js", "next.config.ts", "next.config.mjs"],
            "vite": ["vite.config.ts", "vite.config.js"],
            "react": ["react", "react-dom"],
            "vue": ["vue", "@vue/"],
            "svelte": ["svelte", "@sveltejs/"],
            "astro": ["astro"],
            "remix": ["@remix-run/"],
            "gatsby": ["gatsby"],
            "nuxt": ["nuxt", "nuxt.config"],
        },
        "api": {
            "fastapi": ["fastapi"],
            "express": ["express"],
            "django": ["django"],
            "flask": ["flask"],
            "gin": ["gin-gonic/gin"],
            "actix": ["actix-web"],
            "axum": ["axum"],
            "rocket": ["rocket"],
            "spring": ["spring-boot"],
            "nestjs": ["@nestjs/"],
        },
        "cli": {
            "click": ["click"],
            "typer": ["typer"],
            "commander": ["commander"],
            "cobra": ["spf13/cobra"],
            "clap": ["clap"],
            "argparse": [],  # stdlib
        },
        "agent": {
            "langchain": ["langchain"],
            "crewai": ["crewai"],
            "autogen": ["autogen"],
            "openai-agents": ["openai-agents"],
            "semantic-kernel": ["semantic-kernel"],
        },
        "mobile": {
            "expo": ["expo"],
            "react-native": ["react-native"],
            "flutter": ["flutter"],
            "tauri": ["tauri"],
            "capacitor": ["@capacitor/"],
        },
    }

    # Package manager detection
    PACKAGE_MANAGER_FILES: ClassVar[dict[str, list[str]]] = {
        "npm": ["package-lock.json"],
        "yarn": ["yarn.lock"],
        "pnpm": ["pnpm-lock.yaml"],
        "pip": ["requirements.txt", "requirements.in"],
        "poetry": ["poetry.lock", "pyproject.toml"],
        "uv": ["uv.lock"],
        "cargo": ["Cargo.lock"],
        "go": ["go.mod", "go.sum"],
        "maven": ["pom.xml"],
        "gradle": ["build.gradle", "build.gradle.kts"],
        "composer": ["composer.lock"],
        "bundler": ["Gemfile.lock"],
    }

    def __init__(self):
        pass

    async def analyze(self, workspace: Path) -> ProjectProfile:
        """Analyze workspace and return project profile."""
        profile = ProjectProfile()

        # Detect languages
        profile.languages = self._detect_languages(workspace)

        # Detect config files
        profile.config_files = self._detect_config_files(workspace)

        # Detect package managers
        profile.package_managers = self._detect_package_managers(workspace)

        # Detect frameworks and project type
        profile.frameworks, profile.project_type = self._detect_frameworks_and_type(
            workspace, profile.config_files, profile.package_managers
        )

        # Detect build/test/install commands
        profile.install_commands = self._get_install_commands(profile)
        profile.build_commands = self._get_build_commands(workspace, profile)
        profile.test_commands = self._get_test_commands(workspace, profile)

        # Detect entry points
        profile.entry_points = self._detect_entry_points(workspace, profile)

        # Detect database, Docker, CI
        profile.has_database = self._detect_database(workspace, profile)
        profile.has_dockerfile = (workspace / "Dockerfile").exists()
        profile.has_ci = self._detect_ci(workspace)

        logger.info("Project profiled", project_type=profile.project_type.value, languages=profile.languages)
        return profile

    def _detect_languages(self, workspace: Path) -> list[str]:
        """Detect languages from file extensions."""
        languages: set[str] = set()
        for ext, lang in self.LANGUAGE_EXTENSIONS.items():
            if list(workspace.rglob(f"*{ext}")):
                languages.add(lang)
        return sorted(languages)

    def _detect_config_files(self, workspace: Path) -> dict[str, str]:
        """Find and read key config files."""
        config_files = {}
        config_patterns = [
            "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
            "composer.json", "Gemfile", "pubspec.yaml", "deno.json",
        ]
        for pattern in config_patterns:
            for file in workspace.rglob(pattern):
                try:
                    rel_path = file.relative_to(workspace)
                    config_files[str(rel_path)] = file.read_text(encoding="utf-8", errors="ignore")[:5000]
                except Exception:
                    pass
        return config_files

    def _detect_package_managers(self, workspace: Path) -> list[str]:
        """Detect package managers from lock files."""
        managers = []
        for manager, files in self.PACKAGE_MANAGER_FILES.items():
            for file in files:
                if (workspace / file).exists():
                    managers.append(manager)
                    break
        return managers

    def _detect_frameworks_and_type(
        self, workspace: Path, config_files: dict[str, str], package_managers: list[str]
    ) -> tuple[list[str], ProjectType]:
        """Detect frameworks and determine project type."""
        detected_frameworks = []
        type_scores: dict[ProjectType, int] = dict.fromkeys(ProjectType, 0)

        # Check package.json for JS/TS frameworks
        if "package.json" in config_files:
            try:
                pkg = json.loads(config_files["package.json"])
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                for category, frameworks in self.FRAMEWORK_PATTERNS.items():
                    for fw, patterns in frameworks.items():
                        for pattern in patterns:
                            if pattern in deps:
                                detected_frameworks.append(fw)
                                type_scores[ProjectType(category)] += 2
                                break
            except Exception:
                pass

        # Check Python files for frameworks
        if "python" in [lang.lower() for lang in self._detect_languages(workspace)]:
            for py_file in workspace.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if "fastapi" in content or "FastAPI" in content:
                        detected_frameworks.append("fastapi")
                        type_scores[ProjectType.API] += 2
                    if "django" in content:
                        detected_frameworks.append("django")
                        type_scores[ProjectType.API] += 2
                    if "flask" in content:
                        detected_frameworks.append("flask")
                        type_scores[ProjectType.API] += 1
                except Exception:
                    pass

        # Check Go files
        if "go" in [lang.lower() for lang in self._detect_languages(workspace)]:
            for go_file in workspace.rglob("*.go"):
                try:
                    content = go_file.read_text(encoding="utf-8", errors="ignore")
                    if "gin" in content or "gin-gonic" in content:
                        detected_frameworks.append("gin")
                        type_scores[ProjectType.API] += 2
                except Exception:
                    pass

        # Check Rust files
        if "rust" in [lang.lower() for lang in self._detect_languages(workspace)]:
            if (workspace / "Cargo.toml").exists():
                try:
                    cargo = (workspace / "Cargo.toml").read_text()
                    if "actix-web" in cargo:
                        detected_frameworks.append("actix")
                        type_scores[ProjectType.API] += 2
                    if "axum" in cargo:
                        detected_frameworks.append("axum")
                        type_scores[ProjectType.API] += 2
                except Exception:
                    pass

        # Determine project type from scores
        # Check for CLI entry points
        if self._has_cli_entry_points(workspace):
            type_scores[ProjectType.CLI] += 3

        # Check for mobile
        if "expo" in detected_frameworks or "react-native" in detected_frameworks:
            type_scores[ProjectType.MOBILE] += 3

        # Default to web_app if JS/TS with frontend deps
        if "javascript" in [lang.lower() for lang in self._detect_languages(workspace)] or "typescript" in [lang.lower() for lang in self._detect_languages(workspace)]:
            if any(fw in detected_frameworks for fw in ["react", "vue", "svelte", "nextjs", "vite", "astro", "remix"]):
                type_scores[ProjectType.WEB_APP] += 2

        # Pick highest scoring type
        project_type = max(type_scores, key=type_scores.get)
        if type_scores[project_type] == 0:
            project_type = ProjectType.UNKNOWN

        return detected_frameworks, project_type

    def _has_cli_entry_points(self, workspace: Path) -> bool:
        """Check for CLI entry points."""
        # package.json bin field
        if "package.json" in (workspace / "package.json").read_text(encoding="utf-8", errors="ignore") if (workspace / "package.json").exists() else "":
            pass
        # Python console_scripts / entry_points
        if (workspace / "pyproject.toml").exists():
            content = (workspace / "pyproject.toml").read_text()
            if "console_scripts" in content or "[tool.poetry.scripts]" in content:
                return True
        # Cargo bin
        if (workspace / "Cargo.toml").exists():
            content = (workspace / "Cargo.toml").read_text()
            if "[[bin]]" in content:
                return True
        # Go main package
        for go_file in workspace.rglob("*.go"):
            try:
                if "package main" in go_file.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except Exception:
                pass
        return False

    def _get_install_commands(self, profile: ProjectProfile) -> list[str]:
        """Get install commands for detected package managers."""
        commands = []
        if "npm" in profile.package_managers:
            commands.append("npm ci")
        elif "yarn" in profile.package_managers:
            commands.append("yarn install --frozen-lockfile")
        elif "pnpm" in profile.package_managers:
            commands.append("pnpm install --frozen-lockfile")
        elif "poetry" in profile.package_managers:
            commands.append("poetry install --no-interaction")
        elif "uv" in profile.package_managers:
            commands.append("uv sync")
        elif "pip" in profile.package_managers:
            commands.append("pip install -r requirements.txt")
        elif "cargo" in profile.package_managers:
            commands.append("cargo fetch")
        elif "go" in profile.package_managers:
            commands.append("go mod download")
        return commands

    def _get_build_commands(self, workspace: Path, profile: ProjectProfile) -> list[str]:
        """Get build commands."""
        commands = []

        # Check package.json scripts
        if "package.json" in profile.config_files:
            try:
                pkg = json.loads(profile.config_files["package.json"])
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    commands.append("npm run build")
                elif "compile" in scripts:
                    commands.append("npm run compile")
            except Exception:
                pass

        # TypeScript
        if "typescript" in profile.languages:
            if (workspace / "tsconfig.json").exists():
                commands.append("tsc --noEmit")

        # Rust
        if "cargo" in profile.package_managers:
            commands.append("cargo build --release")

        # Go
        if "go" in profile.package_managers:
            commands.append("go build ./...")

        # Python - no build typically
        # But check for pyproject.toml with build backend
        if (workspace / "pyproject.toml").exists():
            content = (workspace / "pyproject.toml").read_text()
            if "build-backend" in content or "setuptools" in content:
                commands.append("pip install -e .")

        return commands

    def _get_test_commands(self, workspace: Path, profile: ProjectProfile) -> list[str]:
        """Get test commands."""
        commands = []

        # Check package.json scripts
        if "package.json" in profile.config_files:
            try:
                pkg = json.loads(profile.config_files["package.json"])
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    commands.append("npm test")
            except Exception:
                pass

        # Python
        if "python" in profile.languages:
            if (workspace / "pytest.ini").exists() or (workspace / "pyproject.toml").exists():
                commands.append("pytest")
            elif any(workspace.rglob("test_*.py")) or any(workspace.rglob("*_test.py")):
                commands.append("pytest")

        # Rust
        if "cargo" in profile.package_managers:
            commands.append("cargo test")

        # Go
        if "go" in profile.package_managers:
            commands.append("go test ./...")

        return commands

    def _detect_entry_points(self, workspace: Path, profile: ProjectProfile) -> list[str]:
        """Detect entry points."""
        entry_points = []

        # package.json main/bin
        if "package.json" in profile.config_files:
            try:
                pkg = json.loads(profile.config_files["package.json"])
                if "main" in pkg:
                    entry_points.append(pkg["main"])
                if "bin" in pkg:
                    if isinstance(pkg["bin"], dict):
                        entry_points.extend(pkg["bin"].values())
                    else:
                        entry_points.append(pkg["bin"])
            except Exception:
                pass

        # Python
        if (workspace / "pyproject.toml").exists():
            (workspace / "pyproject.toml").read_text()
            # Could parse for console_scripts

        # Go main
        for go_file in workspace.rglob("*.go"):
            try:
                if "package main" in go_file.read_text(encoding="utf-8", errors="ignore"):
                    entry_points.append(str(go_file.relative_to(workspace)))
            except Exception:
                pass

        return entry_points

    def _detect_database(self, workspace: Path, profile: ProjectProfile) -> bool:
        """Detect database usage."""
        # Check for ORM usage
        orm_patterns = [
            "sqlalchemy", "prisma", "drizzle-orm", "knex", "sequelize",
            "typeorm", "mongoose", "gorm", "sqlx", "diesel", "sea-orm",
            "tortoise-orm", "peewee", "pony", "databases",
        ]
        for config_file in profile.config_files.values():
            for pattern in orm_patterns:
                if pattern in config_file:
                    return True
        # Check for migration directories
        if (workspace / "migrations").exists() or (workspace / "alembic").exists():
            return True
        return False

    def _detect_ci(self, workspace: Path) -> bool:
        """Detect CI configuration."""
        ci_paths = [
            ".github/workflows",
            ".gitlab-ci.yml",
            ".circleci/config.yml",
            "azure-pipelines.yml",
            "Jenkinsfile",
            ".travis.yml",
        ]
        for path in ci_paths:
            if (workspace / path).exists():
                return True
        return False
