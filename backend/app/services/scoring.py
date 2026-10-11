"""Scoring engine - deterministic rubric-based scoring."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar

from app.core.logging import get_logger
from app.models import Confidence, Severity
from app.services.rubric import Dimension, Rubric, Subcheck, get_rubric
from app.services.static_analysis import NormalizedFinding

logger = get_logger(__name__)


@dataclass
class SubcheckScore:
    subcheck_id: str
    dimension_code: str
    points_possible: int
    points_earned: float
    status: str  # "passed", "failed", "skipped", "not_applicable"
    evidence_count: int
    finding_ids: list[str]


@dataclass
class DimensionScore:
    code: str
    name: str
    weight: int
    score: float  # 0-100
    max_score: int
    applicable_checks: int
    passed_checks: int
    findings_count: int


@dataclass
class ScoreResult:
    overall_score: int
    grade: str
    readiness_verdict: str
    coverage_percent: float
    confidence_percent: float
    critical_blockers: int
    dimension_scores: list[DimensionScore]
    subcheck_scores: list[SubcheckScore]


class ScoringEngine:
    """Deterministic scoring engine."""

    # Maps rubric evidence sources to the canonical check keys recorded by the
    # orchestrator. A subcheck is only considered "run" when at least one of its
    # evidence sources corresponds to a check that actually executed.
    EVIDENCE_SOURCE_TO_CHECK: ClassVar[dict[str, str]] = {
        "static.eslint": "eslint",
        "static.tsc": "typescript",
        "static.semgrep": "semgrep",
        "static.trivy": "trivy",
        "static.detect_secrets": "detect_secrets",
        "static.profiler": "profiler",
        "static.readme": "readme",
        "arch.imports": "architecture",
        "arch.dependency_graph": "architecture",
        "arch.complexity": "architecture",
        "arch.schema": "architecture",
        "arch.migrations": "architecture",
        "arch.openapi": "architecture",
        "arch.type_sharing": "architecture",
        "arch.network_calls": "architecture",
        "arch.orm_analysis": "architecture",
        "verification.build": "verification",
        "verification.test": "verification",
        "verification.workflow": "verification",
        "verification.e2e": "verification",
        "verification.run": "verification",
    }

    # Check execution statuses that count as "this check ran and produced evidence".
    RAN_STATUSES: ClassVar[frozenset[str]] = frozenset({"passed", "failed", "error"})

    GRADE_BANDS: ClassVar[list[tuple[int, str, str]]] = [
        (90, "A", "Production Ready"),
        (80, "B", "Near Production"),
        (70, "C", "Functional MVP"),
        (60, "D", "Prototype"),
        (0, "F", "Not Ready"),
    ]

    def __init__(self, rubric: Rubric | None = None):
        self.rubric = rubric or get_rubric()

    def calculate(
        self,
        findings: list[dict[str, Any]],
        project_type: str,
        check_results: dict[str, Any],
    ) -> ScoreResult:
        """
        Calculate score from findings and check results.

        Args:
            findings: Enriched findings from FindingAnalyzer
            project_type: Detected project type
            check_results: Dict of check_name -> {status, exit_code, parsed_output, etc.}

        Returns:
            ScoreResult with all scoring details
        """
        # 1. Get applicable subchecks
        applicable_subchecks = self.rubric.get_applicable_subchecks(project_type)

        # 2. Map findings to subchecks
        subcheck_evidence = self._map_findings_to_subchecks(findings, applicable_subchecks)

        # 3. Determine which subchecks had their checks run
        subcheck_check_status = self._get_subcheck_check_status(applicable_subchecks, check_results)

        # 4. Score each subcheck
        subcheck_scores = []
        for subcheck in applicable_subchecks:
            evidence = subcheck_evidence.get(subcheck.id, [])
            check_status = subcheck_check_status.get(subcheck.id, "not_run")
            score = self._score_subcheck(subcheck, evidence, check_status)
            subcheck_scores.append(score)

        # 4. Aggregate by dimension
        dimension_scores = self._aggregate_dimensions(subcheck_scores)

        # 5. Calculate overall score
        overall_score = self._calculate_overall(dimension_scores)

        # 6. Calculate coverage
        coverage = self._calculate_coverage(subcheck_scores, applicable_subchecks)

        # 7. Calculate confidence
        confidence = self._calculate_confidence(findings)

        # 8. Detect critical blockers
        critical_blockers = self._detect_critical_blockers(findings)

        # 9. Determine grade and verdict
        grade, verdict = self._determine_grade_and_verdict(
            overall_score, coverage, confidence, critical_blockers
        )

        return ScoreResult(
            overall_score=overall_score,
            grade=grade,
            readiness_verdict=verdict,
            coverage_percent=coverage,
            confidence_percent=confidence,
            critical_blockers=critical_blockers,
            dimension_scores=dimension_scores,
            subcheck_scores=subcheck_scores,
        )

    def _map_findings_to_subchecks(
        self,
        findings: list[dict[str, Any]],
        applicable_subchecks: list[Subcheck],
    ) -> dict[str, list[dict[str, Any]]]:
        """Map findings to subchecks they provide evidence for."""
        subcheck_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # For each finding, find relevant subchecks
        for finding_data in findings:
            finding = finding_data["finding"]
            dimensions = finding_data["dimensions"]

            # Find subchecks in those dimensions
            for dim_code in dimensions:
                dim = self._get_dimension(dim_code)
                if not dim:
                    continue
                for subcheck in dim.subchecks:
                    if subcheck in applicable_subchecks:
                        # Check if finding is relevant to this subcheck
                        if self._finding_relevant_to_subcheck(finding, subcheck):
                            subcheck_evidence[subcheck.id].append(finding_data)

        return subcheck_evidence

    def _get_subcheck_check_status(
        self,
        applicable_subchecks: list[Subcheck],
        check_results: dict[str, Any],
    ) -> dict[str, str]:
        """Determine the check status for each subcheck based on check_results.

        Scoring integrity rule: a subcheck only counts as executed when at least
        one of its evidence sources maps to a check that actually ran. Missing or
        skipped checks are reported as "not_run" and score as skipped — they are
        never treated as passes.
        """
        status_map: dict[str, str] = {}

        for subcheck in applicable_subchecks:
            ran = False
            for source in subcheck.evidence_sources:
                check_key = self.EVIDENCE_SOURCE_TO_CHECK.get(source)
                if check_key is None:
                    # Unknown evidence source: conservatively treated as not run.
                    continue
                result = check_results.get(check_key)
                if result is None:
                    continue
                status = (
                    result.get("status", "not_run")
                    if isinstance(result, dict)
                    else str(result)
                )
                if status in self.RAN_STATUSES:
                    ran = True
                    break
            status_map[subcheck.id] = "passed" if ran else "not_run"

        return status_map

    def _get_dimension(self, code: str) -> Dimension | None:
        for dim in self.rubric.dimensions:
            if dim.code == code:
                return dim
        return None

    def _finding_relevant_to_subcheck(
        self, finding: NormalizedFinding, subcheck: Subcheck
    ) -> bool:
        """Check if a finding provides evidence for a subcheck."""
        # Use evidence_sources from subcheck
        for source in subcheck.evidence_sources:
            if source == "static.eslint" and finding.tool == "eslint":
                return True
            if source == "static.tsc" and finding.tool == "typescript":
                return True
            if source == "static.semgrep" and finding.tool == "semgrep":
                return True
            if source == "static.trivy" and finding.tool == "trivy":
                return True
            if source == "static.detect_secrets" and finding.tool == "detect_secrets":
                return True
            if source == "verification.build" and "build" in finding.tool:
                return True
            if source == "verification.test" and finding.tool == "verification":
                return True
            if source == "verification.workflow" and "workflow" in finding.tool:
                return True
            if source.startswith("arch.") and finding.tool.startswith("arch."):
                return True
            # Fallback: if tool matches source prefix
            if source.startswith("static.") and finding.tool == source.replace("static.", ""):
                return True
            if source.startswith("verification.") and finding.tool == "verification":
                return True
            if source.startswith("arch.") and finding.tool.startswith("arch."):
                return True
        return False

    def _score_subcheck(
        self,
        subcheck: Subcheck,
        evidence: list[dict[str, Any]],
        check_status: str,
    ) -> SubcheckScore:
        """Score a single subcheck based on evidence and check status."""
        if not evidence:
            if check_status == "not_run":
                return SubcheckScore(
                    subcheck_id=subcheck.id,
                    dimension_code=self._get_dimension_for_subcheck(subcheck.id).code,
                    points_possible=subcheck.points,
                    points_earned=0.0,
                    status="skipped",
                    evidence_count=0,
                    finding_ids=[],
                )
            else:
                # Check ran but no findings = passed
                return SubcheckScore(
                    subcheck_id=subcheck.id,
                    dimension_code=self._get_dimension_for_subcheck(subcheck.id).code,
                    points_possible=subcheck.points,
                    points_earned=float(subcheck.points),
                    status="passed",
                    evidence_count=0,
                    finding_ids=[],
                )

        # Calculate penalty from findings
        total_penalty = 0.0
        finding_ids = []

        for finding_data in evidence:
            finding = finding_data["finding"]
            confidence = finding.confidence  # Use finding's confidence attribute

            # Get severity penalty weight
            severity_weight = self._get_severity_weight(finding.severity)

            # Get confidence weight
            confidence_weight = self._get_confidence_weight(confidence)

            # Get subcheck-specific severity mapping
            severity_map = subcheck.severity_map
            if finding.severity.value in severity_map:
                base_penalty = severity_map[finding.severity.value]
            else:
                base_penalty = severity_weight

            penalty = base_penalty * confidence_weight
            total_penalty += penalty
            finding_ids.append(finding.rule_id)

        # Cap penalty at 1.0 (100% of points)
        total_penalty = min(total_penalty, 1.0)

        points_earned = subcheck.points * (1.0 - total_penalty)

        return SubcheckScore(
            subcheck_id=subcheck.id,
            dimension_code=self._get_dimension_for_subcheck(subcheck.id).code,
            points_possible=subcheck.points,
            points_earned=round(points_earned, 2),
            status="passed" if total_penalty == 0 else "failed",
            evidence_count=len(evidence),
            finding_ids=finding_ids,
        )

    def _get_dimension_for_subcheck(self, subcheck_id: str) -> Dimension | None:
        for dim in self.rubric.dimensions:
            for sc in dim.subchecks:
                if sc.id == subcheck_id:
                    return dim
        return None

    def _get_severity_weight(self, severity: Severity) -> float:
        """Weight for severity level."""
        weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.7,
            Severity.MEDIUM: 0.4,
            Severity.LOW: 0.2,
            Severity.INFO: 0.1,
        }
        return weights.get(severity, 0.1)

    def _get_confidence_weight(self, confidence: Confidence) -> float:
        """Weight for confidence level."""
        weights = {
            Confidence.VERIFIED: 1.0,
            Confidence.LIKELY: 0.7,
            Confidence.HEURISTIC: 0.4,
            Confidence.INFO: 0.2,
        }
        return weights.get(confidence, 0.5)

    def _aggregate_dimensions(self, subcheck_scores: list[SubcheckScore]) -> list[DimensionScore]:
        """Aggregate subcheck scores by dimension."""
        dim_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "points_earned": 0.0,
            "points_possible": 0,
            "applicable_checks": 0,
            "passed_checks": 0,
            "findings_count": 0,
        })

        for sc in subcheck_scores:
            dim = dim_data[sc.dimension_code]
            dim["points_earned"] += sc.points_earned
            dim["points_possible"] += sc.points_possible
            if sc.status != "skipped":
                dim["applicable_checks"] += 1
            if sc.status == "passed":
                dim["passed_checks"] += 1
            dim["findings_count"] += sc.evidence_count

        dimension_scores = []
        for dim in self.rubric.dimensions:
            data = dim_data.get(dim.code, {
                "points_earned": 0.0,
                "points_possible": 0,
                "applicable_checks": 0,
                "passed_checks": 0,
                "findings_count": 0,
            })

            if data["points_possible"] > 0:
                score = (data["points_earned"] / data["points_possible"]) * 100
            else:
                score = 0.0

            dimension_scores.append(DimensionScore(
                code=dim.code,
                name=dim.name,
                weight=dim.weight,
                score=round(score, 1),
                max_score=dim.weight,
                applicable_checks=data["applicable_checks"],
                passed_checks=data["passed_checks"],
                findings_count=data["findings_count"],
            ))

        return dimension_scores

    def _calculate_overall(self, dimension_scores: list[DimensionScore]) -> int:
        """Calculate overall weighted score."""
        # Only include dimensions that have applicable checks
        scored_dimensions = [ds for ds in dimension_scores if ds.applicable_checks > 0]
        if not scored_dimensions:
            return 0

        total_weight = sum(ds.weight for ds in scored_dimensions)
        if total_weight == 0:
            return 0

        weighted_sum = sum(ds.score * ds.weight for ds in scored_dimensions)
        return round(weighted_sum / total_weight)

    def _calculate_coverage(
        self, subcheck_scores: list[SubcheckScore], applicable_subchecks: list[Subcheck]
    ) -> float:
        """Calculate assessment coverage."""
        if not applicable_subchecks:
            return 0.0

        # Coverage = subchecks that were run (not skipped) / applicable subchecks that could be run
        run_checks = sum(1 for sc in subcheck_scores if sc.status != "skipped")
        runnable_checks = sum(1 for sc in subcheck_scores if sc.status != "not_applicable")
        if runnable_checks == 0:
            return 0.0
        return round((run_checks / runnable_checks) * 100, 1)

    def _calculate_confidence(self, findings: list[dict[str, Any]]) -> float:
        """Calculate overall confidence."""
        if not findings:
            return 100.0  # No findings = high confidence in clean result

        confidence_weights = {
            Confidence.VERIFIED: 1.0,
            Confidence.LIKELY: 0.7,
            Confidence.HEURISTIC: 0.4,
            Confidence.INFO: 0.2,
        }

        severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.3,
            Severity.INFO: 0.1,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for finding_data in findings:
            finding = finding_data["finding"]
            conf_weight = confidence_weights.get(finding.confidence, 0.5)
            sev_weight = severity_weights.get(finding.severity, 0.5)
            combined = conf_weight * sev_weight

            total_weight += combined
            weighted_sum += conf_weight * combined

        if total_weight == 0:
            return 100.0

        # Return the average confidence weight across all findings
        return round((weighted_sum / total_weight) * 100, 1)

    def _detect_critical_blockers(self, findings: list[dict[str, Any]]) -> int:
        """Detect critical security blockers."""
        blockers = 0
        for finding_data in findings:
            finding = finding_data["finding"]
            if (finding.severity == Severity.CRITICAL and
                finding.confidence in (Confidence.VERIFIED, Confidence.LIKELY) and
                "security_privacy" in finding_data["dimensions"]):
                blockers += 1
        return blockers

    def _determine_grade_and_verdict(
        self,
        score: int,
        coverage: float,
        confidence: float,
        critical_blockers: int,
    ) -> tuple[str, str]:
        """Determine grade and readiness verdict."""
        # Base grade from score
        grade = "F"
        verdict = "Not Ready"
        for min_score, g, v in self.GRADE_BANDS:
            if score >= min_score:
                grade = g
                verdict = v
                break

        # Critical blockers override everything
        if critical_blockers > 0:
            verdict = "Not Production Ready (Critical Blockers)"

        # Low coverage override (but not if critical blockers already set)
        if coverage < 50 and critical_blockers == 0:
            verdict = "Insufficient Evidence"

        # Low confidence override
        if confidence < 40 and critical_blockers == 0:
            verdict = "Low Confidence"

        return grade, verdict
