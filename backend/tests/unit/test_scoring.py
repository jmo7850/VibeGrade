"""Tests for the scoring engine."""

import pytest

from app.models import Confidence, ProjectType, Severity
from app.services.rubric import get_rubric
from app.services.scoring import ScoringEngine
from app.services.static_analysis import NormalizedFinding


class TestScoringEngine:
    """Test deterministic scoring engine."""

    @pytest.fixture
    def rubric(self):
        return get_rubric("v1")

    @pytest.fixture
    def engine(self, rubric):
        return ScoringEngine(rubric)

    @pytest.fixture
    def sample_findings(self):
        """Create sample findings for testing."""
        return [
            {
                "finding": NormalizedFinding(
                    tool="eslint",
                    tool_version="8.0.0",
                    rule_id="no-unused-vars",
                    rule_name="Unused Variable",
                    file_path="src/utils.ts",
                    line_start=10,
                    line_end=10,
                    severity=Severity.MEDIUM,
                    confidence=Confidence.LIKELY,
                    message="Unused variable 'x'",
                    metadata={},
                ),
                "dimensions": ["engineering_discipline"],
                "applicable": True,
            },
            {
                "finding": NormalizedFinding(
                    tool="semgrep",
                    tool_version="1.0.0",
                    rule_id="sql-injection",
                    rule_name="SQL Injection",
                    file_path="src/db.py",
                    line_start=25,
                    line_end=25,
                    severity=Severity.CRITICAL,
                    confidence=Confidence.VERIFIED,
                    message="Potential SQL injection",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

    @pytest.fixture
    def check_results(self):
        return {
            "eslint": {"status": "passed"},
            "typescript": {"status": "passed"},
            "semgrep": {"status": "passed"},
            "trivy": {"status": "passed"},
            "detect_secrets": {"status": "passed"},
            "verification": {"status": "passed"},
            "profiler": {"status": "passed"},
            "readme": {"status": "passed"},
            "architecture": {"status": "passed"},
        }

    def test_max_score_clean_project(self, engine):
        """Clean project with no findings should score 100."""
        findings = []
        check_results = {
            "eslint": {"status": "passed"},
            "typescript": {"status": "passed"},
            "semgrep": {"status": "passed"},
            "trivy": {"status": "passed"},
            "detect_secrets": {"status": "passed"},
            "verification": {"status": "passed"},
            "profiler": {"status": "passed"},
            "readme": {"status": "passed"},
            "architecture": {"status": "passed"},
        }

        result = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)

        assert result.overall_score == 100
        assert result.grade == "A"
        assert result.coverage_percent == 100.0
        assert result.confidence_percent == 100.0
        assert result.critical_blockers == 0

    def test_security_finding_reduces_score(self, engine, sample_findings, check_results):
        """Security findings should reduce score."""
        result = engine.calculate(sample_findings, ProjectType.WEB_APP.value, check_results)

        # Should be less than 100 due to critical security finding
        assert result.overall_score < 100
        assert result.critical_blockers == 1
        assert result.readiness_verdict == "Not Production Ready (Critical Blockers)"

    def test_applicability_excludes_na_checks(self, engine):
        """CLI project should exclude DB-related checks."""
        findings = []
        check_results = {
            "eslint": {"status": "passed"},
            "typescript": {"status": "passed"},
            "semgrep": {"status": "passed"},
            "trivy": {"status": "passed"},
            "detect_secrets": {"status": "passed"},
            "verification": {"status": "passed"},
            "profiler": {"status": "passed"},
            "readme": {"status": "passed"},
            "architecture": {"status": "passed"},
        }

        # CLI project - should have fewer applicable checks
        result_cli = engine.calculate(findings, ProjectType.CLI.value, check_results)
        result_web = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)

        # Both should get 100 since no findings, but coverage may differ
        assert result_cli.overall_score == 100
        assert result_web.overall_score == 100

    def test_deterministic_reproducibility(self, engine, sample_findings, check_results):
        """Same input should always produce identical output."""
        result1 = engine.calculate(sample_findings, ProjectType.WEB_APP.value, check_results)
        result2 = engine.calculate(sample_findings, ProjectType.WEB_APP.value, check_results)

        assert result1.overall_score == result2.overall_score
        assert result1.grade == result2.grade
        assert result1.coverage_percent == result2.coverage_percent
        assert result1.confidence_percent == result2.confidence_percent
        assert result1.dimension_scores == result2.dimension_scores

    def test_partial_credit_for_heuristic(self, engine, check_results):
        """Heuristic findings should have reduced penalty."""
        findings_heuristic = [
            {
                "finding": NormalizedFinding(
                    tool="semgrep",
                    tool_version="1.0.0",
                    rule_id="some-pattern",
                    rule_name="Some Pattern",
                    file_path="src/test.py",
                    line_start=1,
                    line_end=1,
                    severity=Severity.HIGH,
                    confidence=Confidence.HEURISTIC,
                    message="Heuristic finding",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

        findings_verified = [
            {
                "finding": NormalizedFinding(
                    tool="semgrep",
                    tool_version="1.0.0",
                    rule_id="some-pattern",
                    rule_name="Some Pattern",
                    file_path="src/test.py",
                    line_start=1,
                    line_end=1,
                    severity=Severity.HIGH,
                    confidence=Confidence.VERIFIED,
                    message="Verified finding",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

        result_heuristic = engine.calculate(findings_heuristic, ProjectType.WEB_APP.value, check_results)
        result_verified = engine.calculate(findings_verified, ProjectType.WEB_APP.value, check_results)

        # Heuristic should have higher score (less penalty)
        assert result_heuristic.overall_score > result_verified.overall_score

    def test_grade_bands(self, engine):
        """Test grade band boundaries."""
        # Create findings to get specific scores
        # This is a simplified test - in reality would need carefully crafted findings
        findings = []
        check_results = {
            "eslint": {"status": "passed"},
            "typescript": {"status": "passed"},
            "semgrep": {"status": "passed"},
            "trivy": {"status": "passed"},
            "detect_secrets": {"status": "passed"},
            "verification": {"status": "passed"},
            "profiler": {"status": "passed"},
            "readme": {"status": "passed"},
            "architecture": {"status": "passed"},
        }

        result = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)

        assert result.grade in ["A", "B", "C", "D", "F"]
        assert result.readiness_verdict in [
            "Production Ready",
            "Near Production",
            "Functional MVP",
            "Prototype",
            "Not Ready",
            "Insufficient Evidence",
            "Low Confidence",
            "Not Production Ready (Critical Blockers)",
        ]

    def test_coverage_calculation(self, engine, check_results):
        """Coverage should reflect evidenced checks."""
        # No findings but all checks run = 100% coverage
        findings = []
        result = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)
        assert result.coverage_percent == 100.0

    def test_confidence_calculation(self, engine, check_results):
        """Confidence should weight by finding confidence and severity."""
        findings_high_conf = [
            {
                "finding": NormalizedFinding(
                    tool="semgrep",
                    tool_version="1.0.0",
                    rule_id="test",
                    rule_name="Test",
                    file_path="src/test.py",
                    line_start=1,
                    line_end=1,
                    severity=Severity.HIGH,
                    confidence=Confidence.VERIFIED,
                    message="High confidence",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

        findings_low_conf = [
            {
                "finding": NormalizedFinding(
                    tool="semgrep",
                    tool_version="1.0.0",
                    rule_id="test",
                    rule_name="Test",
                    file_path="src/test.py",
                    line_start=1,
                    line_end=1,
                    severity=Severity.HIGH,
                    confidence=Confidence.HEURISTIC,
                    message="Low confidence",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

        result_high = engine.calculate(findings_high_conf, ProjectType.WEB_APP.value, check_results)
        result_low = engine.calculate(findings_low_conf, ProjectType.WEB_APP.value, check_results)

        # Higher confidence findings should result in higher confidence score
        assert result_high.confidence_percent > result_low.confidence_percent

    def test_critical_blocker_detection(self, engine, check_results):
        """Critical security findings should trigger blockers."""
        findings = [
            {
                "finding": NormalizedFinding(
                    tool="detect_secrets",
                    tool_version="1.0.0",
                    rule_id="aws-access-key",
                    rule_name="AWS Access Key",
                    file_path="config.py",
                    line_start=5,
                    line_end=5,
                    severity=Severity.CRITICAL,
                    confidence=Confidence.VERIFIED,
                    message="AWS secret detected",
                    metadata={},
                ),
                "dimensions": ["security_privacy"],
                "applicable": True,
            },
        ]

        result = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)

        assert result.critical_blockers == 1
        assert "Critical Blockers" in result.readiness_verdict

    def test_low_coverage_verdict(self, engine):
        """Low coverage should trigger insufficient evidence verdict."""
        # Simulate checks not run
        findings = []
        check_results = {
            "eslint": {"status": "not_run"},
            "typescript": {"status": "not_run"},
            "semgrep": {"status": "not_run"},
            "trivy": {"status": "not_run"},
            "detect_secrets": {"status": "not_run"},
            "verification": {"status": "not_run"},
            "profiler": {"status": "not_run"},
            "readme": {"status": "not_run"},
            "architecture": {"status": "not_run"},
        }

        result = engine.calculate(findings, ProjectType.WEB_APP.value, check_results)

        assert result.coverage_percent < 50
        assert result.readiness_verdict == "Insufficient Evidence"


class TestRubricLoading:
    """Test rubric loading and applicability."""

    def test_rubric_loads(self):
        rubric = get_rubric("v1")
        assert rubric.version == "1.0"
        assert len(rubric.dimensions) == 10

    def test_total_points(self):
        rubric = get_rubric("v1")
        total = sum(
            sc.points
            for dim in rubric.dimensions
            for sc in dim.subchecks
        )
        assert total == 100

    def test_applicability_rules(self):
        rubric = get_rubric("v1")

        # Web app should have all checks
        web_checks = rubric.get_applicable_subchecks(ProjectType.WEB_APP.value)
        web_points = sum(sc.points for sc in web_checks)

        # CLI should have fewer checks
        cli_checks = rubric.get_applicable_subchecks(ProjectType.CLI.value)
        cli_points = sum(sc.points for sc in cli_checks)

        assert cli_points < web_points

    def test_subcheck_lookup(self):
        rubric = get_rubric("v1")
        subcheck = rubric.get_subcheck("fc.build_success")
        assert subcheck is not None
        assert subcheck.points == 5

        # Non-existent
        assert rubric.get_subcheck("nonexistent") is None


class TestFindingDeduplication:
    """Test finding deduplication logic."""

    def test_same_tool_same_location_deduplicated(self):
        from app.services.finding_analysis import FindingAnalyzer

        analyzer = FindingAnalyzer()

        findings = [
            NormalizedFinding(
                tool="eslint",
                tool_version="8.0.0",
                rule_id="no-unused-vars",
                rule_name="Unused Variable",
                file_path="src/test.ts",
                line_start=10,
                line_end=10,
                severity=Severity.MEDIUM,
                confidence=Confidence.LIKELY,
                message="Unused variable",
                metadata={},
            ),
            NormalizedFinding(
                tool="eslint",
                tool_version="8.0.0",
                rule_id="no-unused-vars",
                rule_name="Unused Variable",
                file_path="src/test.ts",
                line_start=10,
                line_end=10,
                severity=Severity.HIGH,
                confidence=Confidence.VERIFIED,
                message="Unused variable (stricter)",
                metadata={},
            ),
        ]

        deduplicated = analyzer._deduplicate(findings)
        assert len(deduplicated) == 1
        # Should keep the higher severity one
        assert deduplicated[0].severity == Severity.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
