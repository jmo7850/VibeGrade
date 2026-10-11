"""Deterministic internal checks: README, architecture, and profiler analysis.

These checks run inside VibeGrade itself (no external tools required) and
produce normalized findings plus structured evidence for the report. They
are heuristic or verified-by-inspection, never executed code.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from app.core.logging import get_logger
from app.models import Confidence, Severity
from app.services.profiler import ProjectProfile
from app.services.static_analysis import NormalizedFinding

logger = get_logger(__name__)

# Directories never treated as project modules
IGNORED_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".turbo", "coverage", ".pytest_cache", ".ruff_cache",
    "vendor", "target",
}

MAX_FILES_TO_SCAN = 5000
MAX_FILE_LINES = 20000


@dataclass
class ArchitectureSummary:
    """Structured architecture data for the architecture explorer."""

    project_type: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    modules: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, str]] = field(default_factory=list)
    file_counts: dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    has_database: bool = False
    has_dockerfile: bool = False
    has_ci: bool = False
    inferred: bool = True  # relationships are inferred unless statically proven


def _count_lines(path: Path) -> int:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _iter_project_files(workspace: Path) -> list[Path]:
    """Iterate project files, skipping ignored dirs and huge trees."""
    files: list[Path] = []
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            files.append(Path(root) / name)
            if len(files) >= MAX_FILES_TO_SCAN:
                return files
    return files


class READMEAnalyzer:
    """Evaluates documentation completeness (documentation_reproducibility)."""

    def analyze(self, workspace: Path) -> list[NormalizedFinding]:
        findings: list[NormalizedFinding] = []
        readme_path = None
        for candidate in ("README.md", "readme.md", "README.rst", "README.txt"):
            if (workspace / candidate).exists():
                readme_path = workspace / candidate
                break

        if readme_path is None:
            findings.append(NormalizedFinding(
                tool="readme",
                tool_version="internal",
                rule_id="readme.missing",
                rule_name="README Missing",
                file_path="README.md",
                line_start=1,
                line_end=1,
                severity=Severity.HIGH,
                confidence=Confidence.VERIFIED,
                message="No README found. Setup, usage, and limitation documentation cannot be assessed.",
                metadata={},
            ))
            return findings

        content = readme_path.read_text(encoding="utf-8", errors="ignore")
        length = len(content)
        lower = content.lower()

        if length < 500:
            findings.append(NormalizedFinding(
                tool="readme",
                tool_version="internal",
                rule_id="readme.thin",
                rule_name="README Too Thin",
                file_path=str(readme_path.relative_to(workspace)),
                line_start=1,
                line_end=max(1, content.count("\n")),
                severity=Severity.MEDIUM,
                confidence=Confidence.VERIFIED,
                message=f"README is only {length} characters. It likely lacks setup, usage, or configuration details.",
                metadata={"readme_chars": length},
            ))

        if not re.search(r"#+\s*(install|getting started|setup)", lower):
            findings.append(NormalizedFinding(
                tool="readme",
                tool_version="internal",
                rule_id="readme.no_install",
                rule_name="No Setup Instructions",
                file_path=str(readme_path.relative_to(workspace)),
                line_start=1,
                line_end=1,
                severity=Severity.MEDIUM,
                confidence=Confidence.HEURISTIC,
                message="README has no install/setup section. Reproducibility suffers without build instructions.",
                metadata={},
            ))

        if not re.search(r"#+\s*(usage|example|quickstart|running)", lower):
            findings.append(NormalizedFinding(
                tool="readme",
                tool_version="internal",
                rule_id="readme.no_usage",
                rule_name="No Usage Documentation",
                file_path=str(readme_path.relative_to(workspace)),
                line_start=1,
                line_end=1,
                severity=Severity.LOW,
                confidence=Confidence.HEURISTIC,
                message="README has no usage/example section.",
                metadata={},
            ))

        if not re.search(r"#+\s*(limitation|known issue|caveat|scope)", lower):
            findings.append(NormalizedFinding(
                tool="readme",
                tool_version="internal",
                rule_id="readme.no_limitations",
                rule_name="Limitations Not Documented",
                file_path=str(readme_path.relative_to(workspace)),
                line_start=1,
                line_end=1,
                severity=Severity.LOW,
                confidence=Confidence.HEURISTIC,
                message="README does not document known limitations or scope boundaries.",
                metadata={},
            ))

        return findings


class ArchitectureAnalyzer:
    """Builds a module/dependency inventory and flags structural risks."""

    IMPORT_PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "python": re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE),
        "typescript": re.compile(
            r"""(?:import\s+[^'"]*from\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\))""",
        ),
    }

    # Patterns for placeholder/mock detection
    PLACEHOLDER_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str, Severity]]] = [
        # TODO/FIXME comments in production code
        (re.compile(r"(?i)(TODO|FIXME|XXX|HACK).*"), "placeholder.todo", Severity.LOW),
        # Mock/stub returns in production paths
        (re.compile(r"(?i)return\s+(?:mock|stub|fake|dummy|placeholder)\w*"), "placeholder.mock_return", Severity.MEDIUM),
        (re.compile(r"(?i)(?:mock|stub|fake|dummy)\s*=\s*(?:true|false|none|null)"), "placeholder.mock_assignment", Severity.MEDIUM),
        # Hardcoded test data presented as real
        (re.compile(r"(?i)(?:test|sample|demo|example)\s*(?:data|response|user|account)\s*="), "placeholder.hardcoded_data", Severity.MEDIUM),
        # Fake API implementations
        (re.compile(r"(?i)def\s+\w*fake\w*|async\s+def\s+\w*fake\w*"), "placeholder.fake_function", Severity.HIGH),
        (re.compile(r"(?i)class\s+\w*Fake\w*|class\s+\w*Mock\w*"), "placeholder.fake_class", Severity.MEDIUM),
    ]

    # Patterns for fake API detection
    FAKE_API_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str, Severity]]] = [
        # Hardcoded responses in API handlers
        (re.compile(r"(?i)return\s+\{\s*['\"]?success['\"]?\s*:\s*true\s*,\s*['\"]?data['\"]?\s*:\s*\["), "fake_api.hardcoded_response", Severity.HIGH),
        (re.compile(r"(?i)const\s+\w*(?:mock|fake)\w*\s*=\s*\{"), "fake_api.mock_constant", Severity.MEDIUM),
        # Dummy implementations
        (re.compile(r"(?i)async\s+def\s+\w*(?:login|auth|fetch|get|post|put|delete)\w*\s*\([^)]*\)\s*:\s*[\w\.]*\s*:\s*return\s+(?:True|False|None|null|\[\])"), "fake_api.dummy_impl", Severity.HIGH),
    ]

    # Patterns for missing UI states (web apps)
    MISSING_STATES_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str, Severity]]] = [
        # Missing loading states - useState initialized to false/null/undefined without loading check
        (re.compile(r"(?i)useState\s*\(\s*(?:false|null|undefined)\s*\)\s*;[\s\S]*?(?:if\s*\(!loading\)|await\s+fetch)"), "states.missing_loading", Severity.LOW),
        # Missing error boundaries (React)
        (re.compile(r"(?i)class\s+\w+\s+extends\s+(?:Component|PureComponent)\s*\{[^}]*render\s*\(\s*\)\s*\{"), "states.missing_error_boundary", Severity.LOW),
        # Missing empty states
        (re.compile(r"(?i)\.map\s*\(\s*\w+\s*=>\s*\)\s*\}\s*\}\s*(?!\s*(?:if|else|empty|no-data))"), "states.missing_empty", Severity.LOW),
    ]

    # Patterns for dead controls
    DEAD_CONTROL_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str, Severity]]] = [
        # Buttons/links with no handler
        (re.compile(r"(?i)<(?:button|a)\s+[^>]*onClick\s*=\s*\{\s*\}\s*[^>]*>"), "dead_control.no_handler", Severity.MEDIUM),
        (re.compile(r"(?i)<(?:button|a)\s+[^>]*href\s*=\s*['\"]\s*['\"]\s*[^>]*>"), "dead_control.empty_href", Severity.MEDIUM),
        # Unreachable code after return
        (re.compile(r"return\s+[^;]+;\s*\n\s*[^/\s]"), "dead_code.unreachable", Severity.LOW),
    ]

    def analyze(
        self, workspace: Path, profile: ProjectProfile
    ) -> tuple[list[NormalizedFinding], ArchitectureSummary]:
        findings: list[NormalizedFinding] = []

        files = _iter_project_files(workspace)
        file_counts: dict[str, int] = {}
        modules: dict[str, dict[str, Any]] = {}
        import_graph: dict[str, set[str]] = {}
        large_files: list[str] = []

        for path in files:
            try:
                rel = str(path.relative_to(workspace))
            except ValueError:
                continue
            ext = path.suffix.lower()
            lang = {
                ".ts": "typescript", ".tsx": "typescript",
                ".js": "javascript", ".jsx": "javascript",
                ".py": "python", ".go": "go", ".rs": "rust",
            }.get(ext)
            if lang:
                file_counts[lang] = file_counts.get(lang, 0) + 1

            # Module inventory (top-level source directories and root files)
            parts = Path(rel).parts
            if len(parts) >= 2 and parts[0] not in IGNORED_DIRS:
                module_name = parts[0]
                entry = modules.setdefault(module_name, {
                    "name": module_name,
                    "path": module_name,
                    "file_count": 0,
                    "languages": set(),
                })
                entry["file_count"] += 1
                if lang:
                    entry["languages"].add(lang)

            # Large file detection
            if ext in {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs"}:
                line_count = _count_lines(path)
                if line_count > 500:
                    large_files.append(rel)

            # Import graph for cycle detection
            if lang in self.IMPORT_PATTERNS:
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if len(content) > MAX_FILE_LINES * 200:
                    continue
                pattern = self.IMPORT_PATTERNS[lang]
                for match in pattern.finditer(content):
                    target = match.group(1) or match.group(2)
                    if target:
                        import_graph.setdefault(rel, set()).add(target)

        # Circular import detection (bounded DFS)
        cycles = self._detect_cycles(import_graph)
        for cycle in cycles[:5]:
            findings.append(NormalizedFinding(
                tool="arch",
                tool_version="internal",
                rule_id="arch.import_cycle",
                rule_name="Circular Import Detected",
                file_path=cycle[0],
                line_start=1,
                line_end=1,
                severity=Severity.MEDIUM,
                confidence=Confidence.LIKELY,
                message="Import cycle detected: " + " -> ".join(cycle),
                metadata={"cycle": cycle},
            ))

        for rel in large_files[:10]:
            findings.append(NormalizedFinding(
                tool="arch",
                tool_version="internal",
                rule_id="arch.large_file",
                rule_name="Oversized File",
                file_path=rel,
                line_start=1,
                line_end=1,
                severity=Severity.LOW,
                confidence=Confidence.HEURISTIC,
                message="File exceeds 500 lines; consider splitting for maintainability.",
                metadata={},
            ))

        # Dependency edges (inferred from imports, relative paths only)
        dependencies: list[dict[str, str]] = []
        for source, targets in import_graph.items():
            for target in targets:
                if target.startswith("."):
                    dependencies.append({"from": source, "to": target, "type": "import"})

        summary = ArchitectureSummary(
            project_type=profile.project_type.value,
            languages=profile.languages,
            frameworks=profile.frameworks,
            package_managers=profile.package_managers,
            entry_points=profile.entry_points,
            modules=[
                {
                    "name": m["name"],
                    "path": m["path"],
                    "file_count": m["file_count"],
                    "languages": sorted(m["languages"]),
                }
                for m in modules.values()
            ],
            dependencies=dependencies[:500],
            file_counts=file_counts,
            total_files=len(files),
            has_database=profile.has_database,
            has_dockerfile=profile.has_dockerfile,
            has_ci=profile.has_ci,
        )

        logger.info(
            "Architecture analysis complete",
            files=len(files),
            modules=len(modules),
            cycles=len(cycles),
        )

        # Run additional detection passes
        findings.extend(self._detect_placeholders(files, workspace))
        findings.extend(self._detect_missing_states(files, workspace, profile))
        findings.extend(self._detect_dead_controls(files, workspace, profile))

        return findings, summary

    def _detect_cycles(self, graph: dict[str, set[str]], limit: int = 10) -> list[list[str]]:
        """Detect import cycles with bounded DFS."""
        # Build a resolved adjacency: file -> files it imports (by relative path)
        resolved: dict[str, set[str]] = {}
        all_files = set(graph.keys())
        for source, targets in graph.items():
            for target in targets:
                if not target.startswith("."):
                    continue
                base = str(Path(source).parent)
                # Keep paths relative to the workspace root (no .resolve())
                candidate = os.path.normpath(str(Path(base) / target)) if target else ""
                # Match against known files by suffix variants
                for suffix in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js", ".py"):
                    variant = candidate + suffix
                    if variant in all_files:
                        resolved.setdefault(source, set()).add(variant)
                        break

        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: list[str] = []
        on_stack: set[str] = set()

        def visit(node: str) -> None:
            if len(cycles) >= limit:
                return
            visited.add(node)
            stack.append(node)
            on_stack.add(node)
            for neighbor in resolved.get(node, set()):
                if len(cycles) >= limit:
                    break
                if neighbor in on_stack:
                    idx = stack.index(neighbor)
                    cycles.append([*stack[idx:], neighbor])
                elif neighbor not in visited:
                    visit(neighbor)
            stack.pop()
            on_stack.discard(node)

        for node in list(resolved.keys()):
            if node not in visited:
                visit(node)
        return cycles

    def _detect_placeholders(self, files: list[Path], workspace: Path) -> list[NormalizedFinding]:
        """Detect placeholder implementations, TODOs, mocks in production code."""
        findings: list[NormalizedFinding] = []
        for path in files:
            try:
                rel = str(path.relative_to(workspace))
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, ValueError):
                continue

            if len(content) > MAX_FILE_LINES * 200:
                continue

            # Check placeholder patterns
            for pattern, rule_id, severity in self.PLACEHOLDER_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(NormalizedFinding(
                        tool="arch",
                        tool_version="internal",
                        rule_id=rule_id,
                        rule_name=rule_id.replace(".", " ").title(),
                        file_path=rel,
                        line_start=line_no,
                        line_end=line_no,
                        severity=severity,
                        confidence=Confidence.HEURISTIC,
                        message=f"Placeholder pattern detected: {match.group()[:100]}",
                        metadata={"matched_text": match.group()[:200]},
                    ))

            # Check fake API patterns
            for pattern, rule_id, severity in self.FAKE_API_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(NormalizedFinding(
                        tool="arch",
                        tool_version="internal",
                        rule_id=rule_id,
                        rule_name=rule_id.replace(".", " ").title(),
                        file_path=rel,
                        line_start=line_no,
                        line_end=line_no,
                        severity=severity,
                        confidence=Confidence.HEURISTIC,
                        message=f"Potential fake API implementation: {match.group()[:100]}",
                        metadata={"matched_text": match.group()[:200]},
                    ))

        return findings

    def _detect_missing_states(self, files: list[Path], workspace: Path, profile: ProjectProfile) -> list[NormalizedFinding]:
        """Detect missing loading/error/empty states in web/mobile apps."""
        if profile.project_type.value not in ("web_app", "mobile"):
            return []

        findings: list[NormalizedFinding] = []
        for path in files:
            try:
                rel = str(path.relative_to(workspace))
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, ValueError):
                continue

            if len(content) > MAX_FILE_LINES * 200:
                continue

            # Check for missing UI states patterns
            for pattern, rule_id, severity in self.MISSING_STATES_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(NormalizedFinding(
                        tool="arch",
                        tool_version="internal",
                        rule_id=rule_id,
                        rule_name=rule_id.replace(".", " ").title(),
                        file_path=rel,
                        line_start=line_no,
                        line_end=line_no,
                        severity=severity,
                        confidence=Confidence.HEURISTIC,
                        message=f"Potential missing UI state: {match.group()[:100]}",
                        metadata={"matched_text": match.group()[:200]},
                    ))

        return findings

    def _detect_dead_controls(self, files: list[Path], workspace: Path, profile: ProjectProfile) -> list[NormalizedFinding]:
        """Detect dead controls (buttons/links with no handler) in web/mobile apps."""
        if profile.project_type.value not in ("web_app", "mobile"):
            return []

        findings: list[NormalizedFinding] = []
        for path in files:
            try:
                rel = str(path.relative_to(workspace))
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, ValueError):
                continue

            if len(content) > MAX_FILE_LINES * 200:
                continue

            # Check for dead controls
            for pattern, rule_id, severity in self.DEAD_CONTROL_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(NormalizedFinding(
                        tool="arch",
                        tool_version="internal",
                        rule_id=rule_id,
                        rule_name=rule_id.replace(".", " ").title(),
                        file_path=rel,
                        line_start=line_no,
                        line_end=line_no,
                        severity=severity,
                        confidence=Confidence.HEURISTIC,
                        message=f"Potential dead control: {match.group()[:100]}",
                        metadata={"matched_text": match.group()[:200]},
                    ))

        return findings


