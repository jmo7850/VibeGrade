"""Tests for scoring integrity and internal checks."""

from app.models import Confidence, ProjectType, Severity
from app.services.internal_checks import (
    ArchitectureAnalyzer,
    InternalChecksEngine,
    ProfilerCheck,
    READMEAnalyzer,
)
from app.services.scoring import ScoringEngine
from app.services.static_analysis import NormalizedFinding


def _finding(
    tool: str,
    rule_id: str,
    severity: Severity,
    confidence: Confidence,
    dimensions: list[str],
    file_path: str = "src/main.py",
) -> dict:
    return {
        "finding": NormalizedFinding(
            tool=tool,
            tool_version="internal",
            rule_id=rule_id,
            rule_name=rule_id,
            file_path=file_path,
            line_start=1,
            line_end=1,
            severity=severity,
            confidence=confidence,
            message=f"{rule_id} finding",
            metadata={},
        ),
        "dimensions": dimensions,
        "applicable": True,
    }


def _all_checks_passed() -> dict:
    return {
        "eslint": {"status": "passed"},
        "typescript": {"status": "passed"},
        "semgrep": {"status": "passed"},
        "trivy": {"status": "passed"},
        "detect_secrets": {"status": "passed"},
        "profiler": {"status": "passed"},
        "readme": {"status": "passed"},
        "architecture": {"status": "passed"},
        "verification": {"status": "passed"},
    }


