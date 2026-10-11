# VibeGrade — System Architecture

**Version:** 1.0
**Date:** October 11, 2026
**Scope:** Phases 1-2 (MVP + Secure Runtime Verification)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VIBEGRADE SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   Frontend   │◀──▶│   API Gateway│◀──▶│  Core Engine │◀──▶│ Database │  │
│  │  (React/TS)  │    │  (FastAPI)   │    │  (Orchestr.) │    │ (SQLite) │  │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘    └──────────┘  │
│                             │                   │                            │
│                    ┌────────┴────────┐          │                            │
│                    ▼                 ▼          ▼                            │
│           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│           │ Repository    │  │ Static        │  │ Verification  │          │
│           │ Intake        │  │ Analysis      │  │ Engine        │          │
│           └───────────────┘  └───────────────┘  └───────────────┘          │
│                    │                 │                 │                    │
│                    ▼                 ▼                 ▼                    │
│           ┌─────────────────────────────────────────────────────┐          │
│           │              EVIDENCE STORE                          │          │
│           │  (Normalized findings, tool output, execution logs) │          │
│           └─────────────────────────────────────────────────────┘          │
│                                    │                                       │
│                                    ▼                                       │
│           ┌─────────────────────────────────────────────────────┐          │
│           │           FINDING ANALYSIS & SCORING                │          │
│           │  Deduplication → Severity → Confidence → Rubric     │          │
│           └─────────────────────────────────────────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Boundaries

### 2.1 Frontend (React + TypeScript + Vite)

**Responsibilities:**
- Scan submission UI (URL input, progress tracking)
- Report dashboard (score, findings, evidence, architecture)
- Scan history & comparison
- Settings & privacy controls

**Non-Responsibilities:**
- No business logic; no scoring; no tool execution
- Communicates only via REST API

**Tech Stack:**
- React 18, TypeScript, Vite
- Tailwind CSS (dark-first, cyan/teal accents)
- TanStack Query (server state)
- React Router v6
- Recharts (minimal charts)
- Lucide React (icons)

### 2.2 API Gateway (FastAPI)

**Responsibilities:**
- HTTP routing, request validation, response serialization
- Authentication & authorization (Phase 1: anonymous sessions)
- Rate limiting (per-IP, per-user)
- Scan lifecycle management (create, status, cancel)
- Report generation endpoints
- Static file serving (frontend build in prod)

**Non-Responsibilities:**
- No direct tool execution; delegates to Core Engine
- No database schema mutations outside migrations

**Key Endpoints:**
```
POST   /api/v1/scans              # Create scan from GitHub URL
GET    /api/v1/scans/{scan_id}    # Scan status & progress
GET    /api/v1/scans/{scan_id}/report  # Full report data
GET    /api/v1/scans/{scan_id}/findings  # Filterable findings
GET    /api/v1/scans/history      # User's scan history
POST   /api/v1/scans/{scan_id}/regrade # Trigger re-scan (Phase 4)
GET    /api/v1/rubric             # Current rubric version
```

### 2.3 Core Engine (Orchestrator)

**Responsibilities:**
- Scan orchestration (state machine: pending → profiling → analyzing → scoring → complete)
- Coordinates Repository Intake, Project Profiler, Static Analysis, Verification
- Manages background task execution (in-process for MVP)
- Evidence aggregation and persistence
- Invokes Finding Analysis & Scoring Engine

**Non-Responsibilities:**
- No direct tool execution (delegates to analyzers)
- No UI logic

**Internal API (Python modules):**
```python
# orchestrator.py
async def run_scan(scan_id: str) -> ScanResult:
    scan = await repo_intake.prepare(scan_id)
    profile = await profiler.analyze(scan.workdir)
    static_findings = await static_analyzer.run(scan.workdir, profile)
    verification_results = await verification_engine.run(scan.workdir, profile)
    evidence = await evidence_store.aggregate(scan_id, static_findings, verification_results)
    findings = await finding_analyzer.process(evidence)
    score = await scoring_engine.calculate(findings, profile.project_type)
    await report_generator.generate(scan_id, score, findings)
    return ScanResult(score, findings, evidence)
```

### 2.4 Repository Intake

**Responsibilities:**
- GitHub URL parsing & validation
- Public repository verification via GitHub API
- Shallow clone at immutable commit SHA
- Size validation & eligibility checks
- Workspace preparation (temp directory management)

**Inputs:** GitHub URL + optional branch/commit
**Outputs:** Local workspace path, resolved commit SHA, repo metadata

### 2.5 Project Profiler

**Responsibilities:**
- Language detection (file extensions + content heuristics)
- Framework detection (config files, dependencies)
- Package manager detection
- Build/test command inference
- Project type classification → determines applicable rubric checks

