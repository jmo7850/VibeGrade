"""API routes for scans."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Confidence, FindingStatus, ScanStatus, Severity
from app.schemas import (
    ArchitectureResponse,
    DimensionScoreResponse,
    FindingResponse,
    HealthResponse,
    ReportResponse,
    ScanCreate,
    ScanHistoryResponse,
    ScanResponse,
    ScanStatusResponse,
    ScoreResponse,
)
from app.services.evidence import EvidenceStore
from app.services.intake import RepositoryIntake, RepositoryIntakeError

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
        sandbox="disabled" if not settings.sandbox_enabled else "enabled",
    )


@router.get("/history", response_model=list[ScanHistoryResponse])
async def get_scan_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get scan history with score summaries (anonymous for MVP)."""
    evidence_store = EvidenceStore(db)
    scans = await evidence_store.get_user_scans(user_id=None, limit=limit, offset=offset)

    from sqlalchemy import select as sa_select

    from app.models import Score

    result = await db.execute(
        sa_select(Score).where(Score.scan_id.in_([s.id for s in scans]))
    )
    scores_by_scan = {score.scan_id: score for score in result.scalars().all()}

    history = []
    for scan in scans:
        score = scores_by_scan.get(scan.id)
        history.append(ScanHistoryResponse(
            id=scan.id,
            repo_url=scan.repo_url,
            repo_owner=scan.repo_owner,
            repo_name=scan.repo_name,
            commit_sha=scan.commit_sha,
            branch=scan.branch,
            project_type=scan.project_type,
            status=scan.status,
            rubric_version=scan.rubric_version,
            error=scan.error,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            overall_score=score.overall_score if score else None,
            grade=score.grade if score else None,
            coverage_percent=score.coverage_percent if score else None,
            critical_blockers=score.critical_blockers if score else 0,
        ))
    return history


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan from a GitHub repository URL."""
    settings = get_settings()
    intake = RepositoryIntake()

    # Parse and validate the repository URL up front so the scan
    # record is created with accurate identity fields.
    try:
        owner, repo, branch, commit_sha = intake.parse_github_url(
            str(scan_data.repo_url)
        )
        repo_meta = await intake.validate_repository(owner, repo)
    except RepositoryIntakeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Create a single scan record; the orchestrator updates it in place.
    evidence_store = EvidenceStore(db)
    scan = await evidence_store.create_scan(
        repo_url=str(scan_data.repo_url),
        repo_owner=owner,
        repo_name=repo,
        commit_sha=commit_sha or repo_meta["default_branch"],
        branch=scan_data.branch or branch or repo_meta["default_branch"],
        project_type="unknown",
        rubric_version=settings.rubric_version,
    )

    import tempfile
    from pathlib import Path

    from app.services.orchestrator import ScanOrchestrator

    workspace = Path(tempfile.mkdtemp(prefix="vibegrade_"))
    orchestrator = ScanOrchestrator(db, workspace)

    try:
        await orchestrator.run_scan(
            scan=scan,
            repo_url=str(scan_data.repo_url),
            branch=scan_data.branch,
            commit_sha=scan_data.commit_sha,
            user_id=None,  # Anonymous for MVP
        )
    except Exception:
        # Failure status is already recorded on the scan by the orchestrator.
        pass

    await db.refresh(scan)
    return scan


@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get scan status and progress."""
    evidence_store = EvidenceStore(db)
    scan_data = await evidence_store.get_scan_with_details(scan_id)

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = scan_data["scan"]

    # Calculate progress based on status
    progress_map = {
        ScanStatus.PENDING: 0,
        ScanStatus.PROFILING: 10,
        ScanStatus.ANALYZING: 50,
        ScanStatus.SCORING: 90,
        ScanStatus.COMPLETE: 100,
        ScanStatus.FAILED: 100,
    }

    stage_map = {
        ScanStatus.PENDING: "Queued",
        ScanStatus.PROFILING: "Cloning repository",
        ScanStatus.ANALYZING: "Running analysis",
        ScanStatus.SCORING: "Calculating score",
        ScanStatus.COMPLETE: "Complete",
        ScanStatus.FAILED: "Failed",
    }

    return ScanStatusResponse(
        scan_id=scan.id,
        status=scan.status,
        progress=progress_map.get(scan.status, 0),
        current_stage=stage_map.get(scan.status, "Unknown"),
        error=scan.error,
    )