class ProfilerCheck:
    """Derives findings from the project profile (deployment/engineering discipline)."""

    def analyze(self, workspace: Path, profile: ProjectProfile) -> list[NormalizedFinding]:
        findings: list[NormalizedFinding] = []

        if not profile.has_ci:
            findings.append(NormalizedFinding(
                tool="profiler",
                tool_version="internal",
                rule_id="profiler.missing_ci",
                rule_name="No CI Configuration",
                file_path=".github/workflows",
                line_start=1,
                line_end=1,
                severity=Severity.MEDIUM,
                confidence=Confidence.HEURISTIC,
                message="No CI configuration detected. Lint/test/build are not enforced automatically.",
                metadata={},
            ))

        if not profile.package_managers:
            findings.append(NormalizedFinding(
                tool="profiler",
                tool_version="internal",
                rule_id="profiler.no_package_manager",
                rule_name="Package Manager Not Detected",
                file_path="",
                line_start=1,
                line_end=1,
                severity=Severity.LOW,
                confidence=Confidence.HEURISTIC,
                message="No lockfile or package manifest detected; dependencies may be unpinned.",
                metadata={},
            ))
        elif not any(
            (workspace / lock).exists()
            for lock in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                         "poetry.lock", "uv.lock", "Cargo.lock", "go.sum",
                         "Gemfile.lock", "composer.lock")
        ):
            findings.append(NormalizedFinding(
                tool="profiler",
                tool_version="internal",
                rule_id="profiler.missing_lockfile",
                rule_name="Lockfile Missing",
                file_path="",
                line_start=1,
                line_end=1,
                severity=Severity.MEDIUM,
                confidence=Confidence.VERIFIED,
                message="No lockfile committed. Builds are not reproducible across environments.",
                metadata={},
            ))

        if not profile.has_dockerfile and profile.project_type.value in ("api", "web_app", "agent"):
            findings.append(NormalizedFinding(
                tool="profiler",
                tool_version="internal",
                rule_id="profiler.no_dockerfile",
                rule_name="No Dockerfile",
                file_path="Dockerfile",
                line_start=1,
                line_end=1,
                severity=Severity.INFO,
                confidence=Confidence.HEURISTIC,
                message="No Dockerfile detected; deployment packaging is undefined.",
                metadata={},
            ))

        # Test file presence
        has_tests = any(
            _iter_project_files(workspace)
        ) and self._has_test_files(workspace)
        if not has_tests and profile.project_type.value != "unknown":
            findings.append(NormalizedFinding(
                tool="profiler",
                tool_version="internal",
                rule_id="profiler.no_tests",
                rule_name="No Test Files Detected",
                file_path="tests",
                line_start=1,
                line_end=1,
                severity=Severity.HIGH,
                confidence=Confidence.VERIFIED,
                message="No test files detected in the repository. Behavior is unverified.",
                metadata={},
            ))

        return findings

    def _has_test_files(self, workspace: Path) -> bool:
        for _root, dirs, filenames in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            for name in filenames:
                if name.startswith("."):
                    continue
                lower = name.lower()
                if (
                    lower.startswith("test_")
                    or lower.endswith("_test.py")
                    or lower.endswith(".test.ts")
                    or lower.endswith(".test.tsx")
                    or lower.endswith(".test.js")
                    or lower.endswith("_test.go")
                    or lower == "tests"
                ):
                    return True
        return False


class InternalChecksEngine:
    """Runs all deterministic internal checks."""

    def __init__(self):
        self.readme_analyzer = READMEAnalyzer()
        self.architecture_analyzer = ArchitectureAnalyzer()
        self.profiler_check = ProfilerCheck()

    async def analyze(
        self, workspace: Path, profile: ProjectProfile
    ) -> tuple[list[NormalizedFinding], ArchitectureSummary]:
        """Run internal checks. Returns (findings, architecture summary)."""
        findings: list[NormalizedFinding] = []

        findings.extend(self.readme_analyzer.analyze(workspace))
        findings.extend(self.profiler_check.analyze(workspace, profile))
        arch_findings, summary = self.architecture_analyzer.analyze(workspace, profile)
        findings.extend(arch_findings)

        return findings, summary
