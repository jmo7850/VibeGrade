"""Main scan orchestrator."""

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import (
    CheckCategory,
    CheckStatus,
    Confidence,
    ProjectType,
    ScanStatus,
    Severity,
    VerificationStatus,
)
from app.services.evidence import EvidenceStore
from app.services.finding_analysis import FindingAnalyzer
from app.services.intake import RepositoryIntake, RepositoryIntakeError
from app.services.internal_checks import InternalChecksEngine
from app.services.profiler import ProjectProfiler
from app.services.sandbox import SandboxVerificationEngine
from app.services.scoring import ScoreResult, ScoringEngine
from app.services.static_analysis import NormalizedFinding, StaticAnalysisEngine

logger = get_logger(__name__)


class ScanOrchestrator:
    """Orchestrates the complete scan pipeline.

    The orchestrator updates the scan record passed in by the caller
    (typically the API layer). It never creates a second scan record.

    Runtime verification (install/build/test) is only executed when
    sandbox isolation is enabled. Without isolation, untrusted commands
    are NOT executed on the host — verification checks are recorded as
    skipped and disclosed in the report.
    """

    def __init__(self, session: AsyncSession, workspace: Path):
        self.session = session
        self.workspace = workspace
        self.settings = get_settings()
        self.evidence_store = EvidenceStore(session)
        self.intake = RepositoryIntake()
        self.profiler = ProjectProfiler()
        self.static_analyzer = StaticAnalysisEngine()
        self.internal_checks = InternalChecksEngine()
        self.finding_analyzer = FindingAnalyzer()
        self.scoring_engine = ScoringEngine()

    async def run_scan(
        self,
        scan,
        repo_url: str,
        branch: str | None = None,
        commit_sha: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ScoreResult:
        """Run complete scan pipeline on an existing scan record."""
        repo_workspace = None

        try:
            # Stage 1: Repository Intake
            logger.info("Starting repository intake", repo_url=repo_url)
            await self.evidence_store.update_scan_status(scan.id, ScanStatus.PROFILING)

            owner, repo, detected_branch, detected_commit = self.intake.parse_github_url(repo_url)
            branch = branch or detected_branch
            commit_sha = commit_sha or detected_commit

            repo_meta = await self.intake.validate_repository(owner, repo)

            scan.repo_owner = owner
            scan.repo_name = repo
            scan.branch = branch or repo_meta["default_branch"]
            scan.commit_sha = commit_sha or repo_meta["default_branch"]
            scan.project_type = ProjectType.UNKNOWN
            scan.user_id = user_id
            await self.session.flush()

            repo_workspace, resolved_sha = await self.intake.clone_repository(
                owner=owner,
                repo=repo,
                commit_sha=commit_sha,
                branch=branch,
            )
            scan.commit_sha = resolved_sha
            await self.session.flush()

            # Stage 2: Project Profiling
            logger.info("Starting project profiling")
            await self.evidence_store.update_scan_status(scan.id, ScanStatus.ANALYZING)

            profile = await self.profiler.analyze(repo_workspace)
            scan.project_type = profile.project_type
            await self.session.flush()

            # Stage 3: Static Analysis (external tools)
            logger.info("Starting static analysis")
            static_check = await self.evidence_store.create_check(
                scan_id=scan.id,
                name="static_analysis",
                category=CheckCategory.STATIC,
            )
            await self.evidence_store.update_check_status(static_check.id, CheckStatus.RUNNING)

            static_findings = await self.static_analyzer.analyze(repo_workspace, profile)
            static_tools_ran = {f.tool for f in static_findings}

            # Record which external tools actually executed. A tool that is
            # not installed in this environment records 'not_run' so the
            # scoring engine treats its subchecks as skipped, not passed.
            tool_check_results = self._probe_tool_availability()

            await self.evidence_store.store_evidence(
                static_check.id,
                {
                    "findings_count": len(static_findings),
                    "tools_run": sorted(static_tools_ran),
                    "tools_available": {
                        k: v["status"] for k, v in tool_check_results.items()
                    },
                },
            )
            await self.evidence_store.update_check_status(
                static_check.id, CheckStatus.PASSED, exit_code=0, duration_ms=0
            )

            # Stage 3b: Internal deterministic checks (profiler/readme/architecture)
            logger.info("Starting internal checks")
            internal_check = await self.evidence_store.create_check(
                scan_id=scan.id,
                name="internal_analysis",
                category=CheckCategory.STATIC,
            )
            await self.evidence_store.update_check_status(internal_check.id, CheckStatus.RUNNING)

            internal_findings, architecture_summary = await self.internal_checks.analyze(
                repo_workspace, profile
            )

            await self.evidence_store.store_evidence(
                internal_check.id,
                {
                    "findings_count": len(internal_findings),
                    "architecture": architecture_summary.__dict__,
                },
            )
            await self.evidence_store.update_check_status(
                internal_check.id, CheckStatus.PASSED, exit_code=0, duration_ms=0
            )

            # Stage 4: Verification (build & test) — sandbox-gated
            logger.info("Starting verification")
            verification_check = await self.evidence_store.create_check(
                scan_id=scan.id,
                name="verification",
                category=CheckCategory.VERIFICATION,
            )
            await self.evidence_store.update_check_status(verification_check.id, CheckStatus.RUNNING)

            verification_results = []
            verification_status = "not_run"
            if self.settings.sandbox_enabled:
                verification_engine = SandboxVerificationEngine(repo_workspace, profile)
                verification_results = await verification_engine.run_all()
                verification_status = (
                    "passed"
                    if all(r.status == VerificationStatus.PASSED for r in verification_results)
                    else "failed"
                )
                for vr in verification_results:
                    await self.evidence_store.store_verification_result(verification_check.id, vr)
                await self.evidence_store.update_check_status(
                    verification_check.id,
                    CheckStatus.PASSED if verification_status == "passed" else CheckStatus.FAILED,
                    exit_code=0,
                )
            else:
                # Security boundary: untrusted build/test commands are never
                # executed without isolated sandbox infrastructure.
                await self.evidence_store.update_check_status(
                    verification_check.id, CheckStatus.SKIPPED
                )
                await self.evidence_store.store_evidence(
                    verification_check.id,
                    {
                        "status": "skipped",
                        "reason": "sandbox_disabled",
                        "detail": (
                            "Build and test execution requires an isolated sandbox. "
                            "Runtime verification is disabled in this deployment "
                            "(SANDBOX_ENABLED=false); functional correctness is "
                            "assessed from static evidence only."
                        ),
                        "commands_would_run": {
                            "install": profile.install_commands,
                            "build": profile.build_commands,
                            "test": profile.test_commands,
                        },
                    },
                )

            # Stage 5: Finding Analysis
            logger.info("Starting finding analysis")
            all_findings = list(static_findings) + list(internal_findings)

            # Verification failures become pseudo-findings with verified confidence
            for vr in verification_results:
                parsed = vr.parsed_output or {}
                if vr.status in (VerificationStatus.FAILED, VerificationStatus.ERROR):
                    rule_id = (
                        "test_failure"
                        if "test" in vr.name
                        else "build_failure"
                        if "build" in vr.name
                        else "install_failure"
                    )
                    all_findings.append(NormalizedFinding(
                        tool="verification",
                        tool_version="internal",
                        rule_id=rule_id,
                        rule_name="Verification Failed",
                        file_path="verification",
                        line_start=1,
                        line_end=1,
                        severity=Severity.HIGH,
                        confidence=Confidence.VERIFIED,
                        message=f"{vr.name} failed (exit {vr.exit_code}): {vr.stderr[:200]}",
                        metadata={"parsed_output": parsed},
                    ))

            enriched_findings = self.finding_analyzer.analyze(all_findings, profile.project_type.value)

            for finding_data in enriched_findings:
                await self.evidence_store.store_findings(
                    scan_id=scan.id,
                    check_id=static_check.id,
                    findings=[finding_data["finding"]],
                )

            # Stage 6: Scoring
            logger.info("Starting scoring")
            await self.evidence_store.update_scan_status(scan.id, ScanStatus.SCORING)

            check_results: dict[str, dict[str, Any]] = {
                **tool_check_results,
                "profiler": {"status": "passed"},
                "readme": {"status": "passed"},
                "architecture": {"status": "passed"},
                "verification": {"status": verification_status},
            }

            score_result = self.scoring_engine.calculate(
                findings=enriched_findings,
                project_type=profile.project_type.value,
                check_results=check_results,
            )

            # Stage 7: Store Score (with full scoring traceability)
            await self.evidence_store.store_score(
                scan_id=scan.id,
                overall_score=score_result.overall_score,
                coverage_percent=score_result.coverage_percent,
                confidence_percent=score_result.confidence_percent,
                grade=score_result.grade,
                readiness_verdict=score_result.readiness_verdict,
                critical_blockers=score_result.critical_blockers,
                dimension_scores=[
                    {
                        "code": ds.code,
                        "name": ds.name,
                        "weight": ds.weight,
                        "score": ds.score,
                        "max_score": ds.max_score,
                        "applicable_checks": ds.applicable_checks,
                        "passed_checks": ds.passed_checks,
                        "findings_count": ds.findings_count,
                    }
                    for ds in score_result.dimension_scores
                ],
            )

            # Store subcheck-level scoring evidence for reproducibility
            scoring_check = await self.evidence_store.create_check(
                scan_id=scan.id,
                name="scoring",
                category=CheckCategory.STATIC,
            )
            await self.evidence_store.store_evidence(
                scoring_check.id,
                {
                    "rubric_version": scan.rubric_version,
                    "project_type": profile.project_type.value,
                    "check_results": check_results,
                    "subcheck_scores": [
                        {
                            "subcheck_id": sc.subcheck_id,
                            "dimension_code": sc.dimension_code,
                            "points_possible": sc.points_possible,
                            "points_earned": sc.points_earned,
                            "status": sc.status,
                            "evidence_count": sc.evidence_count,
                            "finding_ids": sc.finding_ids,
                        }
                        for sc in score_result.subcheck_scores
                    ],
                },
            )
            await self.evidence_store.update_check_status(
                scoring_check.id, CheckStatus.PASSED, exit_code=0, duration_ms=0
            )

            await self.evidence_store.update_scan_status(scan.id, ScanStatus.COMPLETE)
            logger.info("Scan completed", scan_id=scan.id, score=score_result.overall_score)

            return score_result

        except RepositoryIntakeError as e:
            logger.error("Repository intake failed", error=str(e))
            await self.evidence_store.update_scan_status(scan.id, ScanStatus.FAILED, error=str(e))
            raise
        except Exception as e:
            logger.exception("Scan failed", error=str(e))
            await self.evidence_store.update_scan_status(scan.id, ScanStatus.FAILED, error=str(e))
            raise
        finally:
            if repo_workspace:
                self.intake.cleanup_workspace(repo_workspace)

    def _probe_tool_availability(self) -> dict[str, dict[str, str]]:
        """Probe which external analysis tools are installed.

        A tool that is not installed records 'not_run' so the scoring
        engine treats its subchecks as skipped, not passed.
        """
        import shutil

        availability: dict[str, dict[str, str]] = {}
        for tool in ("eslint", "tsc", "semgrep", "trivy", "detect-secrets"):
            check_key = {
                "tsc": "typescript",
                "detect-secrets": "detect_secrets",
            }.get(tool, tool)
            available = shutil.which(tool) is not None
            availability[check_key] = {
                "status": "passed" if available else "not_run",
                "tool_installed": available,
            }
        return availability
