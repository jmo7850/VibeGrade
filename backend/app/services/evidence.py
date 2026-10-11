"""Evidence store for persisting scan evidence."""

import gzip
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Check,
    CheckCategory,
    CheckStatus,
    EvidenceBlob,
    Finding,
    Scan,
    ScanStatus,
    Score,
)
from app.services.static_analysis import NormalizedFinding
from app.services.verification import VerificationResult

logger = get_logger(__name__)


class EvidenceStore:
    """Manages persistence of scan evidence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scan(
        self,
        repo_url: str,
        repo_owner: str,
        repo_name: str,
        commit_sha: str,
        branch: str,
        project_type: str,
        rubric_version: str,
        user_id: uuid.UUID | None = None,
    ) -> Scan:
        """Create a new scan record."""
        scan = Scan(
            user_id=user_id,
            repo_url=repo_url,
            repo_owner=repo_owner,
            repo_name=repo_name,
            commit_sha=commit_sha,
            branch=branch,
            project_type=project_type,
            status=ScanStatus.PENDING,
            rubric_version=rubric_version,
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def update_scan_status(
        self,
        scan_id: uuid.UUID,
        status: ScanStatus,
        error: str | None = None,
    ) -> None:
        """Update scan status."""
        scan = await self.session.get(Scan, scan_id)
        if scan:
            scan.status = status
            if status in (ScanStatus.COMPLETE, ScanStatus.FAILED):
                scan.completed_at = datetime.now(UTC)
            elif status == ScanStatus.ANALYZING:
                scan.started_at = datetime.now(UTC)
            if error:
                scan.error = error
            await self.session.flush()

    async def create_check(
        self,
        scan_id: uuid.UUID,
        name: str,
        category: CheckCategory,
    ) -> Check:
        """Create a check record."""
        check = Check(
            scan_id=scan_id,
            name=name,
            category=category,
            status=CheckStatus.PENDING,
        )
        self.session.add(check)
        await self.session.flush()
        return check

    async def update_check_status(
        self,
        check_id: uuid.UUID,
        status: CheckStatus,
        exit_code: int | None = None,
        duration_ms: int | None = None,
        output_summary: str | None = None,
    ) -> None:
        """Update check status."""
        check = await self.session.get(Check, check_id)
        if check:
            check.status = status
            if status == CheckStatus.RUNNING:
                check.started_at = datetime.now(UTC)
            elif status in (CheckStatus.PASSED, CheckStatus.FAILED, CheckStatus.SKIPPED, CheckStatus.ERROR):
                check.completed_at = datetime.now(UTC)
            if exit_code is not None:
                check.exit_code = exit_code
            if duration_ms is not None:
                check.duration_ms = duration_ms
            if output_summary is not None:
                check.output_summary = output_summary[:500] if output_summary else None
            await self.session.flush()

    async def store_evidence(
        self,
        check_id: uuid.UUID,
        content: dict[str, Any],
        content_type: str = "application/json",
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceBlob:
        """Store evidence blob for a check."""
        # Compress if large
        content_bytes = json.dumps(content, default=str).encode("utf-8")
        if len(content_bytes) > 1024:
            content_bytes = gzip.compress(content_bytes)
            content_type += "+gzip"

        evidence = EvidenceBlob(
            check_id=check_id,
            content_type=content_type,
            content=content_bytes,
            blob_metadata=metadata or {},
        )
        self.session.add(evidence)
        await self.session.flush()

        # Update check with evidence reference
        check = await self.session.get(Check, check_id)
        if check:
            check.evidence_ref = evidence.id
            await self.session.flush()

        return evidence

    async def get_evidence(self, evidence_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve and decompress evidence."""
        evidence = await self.session.get(EvidenceBlob, evidence_id)
        if not evidence:
            return None

        content = evidence.content
        if evidence.content_type.endswith("+gzip"):
            content = gzip.decompress(content)

        return json.loads(content.decode("utf-8"))

    async def store_findings(
        self,
        scan_id: uuid.UUID,
        check_id: uuid.UUID,
        findings: list[NormalizedFinding],
        evidence_ref: uuid.UUID | None = None,
    ) -> list[Finding]:
        """Store normalized findings."""
        db_findings = []
        for finding in findings:
            # Create fingerprint for deduplication
            fingerprint = f"{finding.tool}:{finding.rule_id}:{finding.file_path}:{finding.line_start}"

            db_finding = Finding(
                scan_id=scan_id,
                check_id=check_id,
                fingerprint=fingerprint,
                tool=finding.tool,
                rule_id=finding.rule_id,
                file_path=finding.file_path,
                line_start=finding.line_start,
                line_end=finding.line_end,
                severity=finding.severity,
                confidence=finding.confidence,
                title=finding.rule_name,
                description=finding.message,
                evidence_ref=evidence_ref,
                rubric_dimensions=[],  # Will be populated by finding analyzer
            )
            self.session.add(db_finding)
            db_findings.append(db_finding)

        await self.session.flush()
        return db_findings

    async def store_verification_result(
        self,
        check_id: uuid.UUID,
        result: VerificationResult,
    ) -> EvidenceBlob:
        """Store verification result."""
        content = {
            "command": result.command,
            "status": result.status.value,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "parsed_output": result.parsed_output,
        }
        return await self.store_evidence(
            check_id=check_id,
            content=content,
            content_type="application/json",
            metadata={"verification": True},
        )

    async def store_score(
        self,
        scan_id: uuid.UUID,
        overall_score: int,
        coverage_percent: float,
        confidence_percent: float,
        grade: str,
        readiness_verdict: str,
        critical_blockers: int,
        dimension_scores: dict[str, Any],
    ) -> Score:
        """Store final score."""
        score = Score(
            scan_id=scan_id,
            overall_score=overall_score,
            coverage_percent=coverage_percent,
            confidence_percent=confidence_percent,
            grade=grade,
            readiness_verdict=readiness_verdict,
            critical_blockers=critical_blockers,
            dimension_scores=dimension_scores,
        )
        self.session.add(score)
        await self.session.flush()
        return score

    async def get_scan_with_details(self, scan_id: uuid.UUID) -> dict[str, Any] | None:
        """Get complete scan data for report generation."""
        # Get scan
        scan = await self.session.get(Scan, scan_id)
        if not scan:
            return None

        # Get score
        score_result = await self.session.execute(
            select(Score).where(Score.scan_id == scan_id)
        )
        score = score_result.scalar_one_or_none()

        # Get checks
        checks_result = await self.session.execute(
            select(Check).where(Check.scan_id == scan_id).order_by(Check.created_at)
        )
        checks = list(checks_result.scalars().all())

        # Get findings
        findings_result = await self.session.execute(
            select(Finding).where(Finding.scan_id == scan_id).order_by(Finding.severity.desc(), Finding.first_seen)
        )
        findings = list(findings_result.scalars().all())

        return {
            "scan": scan,
            "score": score,
            "checks": checks,
            "findings": findings,
        }

    async def get_user_scans(
        self,
        user_id: uuid.UUID | None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Scan]:
        """Get scans for a user."""
        query = select(Scan).order_by(Scan.created_at.desc()).limit(limit).offset(offset)
        if user_id:
            query = query.where(Scan.user_id == user_id)
        else:
            # Anonymous scans - would need session tracking
            query = query.where(Scan.user_id.is_(None))

        result = await self.session.execute(query)
        return list(result.scalars().all())