**Detection Targets (MVP):**
| Project Type | Indicators |
|---|---|
| `web_app` | `package.json` + `next`/`vite`/`react`/`vue`/`svelte` |
| `api` | `fastapi`/`express`/`django`/`flask`/`gin`/`actix` |
| `cli` | `bin`/`cli` entrypoints; `commander`/`click`/`cobra`/`clap` |
| `library` | No entrypoints; exports only; `pyproject.toml`/`package.json` with `main`/`exports` |
| `agent` | `langchain`/`autogen`/`crewai`/`openai-agents`; tool definitions |
| `mobile` | `expo`/`react-native`/`flutter`/`tauri`/`capacitor` |
| `unknown` | Fallback |

### 2.6 Static Analysis Engine

**Responsibilities:**
- Tool runner abstraction (subprocess with timeout, resource limits)
- Tool integration: ESLint, TypeScript, Semgrep, Trivy, detect-secrets
- Output normalization to unified `Finding` schema
- Tool version pinning & availability checking

**Tool Configuration (MVP):**

| Tool | Languages | Command | Output Format |
|---|---|---|---|
| ESLint | JS/TS | `eslint --format=json --no-error-on-unmatched-pattern .` | JSON |
| TypeScript | TS | `tsc --noEmit --pretty false` | JSON (parsed) |
| Semgrep | All | `semgrep --config=auto --json --quiet .` | SARIF/JSON |
| Trivy | All | `trivy fs --format=json --quiet .` | JSON |
| detect-secrets | All | `detect-secrets scan --all-files .` | JSON |

**Normalization Schema:**
```python
class NormalizedFinding(BaseModel):
    tool: str                    # "eslint", "semgrep", etc.
    tool_version: str
    rule_id: str                 # Tool-specific rule identifier
    rule_name: str               # Human-readable
    file_path: str               # Relative to repo root
    line_start: int
    line_end: int
    severity: Severity           # critical, high, medium, low, info
    confidence: Confidence       # verified, likely, heuristic
    message: str
    metadata: dict               # Tool-specific extra data
```

### 2.7 Verification Engine

**Phase 1 (MVP): Build & Test Only**
- Execute install, build, test commands in workspace
- Capture exit codes, stdout, stderr, duration
- Parse test output (JUnit, TAP, custom) for pass/fail counts

**Phase 2+: Sandbox Execution**
- Docker container per scan/check
- Resource limits (CPU, memory, pids, time, disk)
- Network isolation (default deny)
- User namespace mapping (non-root)
- Ephemeral filesystem (tmpfs)

**Command Inference (from Profiler):**
```python
commands = {
    "install": ["npm ci", "pip install -e .", "cargo build", "go mod download"],
    "build": ["npm run build", "tsc", "cargo build --release", "go build ./..."],
    "test": ["npm test", "pytest", "cargo test", "go test ./..."],
}
```

### 2.8 Evidence Store

**Responsibilities:**
- Persist structured evidence linked to scan, check, finding
- Store tool raw output (JSON), test summaries, execution logs
- Query API for report generation
- Retention & deletion policies

**Database Schema (SQLAlchemy 2.0):**

```python
# Core tables
class Scan(Base):
    id: UUID (PK)
    user_id: UUID | None (anonymous sessions)
    repo_url: str
    repo_owner: str
    repo_name: str
    commit_sha: str (40-char hex)
    branch: str
    project_type: str
    status: ScanStatus (pending, profiling, analyzing, scoring, complete, failed)
    rubric_version: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None

class Check(Base):
    id: UUID (PK)
    scan_id: UUID (FK)
    name: str                    # "eslint", "typescript", "build", "test"
    category: CheckCategory      # static, verification, dynamic
    status: CheckStatus          # pending, running, passed, failed, skipped, error
    started_at: datetime | None
    completed_at: datetime | None
    exit_code: int | None
    duration_ms: int | None
    output_summary: str          # Truncated for UI
    evidence_ref: UUID (FK)      # Points to EvidenceBlob

class EvidenceBlob(Base):
    id: UUID (PK)
    check_id: UUID (FK)
    content_type: str            # "application/json", "text/plain"
    content: bytes               # Compressed (gzip) if > 1KB
    metadata: dict               # Tool version, command, etc.

class Finding(Base):
    id: UUID (PK)
    scan_id: UUID (FK)
    check_id: UUID (FK)
    fingerprint: str             # Stable hash: tool:rule:file:line
    tool: str
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    confidence: Confidence
    title: str
    description: str
    evidence_ref: UUID (FK)
    rubric_dimensions: list[str] # Which dimensions this affects
    status: FindingStatus        # detected, triaged, confirmed, disputed, resolved
    first_seen: datetime
    last_seen: datetime

class RubricVersion(Base):
    version: str (PK)
    config: dict                 # Full YAML parsed
    created_at: datetime
    is_active: bool
```

### 2.9 Finding Analysis