@router.get("/{scan_id}/report", response_model=ReportResponse)
async def get_scan_report(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full scan report."""
    evidence_store = EvidenceStore(db)
    scan_data = await evidence_store.get_scan_with_details(scan_id)

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = scan_data["scan"]
    score = scan_data["score"]
    findings = scan_data["findings"]
    checks = scan_data["checks"]

    if not score:
        raise HTTPException(status_code=404, detail="Report not yet available")

    # Convert findings to response format
    finding_responses = [
        FindingResponse(
            id=f.id,
            fingerprint=f.fingerprint,
            tool=f.tool,
            rule_id=f.rule_id,
            file_path=f.file_path,
            line_start=f.line_start,
            line_end=f.line_end,
            severity=f.severity,
            confidence=f.confidence,
            title=f.title,
            description=f.description,
            rubric_dimensions=f.rubric_dimensions,
            status=f.status,
            first_seen=f.first_seen,
            last_seen=f.last_seen,
        )
        for f in findings
    ]

    # Convert checks
    check_responses = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "status": c.status,
            "started_at": c.started_at,
            "completed_at": c.completed_at,
            "exit_code": c.exit_code,
            "duration_ms": c.duration_ms,
            "output_summary": c.output_summary,
        }
        for c in checks
    ]

    # Build dimension scores
    dimension_scores = [
        DimensionScoreResponse(**ds)
        for ds in score.dimension_scores
    ]

    return ReportResponse(
        scan=ScanResponse.model_validate(scan),
        score=ScoreResponse(
            overall_score=score.overall_score,
            grade=score.grade,
            readiness_verdict=score.readiness_verdict,
            coverage_percent=score.coverage_percent,
            confidence_percent=score.confidence_percent,
            critical_blockers=score.critical_blockers,
            dimension_scores=dimension_scores,
        ),
        findings=finding_responses,
        checks=check_responses,
        rubric_version=scan.rubric_version,
    )


@router.get("/{scan_id}/findings", response_model=list[FindingResponse])
async def get_scan_findings(
    scan_id: uuid.UUID,
    severity: list[Severity] | None = Query(None),
    confidence: list[Confidence] | None = Query(None),
    status: list[FindingStatus] | None = Query(None),
    dimension: str | None = Query(None),
    tool: str | None = Query(None),
    file_path: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get filtered findings for a scan."""
    evidence_store = EvidenceStore(db)
    scan_data = await evidence_store.get_scan_with_details(scan_id)

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    findings = scan_data["findings"]

    # Apply filters
    if severity:
        findings = [f for f in findings if f.severity in severity]
    if confidence:
        findings = [f for f in findings if f.confidence in confidence]
    if status:
        findings = [f for f in findings if f.status in status]
    if dimension:
        findings = [f for f in findings if dimension in f.rubric_dimensions]
    if tool:
        findings = [f for f in findings if f.tool == tool]
    if file_path:
        findings = [f for f in findings if file_path in f.file_path]

    # Paginate
    findings = findings[offset:offset + limit]

    return [
        FindingResponse(
            id=f.id,
            fingerprint=f.fingerprint,
            tool=f.tool,
            rule_id=f.rule_id,
            file_path=f.file_path,
            line_start=f.line_start,
            line_end=f.line_end,
            severity=f.severity,
            confidence=f.confidence,
            title=f.title,
            description=f.description,
            rubric_dimensions=f.rubric_dimensions,
            status=f.status,
            first_seen=f.first_seen,
            last_seen=f.last_seen,
        )
        for f in findings
    ]


@router.get("/{scan_id}/export")
async def export_scan_report(
    scan_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|markdown)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export a full assessment report (JSON or Markdown)."""
    import json as json_module
    from datetime import UTC, datetime

    from fastapi.responses import Response

    evidence_store = EvidenceStore(db)
    scan_data = await evidence_store.get_scan_with_details(scan_id)

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = scan_data["scan"]
    score = scan_data["score"]
    findings = scan_data["findings"]
    checks = scan_data["checks"]

    if not score:
        raise HTTPException(
            status_code=409,
            detail="Report not yet available (scan incomplete)",
        )

    report = {
        "vibegrade_report_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "rubric_version": scan.rubric_version,
        "scan": {
            "repository": f"{scan.repo_owner}/{scan.repo_name}",
            "repo_url": scan.repo_url,
            "commit_sha": scan.commit_sha,
            "branch": scan.branch,
            "project_type": scan.project_type.value,
            "status": scan.status.value,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        },
        "score": {
            "overall_score": score.overall_score,
            "grade": score.grade,
            "readiness_verdict": score.readiness_verdict,
            "coverage_percent": score.coverage_percent,
            "confidence_percent": score.confidence_percent,
            "critical_blockers": score.critical_blockers,
            "dimension_scores": score.dimension_scores,
        },
        "findings": [
            {
                "fingerprint": f.fingerprint,
                "tool": f.tool,
                "rule_id": f.rule_id,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "severity": f.severity.value,
                "confidence": f.confidence.value,
                "title": f.title,
                "description": f.description,
                "rubric_dimensions": f.rubric_dimensions,
                "status": f.status.value,
            }
            for f in findings
        ],
        "checks": [
            {
                "name": c.name,
                "category": c.category.value,
                "status": c.status.value,
                "exit_code": c.exit_code,
                "duration_ms": c.duration_ms,
                "output_summary": c.output_summary,
            }
            for c in checks
        ],
    }

    if format == "markdown":
        return Response(
            content=_render_markdown_report(report),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="vibegrade-{scan.repo_name}-{scan.commit_sha[:8]}.md"'
            },
        )

    return Response(
        content=json_module.dumps(report, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="vibegrade-{scan.repo_name}-{scan.commit_sha[:8]}.json"'
        },
    )


def _render_markdown_report(report: dict) -> str:
    """Render a markdown assessment report."""
    score = report["score"]
    scan = report["scan"]
    lines = [
        f"# VibeGrade Assessment: {scan['repository']}",
        "",
        f"- **Score:** {score['overall_score']}/100 (Grade {score['grade']})",
        f"- **Verdict:** {score['readiness_verdict']}",
        f"- **Coverage:** {score['coverage_percent']}% | **Confidence:** {score['confidence_percent']}%",
        f"- **Critical blockers:** {score['critical_blockers']}",
        f"- **Commit:** `{scan['commit_sha']}` ({scan['branch']})",
        f"- **Project type:** {scan['project_type']} | **Rubric:** {report['rubric_version']}",
        "",
        "## Dimension Scores",
        "",
        "| Dimension | Score | Weight | Checks | Findings |",
        "|---|---:|---:|---:|---:|",
    ]
    for dim in score["dimension_scores"]:
        lines.append(
            f"| {dim['name']} | {dim['score']:.0f}% | {dim['weight']} | "
            f"{dim['passed_checks']}/{dim['applicable_checks']} | {dim['findings_count']} |"
        )
    lines += ["", "## Findings", ""]
    if not report["findings"]:
        lines.append("_No findings recorded._")
    for i, f in enumerate(report["findings"], 1):
        lines += [
            f"### {i}. {f['title']}",
            "",
            f"- **Severity:** {f['severity']} | **Confidence:** {f['confidence']}",
            f"- **Tool:** {f['tool']} (`{f['rule_id']}`)",
            f"- **Location:** `{f['file_path']}:{f['line_start']}`",
            f"- **Dimensions:** {', '.join(f['rubric_dimensions']) or 'n/a'}",
            "",
            f["description"],
            "",
        ]
    lines += ["## Checks Executed", ""]
    for c in report["checks"]:
        lines.append(
            f"- **{c['name']}** ({c['category']}): {c['status']}"
            + (f" (exit {c['exit_code']})" if c.get("exit_code") is not None else "")
        )
    lines += [
        "",
        "---",
        "Generated by VibeGrade. Scores are evidence-based heuristics, not objective truth.",
    ]
    return "\n".join(lines)


@router.get("/{scan_id}/architecture", response_model=ArchitectureResponse)
async def get_scan_architecture(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get architecture inventory captured during the scan."""
    evidence_store = EvidenceStore(db)
    scan_data = await evidence_store.get_scan_with_details(scan_id)

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Architecture summary is stored as evidence on the internal_analysis check
    for check in scan_data["checks"]:
        if check.name == "internal_analysis" and check.evidence_ref:
            evidence = await evidence_store.get_evidence(check.evidence_ref)
            if evidence and "architecture" in evidence:
                arch = evidence["architecture"]
                return ArchitectureResponse(
                    project_type=arch.get("project_type", "unknown"),
                    languages=arch.get("languages", []),
                    frameworks=arch.get("frameworks", []),
                    package_managers=arch.get("package_managers", []),
                    entry_points=arch.get("entry_points", []),
                    modules=arch.get("modules", []),
                    dependencies=arch.get("dependencies", []),
                    file_counts=arch.get("file_counts", {}),
                    total_files=arch.get("total_files", 0),
                    has_database=arch.get("has_database", False),
                    has_dockerfile=arch.get("has_dockerfile", False),
                    has_ci=arch.get("has_ci", False),
                    inferred=arch.get("inferred", True),
                )

    raise HTTPException(
        status_code=404,
        detail="Architecture data not available for this scan",
    )