class TestScoringIntegrity:
    """Scoring integrity rules from the grading contract."""

    def test_skipped_checks_do_not_award_points(self):
        """A check that never ran must not be treated as a pass."""
        engine = ScoringEngine()
        # Only profiler ran; everything else not_run
        check_results = {
            "profiler": {"status": "passed"},
            "eslint": {"status": "not_run"},
            "typescript": {"status": "not_run"},
            "semgrep": {"status": "not_run"},
            "trivy": {"status": "not_run"},
            "detect_secrets": {"status": "not_run"},
            "readme": {"status": "not_run"},
            "architecture": {"status": "not_run"},
            "verification": {"status": "not_run"},
        }
        result = engine.calculate([], ProjectType.WEB_APP.value, check_results)

        # Coverage must be far below 100% when most checks did not run
        assert result.coverage_percent < 40
        # Score must be reduced: skipped subchecks earn 0 points
        assert result.overall_score < 100

    def test_verification_skipped_disclosed(self):
        """Sandbox-disabled verification must not credit functional correctness."""
        engine = ScoringEngine()
        check_results = _all_checks_passed()
        check_results["verification"] = {"status": "skipped"}

        result = engine.calculate([], ProjectType.WEB_APP.value, check_results)

        fc_subchecks = [
            sc for sc in result.subcheck_scores
            if sc.dimension_code == "functional_correctness"
        ]
        verification_linked = [
            sc for sc in fc_subchecks
            if any(
                s in ("verification.build", "verification.run", "verification.workflow")
                for s in engine.rubric.get_subcheck(sc.subcheck_id).evidence_sources
            )
        ]
        assert verification_linked
        assert all(sc.status == "skipped" for sc in verification_linked)
        assert all(sc.points_earned == 0 for sc in verification_linked)

    def test_missing_evidence_not_a_pass(self):
        """Subchecks with no recorded evidence source are skipped."""
        engine = ScoringEngine()
        result = engine.calculate([], ProjectType.WEB_APP.value, {})
        assert result.coverage_percent == 0.0
        assert all(
            sc.status == "skipped" for sc in result.subcheck_scores
        )

    def test_clean_project_with_all_checks_scores_100(self):
        """All checks executed and no findings = 100."""
        engine = ScoringEngine()
        result = engine.calculate([], ProjectType.WEB_APP.value, _all_checks_passed())
        assert result.overall_score == 100
        assert result.coverage_percent == 100.0

    def test_tool_not_installed_is_not_run(self):
        """Tool availability probe semantics: absent tool = not_run."""
        engine = ScoringEngine()
        check_results = _all_checks_passed()
        check_results["semgrep"] = {"status": "not_run", "tool_installed": False}
        result = engine.calculate([], ProjectType.WEB_APP.value, check_results)
        sec_subchecks = [
            sc for sc in result.subcheck_scores
            if sc.dimension_code == "security_privacy"
        ]
        # sec.no_secrets depends solely on detect_secrets; must still pass
        no_secrets = next(
            sc for sc in sec_subchecks if sc.subcheck_id == "sec.no_secrets"
        )
        assert no_secrets.status == "passed"

    def test_internal_finding_maps_to_documentation_dimension(self):
        """README findings must reduce documentation_reproducibility score."""
        engine = ScoringEngine()
        findings = [
            _finding("readme", "readme.missing", Severity.HIGH,
                     Confidence.VERIFIED, ["documentation_reproducibility"],
                     "README.md"),
        ]
        result = engine.calculate(findings, ProjectType.WEB_APP.value, _all_checks_passed())
        doc_dim = next(
            d for d in result.dimension_scores
            if d.code == "documentation_reproducibility"
        )
        assert doc_dim.score < 100
        assert doc_dim.findings_count >= 1

    def test_internal_finding_maps_to_deployment_dimension(self):
        """Profiler CI finding must reduce deployment_operations score."""
        engine = ScoringEngine()
        findings = [
            _finding("profiler", "profiler.missing_ci", Severity.MEDIUM,
                     Confidence.HEURISTIC, ["deployment_operations"],
                     ".github/workflows"),
        ]
        result = engine.calculate(findings, ProjectType.WEB_APP.value, _all_checks_passed())
        deploy_dim = next(
            d for d in result.dimension_scores
            if d.code == "deployment_operations"
        )
        assert deploy_dim.score < 100

    def test_critical_blocker_overrides_score(self):
        """Critical security finding must trigger readiness warning."""
        engine = ScoringEngine()
        findings = [
            _finding("detect_secrets", "aws-key", Severity.CRITICAL,
                     Confidence.VERIFIED, ["security_privacy"],
                     "config.py"),
        ]
        result = engine.calculate(findings, ProjectType.WEB_APP.value, _all_checks_passed())
        assert result.critical_blockers == 1
        assert "Critical Blockers" in result.readiness_verdict
        # Even a high score must not claim production readiness
        assert result.readiness_verdict != "Production Ready"

    def test_determinism(self):
        """Same inputs produce identical outputs."""
        engine = ScoringEngine()
        findings = [
            _finding("semgrep", "rule-x", Severity.HIGH,
                     Confidence.LIKELY, ["security_privacy"]),
        ]
        r1 = engine.calculate(findings, ProjectType.WEB_APP.value, _all_checks_passed())
        r2 = engine.calculate(findings, ProjectType.WEB_APP.value, _all_checks_passed())
        assert r1.overall_score == r2.overall_score
        assert r1.subcheck_scores == r2.subcheck_scores


class TestREADMEAnalyzer:
    def test_missing_readme(self, temp_workspace):
        findings = READMEAnalyzer().analyze(temp_workspace)
        assert any(f.rule_id == "readme.missing" for f in findings)

    def test_thin_readme(self, temp_workspace):
        (temp_workspace / "README.md").write_text("# Project\n\nShort.")
        findings = READMEAnalyzer().analyze(temp_workspace)
        assert any(f.rule_id == "readme.thin" for f in findings)

    def test_complete_readme_clean(self, temp_workspace):
        (temp_workspace / "README.md").write_text(
            "# Project\n\n## Installation\n\nRun `npm install`.\n\n"
            "## Usage\n\nRun `npm start`.\n\n## Limitations\n\nNone known.\n"
            + "x" * 600
        )
        findings = READMEAnalyzer().analyze(temp_workspace)
        assert findings == []