**Responsibilities:**
- Deduplication: merge findings with same `(file_path, line_start, rule_id)` across tools
- Severity normalization: map tool severities → unified `critical|high|medium|low|info`
- Confidence assignment: based on check category (verification > static > heuristic)
- Applicability tagging: link findings to rubric dimensions

**Deduplication Rules:**
1. Same tool, same rule, same location → merge (keep highest severity)
2. Different tools, same rule category (e.g., "unused-variable"), same location → merge
3. Different categories → keep separate (may affect different dimensions)

### 2.10 Scoring Engine

**Responsibilities:**
- Load rubric version (YAML config)
- Apply applicability rules based on project profile
- Calculate dimension scores, overall score, coverage, confidence
- Detect critical blockers
- Pure deterministic function: `score = f(evidence, rubric, profile)`

**Algorithm:**
```python
def calculate_score(findings: list[Finding], profile: ProjectProfile, rubric: Rubric) -> ScoreResult:
    # 1. Filter applicable subchecks
    applicable = [sc for sc in rubric.subchecks if sc.applies_to(profile)]
    
    # 2. Map findings to subchecks
    subcheck_evidence = map_findings_to_subchecks(findings, applicable)
    
    # 3. Score each subcheck
    subcheck_scores = {}
    for sc in applicable:
        evidence = subcheck_evidence.get(sc.id, [])
        subcheck_scores[sc.id] = score_subcheck(sc, evidence)
    
    # 4. Aggregate by dimension
    dimension_scores = aggregate_by_dimension(subcheck_scores, rubric)
    
    # 5. Overall score (weighted)
    overall = sum(ds.score * ds.weight for ds in dimension_scores) / 100
    
    # 6. Coverage & confidence
    coverage = len([sc for sc in applicable if sc.id in subcheck_evidence]) / len(applicable)
    confidence = calculate_confidence(findings)
    
    # 7. Critical blockers
    blockers = [f for f in findings if f.is_critical_blocker()]
    
    return ScoreResult(overall, dimension_scores, coverage, confidence, blockers)
```

---

## 3. Data Flow

### 3.1 Scan Lifecycle

```
1. USER SUBMITS URL
   └─▶ POST /api/v1/scans {url, branch?}
   
2. API CREATES SCAN RECORD
   └─▶ Scan(status=pending) → DB
   
3. BACKGROUND TASK STARTS
   └─▶ Scan(status=profiling)
   
4. REPOSITORY INTAKE
   └─▶ Clone repo at commit SHA → workspace
   └─▶ Scan(status=analyzing)
   
5. PROJECT PROFILER
   └─▶ Detect project_type, commands, config
   
6. STATIC ANALYSIS (parallel)
   └─▶ Run ESLint, TypeScript, Semgrep, Trivy, detect-secrets
   └─▶ Normalize findings → Evidence Store
   
7. VERIFICATION (sequential)
   └─▶ Install → Build → Test
   └─▶ Capture results → Evidence Store
   
8. FINDING ANALYSIS
   └─▶ Deduplicate, severity, confidence, applicability
   
9. SCORING ENGINE
   └─▶ Apply rubric v1 → ScoreResult
   
10. REPORT GENERATION
    └─▶ Persist score, findings, metadata
    └─▶ Scan(status=complete)
    
11. FRONTEND POLLS → COMPLETE
    └─▶ GET /api/v1/scans/{id}/report
```

### 3.2 Error Handling

| Stage | Failure Mode | Result |
|---|---|---|
| Clone | Repo not found / private / too large | `Scan.status=failed`; `error` populated |
| Profiling | No supported project detected | `project_type=unknown`; limited checks |
| Static Analysis | Tool crash / timeout | Check `status=error`; findings=[]; coverage reduced |
| Verification | Build/test fails | Check `status=failed`; evidence captured; not a scan failure |
| Scoring | No applicable checks | Score=0; coverage=0; verdict="Insufficient Evidence" |

---

## 4. Security Architecture

### 4.1 Trust Boundaries (Reiterated)

| Boundary | Protection |
|---|---|
| Internet → API | HTTPS; rate limiting; input validation; CORS |
| API → Database | Parameterized queries; connection pooling; least privilege |
| API → Core Engine | Internal function calls; no serialization boundary |
| Core Engine → Sandbox | **Docker isolation** (Phase 2); subprocess limits (Phase 1) |
| Sandbox → Host | No network; read-only rootfs; non-root; resource limits |

### 4.2 Secrets Management

- **Development:** `.env` file (gitignored); `.env.example` committed
- **Production:** Environment variables injected at deploy time
- **Never in code:** Database URLs, API keys, encryption keys
- **Scanning:** detect-secrets runs on every scan; findings flagged

### 4.3 Audit Logging

