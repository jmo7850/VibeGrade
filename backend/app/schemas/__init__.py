"""Pydantic schemas for API requests and responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import (
    CheckCategory,
    CheckStatus,
    Confidence,
    FindingStatus,
    ProjectType,
    ScanStatus,
    Severity,
)


# Scan Schemas
class ScanCreate(BaseModel):
    repo_url: HttpUrl
    branch: str | None = None
    commit_sha: str | None = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repo_url: str
    repo_owner: str
    repo_name: str
    commit_sha: str
    branch: str
    project_type: ProjectType
    status: ScanStatus
    rubric_version: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ScanStatusResponse(BaseModel):
    scan_id: uuid.UUID
    status: ScanStatus
    progress: int = Field(ge=0, le=100)
    current_stage: str
    error: str | None = None


# Check Schemas
class CheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: CheckCategory
    status: CheckStatus
    started_at: datetime | None
    completed_at: datetime | None
    exit_code: int | None
    duration_ms: int | None
    output_summary: str | None


# Finding Schemas
class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fingerprint: str
    tool: str
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    confidence: Confidence
    title: str
    description: str
    rubric_dimensions: list[str]
    status: FindingStatus
    first_seen: datetime
    last_seen: datetime


class FindingFilter(BaseModel):
    severity: list[Severity] | None = None
    confidence: list[Confidence] | None = None
    status: list[FindingStatus] | None = None
    dimension: str | None = None
    tool: str | None = None
    file_path: str | None = None


# Score Schemas
class DimensionScoreResponse(BaseModel):
    code: str
    name: str
    weight: int
    score: float
    max_score: int
    applicable_checks: int
    passed_checks: int
    findings_count: int


class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_score: int
    grade: str
    readiness_verdict: str
    coverage_percent: float
    confidence_percent: float
    critical_blockers: int
    dimension_scores: list[DimensionScoreResponse]


# Report Schema
class ReportResponse(BaseModel):
    scan: ScanResponse
    score: ScoreResponse
    findings: list[FindingResponse]
    checks: list[CheckResponse]
    rubric_version: str


# Rubric Schema
class RubricSubcheckSchema(BaseModel):
    id: str
    name: str
    points: int
    applies_to: list[str]
    not_applies_to: list[str] = []
    evidence_sources: list[str]
    description: str
    severity_map: dict[str, float]


class RubricDimensionSchema(BaseModel):
    code: str
    name: str
    weight: int
    description: str
    subchecks: list[RubricSubcheckSchema]


class RubricResponse(BaseModel):
    version: str
    description: str
    dimensions: list[RubricDimensionSchema]
    project_type_rules: dict[str, Any]
    severity_mapping: dict[str, dict[str, str]]
    confidence_by_category: dict[str, str]


# Health Check
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    sandbox: str


# Scan history with score summary
class ScanHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repo_url: str
    repo_owner: str
    repo_name: str
    commit_sha: str
    branch: str
    project_type: ProjectType
    status: ScanStatus
    rubric_version: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    # Score summary (joined from scores table; None until scan completes)
    overall_score: int | None = None
    grade: str | None = None
    coverage_percent: float | None = None
    critical_blockers: int = 0


# Architecture explorer response
class ArchitectureModuleSchema(BaseModel):
    name: str
    path: str
    file_count: int
    languages: list[str] = []


class ArchitectureDependencySchema(BaseModel):
    from_: str = Field(alias="from")
    to: str
    type: str = "import"


class ArchitectureResponse(BaseModel):
    project_type: str
    languages: list[str] = []
    frameworks: list[str] = []
    package_managers: list[str] = []
    entry_points: list[str] = []
    modules: list[ArchitectureModuleSchema] = []
    dependencies: list[ArchitectureDependencySchema] = []
    file_counts: dict[str, int] = {}
    total_files: int = 0
    has_database: bool = False
    has_dockerfile: bool = False
    has_ci: bool = False
    inferred: bool = True