class TestProfilerCheck:
    def test_no_ci_detected(self, temp_workspace):
        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.WEB_APP, has_ci=False)
        findings = ProfilerCheck().analyze(temp_workspace, prof)
        assert any(f.rule_id == "profiler.missing_ci" for f in findings)

    def test_no_tests_detected(self, temp_workspace):
        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.API)
        findings = ProfilerCheck().analyze(temp_workspace, prof)
        assert any(f.rule_id == "profiler.no_tests" for f in findings)

    def test_missing_lockfile(self, temp_workspace):
        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        (temp_workspace / "package.json").write_text('{"name": "x"}')
        prof = ProjectProfile(
            project_type=ProjectType.WEB_APP,
            package_managers=["npm"],
        )
        findings = ProfilerCheck().analyze(temp_workspace, prof)
        assert any(f.rule_id == "profiler.missing_lockfile" for f in findings)


class TestArchitectureAnalyzer:
    def test_cycle_detection(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "a.ts").write_text('import { b } from "./b";\nexport const a = 1;')
        (src / "b.ts").write_text('import { a } from "./a";\nexport const b = 2;')

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.WEB_APP, languages=["typescript"])
        findings, summary = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "arch.import_cycle" for f in findings)
        assert summary.total_files == 2

    def test_large_file_detection(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "big.py").write_text("# line\n" * 600)

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.API, languages=["python"])
        findings, _summary = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "arch.large_file" for f in findings)

    def test_placeholder_detection(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "service.py").write_text("""
def get_user(user_id: str):
    # TODO: implement proper user lookup
    return mock_user_data(user_id)

def mock_user_data(user_id):
    return {"id": user_id, "name": "Test User"}

class FakeAuthService:
    async def login(self, email: str, password: str):
        return True
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.API, languages=["python"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "placeholder.todo" for f in findings)
        assert any(f.rule_id == "placeholder.mock_return" for f in findings)
        assert any(f.rule_id == "placeholder.fake_class" for f in findings)

    def test_fake_api_detection(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "api.py").write_text("""
async def get_user(user_id: str):
    # Fake API implementation
    return {"success": True, "data": [{"id": user_id, "name": "Fake User"}]}

const mockResponse = {
    success: true,
    data: []
}
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.API, languages=["python"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "fake_api.hardcoded_response" for f in findings)
        assert any(f.rule_id == "fake_api.mock_constant" for f in findings)

    def test_missing_states_detection_web_app(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "Component.tsx").write_text("""
import React, { useState } from 'react';

function UserList() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);

    // Missing loading state check
    if (!loading) {
        return users.map(u => <div>{u.name}</div>);
    }

    return <div>Loading...</div>;
}
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.WEB_APP, languages=["typescript"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "states.missing_loading" for f in findings)

    def test_missing_states_not_applies_to_cli(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "main.py").write_text("""
def main():
    users = get_users()
    for user in users:
        print(user.name)
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.CLI, languages=["python"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert not any(f.rule_id.startswith("states.") for f in findings)

    def test_dead_control_detection(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "Button.tsx").write_text("""
function Button() {
    return <button onClick={}>Click me</button>;
}

function Link() {
    return <a href="">Empty link</a>;
}
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.WEB_APP, languages=["typescript"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert any(f.rule_id == "dead_control.no_handler" for f in findings)
        assert any(f.rule_id == "dead_control.empty_href" for f in findings)

    def test_dead_control_not_applies_to_cli(self, temp_workspace):
        src = temp_workspace / "src"
        src.mkdir()
        (src / "main.py").write_text("""
def main():
    pass
""")

        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.CLI, languages=["python"])
        findings, _ = ArchitectureAnalyzer().analyze(temp_workspace, prof)
        assert not any(f.rule_id.startswith("dead_control.") for f in findings)


class TestInternalChecksEngine:
    async def test_engine_runs_all_checks(self, temp_workspace):
        from app.models import ProjectType
        from app.services.profiler import ProjectProfile

        prof = ProjectProfile(project_type=ProjectType.WEB_APP)
        engine = InternalChecksEngine()
        findings, summary = await engine.analyze(temp_workspace, prof)
        assert isinstance(findings, list)
        assert summary.project_type == "web_app"