All state-changing operations logged:
- Scan creation, start, completion, failure
- Report access (read)
- Finding status changes
- User authentication events (Phase 2+)

Log format: Structured JSON with `timestamp, event_type, scan_id, user_id, metadata`

---

## 5. Deployment Architecture

### 5.1 Development (Docker Compose)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: vibegrade
      POSTGRES_USER: vibegrade
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://vibegrade:${DB_PASSWORD}@postgres:5432/vibegrade
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      RUBRIC_VERSION: v1
    depends_on: [postgres]
    volumes:
      - ./backend:/app  # Hot reload

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on: [api]
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

### 5.2 Production Considerations

- **API:** Gunicorn + Uvicorn workers behind nginx
- **Database:** Managed PostgreSQL (RDS, Cloud SQL) with backups
- **Frontend:** Static build served by nginx or CDN (CloudFront, Vercel)
- **Sandbox:** Dedicated runner pool (separate VMs or Kubernetes)
- **Secrets:** Vault / AWS Secrets Manager / GCP Secret Manager
- **Observability:** Structured logs → Loki/ELK; metrics → Prometheus/Grafana

---

## 6. Technology Choices & Rationale

| Layer | Choice | Rationale |
|---|---|---|
| Backend Language | Python 3.12+ | Best ecosystem for static analysis tools, subprocess orchestration, data science (scoring) |
| Web Framework | FastAPI | Async-native; automatic OpenAPI; Pydantic integration; high performance |
| ORM | SQLAlchemy 2.0 | Async support; type-safe; mature; dialect-agnostic (SQLite→PostgreSQL) |
| Migrations | Alembic | Standard with SQLAlchemy; version-controlled |
| Frontend Framework | React 18 | Component model; ecosystem; TypeScript support; hiring pool |
| Build Tool | Vite | Fast HMR; TypeScript native; optimized production builds |
| Styling | Tailwind CSS | Utility-first; dark mode native; small bundle; design system friendly |
| State Management | TanStack Query | Server state synchronization; caching; deduping; mutations |
| Routing | React Router v6 | Standard; nested routes; data loading APIs |
| Database (Dev) | SQLite | Zero-config; file-based; same SQL dialect as PostgreSQL |
| Database (Prod) | PostgreSQL 16 | Production-grade; JSONB; full-text search; concurrency |
| Sandbox | Docker | Industry standard; strong isolation; resource limits; multi-language |
| Task Queue (MVP) | In-process (asyncio) | Zero dependencies; sufficient for sequential scans |
| Task Queue (Scale) | Redis + RQ / Celery | Horizontal scaling; persistence; retries |

---

## 7. API Contracts (OpenAPI)

Full OpenAPI spec served at `/api/v1/openapi.json` from FastAPI.

**Key Models:**
```typescript
// Scan creation
interface ScanRequest {
  repo_url: string;
  branch?: string;
  commit_sha?: string;
}

// Scan status
interface ScanStatusResponse {
  scan_id: string;
  status: "pending" | "profiling" | "analyzing" | "scoring" | "complete" | "failed";
  progress: number; // 0-100
  current_stage: string;
  error?: string;
}

// Report
interface ReportResponse {
  scan: ScanMetadata;
  score: ScoreResult;
  findings: Finding[];
  dimensions: DimensionScore[];
  rubric_version: string;
}
```

---

## 8. Extensibility Points

| Extension Point | Mechanism | Example |
|---|---|---|
| New static analysis tool | Implement `ToolRunner` protocol | Add `ruff` for Python |
| New project type | Add detector in `profiler/detectors/` | Detect `mobile` → Expo |
| New rubric dimension | Add to rubric YAML; update scoring | Add "Accessibility" |
| New verification check | Implement `VerificationCheck` | Playwright E2E |
| New export format | Add `ReportExporter` plugin | SARIF, JUnit, PDF |
| AI analysis provider | Implement `AIAnalyzer` interface | Local Ollama, OpenAI, Anthropic |

---

## 9. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Scan latency (small repo, static only) | < 60 seconds |
| Scan latency (with verification) | < 300 seconds |
| API response time (p95) | < 200 ms |
| Concurrent scans (MVP) | 3 (configurable) |
| Database size per scan | < 10 MB (evidence compressed) |
| Availability | 99.5% (single region) |
| Data retention (default) | 90 days |

---

## 10. Future Evolution (Post-MVP)

| Phase | Architectural Change |
|---|---|
| Phase 2 | Sandbox service extracted; gRPC between API and Sandbox Runner |
| Phase 3 | Plugin system for analyzers; dynamic rubric loading |
| Phase 4 | Task queue (Redis/RQ); webhook callbacks; re-scan scheduling |
| Phase 5 | Benchmark service; cohort comparison API; multi-tenant isolation |

---

*This architecture prioritizes simplicity and security for MVP. Complexity is added only when validated by user need.*