# VibeGrade — Implementation Plan

**Status:** Phase 0 (Research & Architecture) → Transitioning to Phase 1 (Functional MVP)
**Last Updated:** October 11, 2026
**Repository:** https://github.com/jmo7850/VibeGrade.git

---

## Phase 0 — Research and Architecture ✅ COMPLETE

| Task | Status | Evidence |
|---|---|---|
| Repository audit | ✅ Complete | Empty repo; established clean foundation |
| Competitor research | ✅ Complete | `docs/COMPETITOR_ANALYSIS.md` with 8 competitors analyzed |
| Architecture definition | ✅ Complete | Documented in this plan and architecture decisions below |
| Threat model | ✅ Complete | Documented in `docs/THREAT_MODEL.md` |
| Rubric & scoring semantics | ✅ Complete | Documented in `docs/GRADING_RUBRIC.md` |
| Implementation plan | ✅ Complete | This document |

**Phase 0 Acceptance Criteria Met:**
- Architecture and grading rules documented
- Competitor claims sourced and qualified
- Security boundaries defined before runtime execution

---

## Phase 1 — Functional MVP 🔄 IN PROGRESS

### 1.1 Project Foundation & Tech Stack

| Task | Status | Acceptance Criteria |
|---|---|---|
| Initialize Python backend (FastAPI) | 🔄 In Progress | `uv`/`pip` project; runs `uvicorn`; health endpoint |
| Initialize React frontend (Vite + TS) | ⏳ Pending | `npm create vite`; TypeScript; dev server runs |
| Configure shared tooling (lint, format, type-check) | ⏳ Pending | `ruff`, `mypy`, `eslint`, `prettier` pass |
| Database schema & migrations (SQLite → PostgreSQL ready) | ⏳ Pending | Tables for scans, findings, evidence, rubric versions |
| Docker Compose for local development | ⏳ Pending | `docker compose up` starts API + DB + frontend proxy |

**Tech Stack Decisions:**
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router
- **Database:** SQLite (dev), PostgreSQL (prod) via SQLAlchemy
- **Sandbox:** Docker containers with resource limits (Phase 2)
- **Static Analysis:** Subprocess integration of ESLint, TypeScript, Semgrep, Trivy, detect-secrets
- **Task Queue:** In-process background tasks for MVP; Redis/RQ for Phase 2+

### 1.2 Repository Intake (Public GitHub)

| Task | Status | Acceptance Criteria |
|---|---|---|
| GitHub URL validation & normalization | ⏳ Pending | Accepts `github.com/owner/repo`, `github.com/owner/repo/tree/branch`, etc. |
| Public repo metadata via GitHub API | ⏳ Pending | Fetches default branch, commit SHA, size, languages |
| Shallow clone with depth=1 at target commit | ⏳ Pending | Immutable SHA resolved; no auth required for public |
| Size limits & eligibility checks | ⏳ Pending | Reject >500MB; unsupported types (non-code) |
| Scan creation & status tracking | ⏳ Pending | `Scan` record: `pending` → `profiling` → `analyzing` → `scoring` → `complete`/`failed` |

### 1.3 Project Profiler

| Task | Status | Acceptance Criteria |
|---|---|---|
| Language detection (linguist / heuristic) | ⏳ Pending | Detects primary/secondary languages from file extensions |
| Framework detection (package.json, pyproject.toml, Cargo.toml, go.mod) | ⏳ Pending | Identifies: Next.js, Express, FastAPI, Django, React, Vue, Svelte, CLI, etc. |
| Package manager detection | ⏳ Pending | npm/yarn/pnpm, pip/poetry/uv, cargo, go mod, bun |
| Build/test command inference | ⏳ Pending | Reads scripts from package.json, Makefile, pyproject.toml, etc. |
| Project type classification | ⏳ Pending | Maps to: `web-app`, `api`, `cli`, `library`, `mobile`, `agent`, `unknown` |
| Applicable check selection | ⏳ Pending | Uses project type to filter rubric checks (applicability rules) |

### 1.4 Static Analysis Engine

| Task | Status | Acceptance Criteria |
|---|---|---|
| Tool runner abstraction | ⏳ Pending | Runs tools via subprocess; captures stdout/stderr/exit code; timeout |
| ESLint + TypeScript (JS/TS projects) | ⏳ Pending | Runs `eslint --format json`, `tsc --noEmit`; normalizes findings |
| Semgrep security rules (multi-language) | ⏳ Pending | Runs `semgrep --config=auto --json`; OSS rules only |
| Trivy dependency scanning | ⏳ Pending | Runs `trivy fs --format json`; vulnerability findings |
| detect-secrets | ⏳ Pending | Runs `detect-secrets scan`; baseline comparison |
| Finding normalization schema | ⏳ Pending | Unified `Finding` model: tool, rule, file, line, severity, message, confidence |

### 1.5 Verification Engine (Basic — Build & Test Only)

| Task | Status | Acceptance Criteria |
|---|---|---|
| Sandbox execution abstraction | ⏳ Pending | Runs commands in temp dir; captures exit code, stdout, stderr, duration |
| Install command execution | ⏳ Pending | `npm ci`, `pip install`, `cargo build`, `go mod download` |
| Build command execution | ⏳ Pending | `npm run build`, `tsc`, `cargo build --release`, `go build` |
| Test command execution | ⏳ Pending | `npm test`, `pytest`, `cargo test`, `go test ./...` |
| Test output parsing | ⏳ Pending | Extracts: passed, failed, skipped, duration per test suite |
| Check status classification | ⏳ Pending | `passed` | `failed` | `skipped` | `error` | `timeout` |

### 1.6 Evidence Store

| Task | Status | Acceptance Criteria |
|---|---|---|
| SQLAlchemy models for core entities | ⏳ Pending | `Scan`, `Project`, `Check`, `Finding`, `Evidence`, `RubricVersion` |
| Evidence persistence (structured JSON blobs) | ⏳ Pending | Tool output, test summaries, logs stored per check |
| Query API for report generation | ⏳ Pending | "All findings for scan X", "Evidence for finding Y" |

### 1.7 Finding Analysis

| Task | Status | Acceptance Criteria |
|---|---|---|
| Deduplication by (file, line, rule) | ⏳ Pending | Merges findings from multiple tools on same location |
| Severity mapping (tool → unified) | ⏳ Pending | `critical` | `high` | `medium` | `low` | `info` |
| Confidence assignment | ⏳ Pending | `verified` (tool + execution) | `likely` (static only) | `heuristic` (pattern) |
| Applicability tagging | ⏳ Pending | Links finding to rubric dimension(s) |

### 1.8 Scoring Engine (v1 Rubric)

| Task | Status | Acceptance Criteria |
|---|---|---|
| Rubric v1 as YAML/JSON config | ⏳ Pending | 10 dimensions, weights, subchecks, applicability rules |
| Deterministic score calculation | ⏳ Pending | Pure function: `evidence + rubric → score, coverage, confidence` |
| Coverage computation | ⏳ Pending | `(applicable checks with evidence) / (total applicable checks)` |
| Confidence computation | ⏳ Pending | Weighted by finding confidence; disclosed separately |
| Critical blocker detection | ⏳ Pending | Security `critical`/`high` → blocker flag; readiness warning |
| Score reproducibility test | ⏳ Pending | Same evidence + same rubric = identical score |

### 1.9 Report Dashboard (Web UI)

| Task | Status | Acceptance Criteria |
|---|---|---|
| Scan submission page | ⏳ Pending | URL input, validation, progress polling |
| Report overview: score, grade, verdict, coverage, confidence | ⏳ Pending | Visual score card; letter grade; readiness badge |
| Dimension breakdown | ⏳ Pending | 10 bars with scores, weights, applicable checks count |
| Findings explorer (filterable table) | ⏳ Pending | Filter by severity, dimension, confidence, status |
| Finding detail view | ⏳ Pending | Evidence, reproduction, remediation, rubric links |
| Scan history list | ⏳ Pending | Previous scans for same repo with score trend |
| Export (JSON, PDF) | ⏳ Pending | Download buttons on report page |

### 1.10 Remediation Prompts (Basic)

| Task | Status | Acceptance Criteria |
|---|---|---|
| Prompt template per finding type | ⏳ Pending | Context + evidence + desired fix + verification command |
| Top-N prioritized prompts | ⏳ Pending | Sorted by severity × confidence × dimension weight |
| Copy-to-clipboard UI | ⏳ Pending | One-click copy for coding agents |

---

## Phase 2 — Secure Runtime Verification (Planned)

| Task | Status | Notes |
|---|---|---|
| Docker sandbox implementation | ⏳ Planned | Isolated containers; CPU/memory/disk/time limits; no network by default |
| User workflow verification (Playwright/API) | ⏳ Planned | Scripted critical paths; evidence capture |
| Security hardening & testing | ⏳ Planned | Attempt escapes; verify isolation |
| Log sanitization | ⏳ Planned | Strip secrets, PII from stored outputs |

---

## Phase 3 — Product-Aware Evaluation (Planned)

| Task | Status | Notes |
|---|---|---|
| Project-type rubric overlays | ✅ Complete | Weight overrides for all 10 dimensions per project type |
| Architecture analysis (dependency graph) | ✅ Complete | Module boundaries, cycles, coupling metrics, import graph |
| Placeholder/mock detection | ✅ Complete | TODOs, mock returns, fake classes, hardcoded data |
| Data/backend integrity checks | ⏳ Planned | Schema, migrations, API contracts |
| Missing UI states detection | ✅ Complete | Loading, error, empty states for web/mobile apps |
| Dead controls detection | ✅ Complete | Buttons/links with no handlers for web/mobile apps |
| Fake API detection | ✅ Complete | Hardcoded responses, dummy implementations |

---

## Phase 4 — Remediation & Regression (Planned)

| Task | Status | Notes |
|---|---|---|
| Fix tracking & re-scan | ⏳ Planned | Targeted check re-run; before/after comparison |
| Regression detection | ⏳ Planned | Findings reappearing across scans |

---

## Phase 5 — Benchmarking & Expansion (Planned)

| Task | Status | Notes |
|---|---|---|
| Benchmark suite (fixtures with known findings) | ⏳ Planned | Calibration data for rubric weights |
| Local CLI scanner | ⏳ Planned | Same engine, local execution |
| CI/CD integrations | ⏳ Planned | GitHub App, GitLab, GitHub Actions |

---

## Architecture Decisions (Recorded for Traceability)

| Decision | Rationale | Reversibility |
|---|---|---|
| Python backend (FastAPI) | Best ecosystem for static analysis tools, sandbox orchestration, data processing | Moderate (rewrite needed) |
| React + TypeScript frontend | Industry standard; good DX; type safety | Low (UI rewrite) |
| SQLite for MVP | Zero-config dev; easy migration to PostgreSQL | High (swap dialect) |
| Docker sandbox (Phase 2) | Strongest isolation available in standard environments | Moderate (alternative: gVisor, Firecracker) |
| Subprocess tool integration | Leverages mature tools; avoids reimplementation | High (swap tools) |
| Versioned rubric as data (YAML) | Non-developers can inspect/modify; deterministic | High (config change) |
| In-process background tasks (MVP) | Simplicity; no Redis dependency yet | High (add queue later) |
| No mandatory AI for scoring | Deterministic, auditable, offline-capable | Low (core principle) |

---

## Known Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Sandbox escape in shared environment | Medium | Critical | Disable runtime execution if Docker not available; document limitation |
| Tool output parsing breaks on version changes | High | Medium | Pin tool versions in Dockerfile; integration tests with fixtures |
| GitHub API rate limits (unauthenticated) | High | Medium | Cache responses; respect headers; document limits |
| Large repos timeout during clone/analysis | Medium | High | Size limits; shallow clone; configurable timeouts |
| False positives from static analysis | High | Medium | Confidence labeling; deduplication; user feedback loop |
| Scoring calibration without real data | High | High | Build benchmark fixtures early (Phase 1.8 test) |

---

## Validation Commands (To Be Executed)

```bash
# Backend
cd backend
uv sync                    # or pip install -e .
ruff check .               # lint
mypy .                     # type check
pytest -v                  # tests
uvicorn app.main:app --reload  # run server

# Frontend
cd frontend
npm install
npm run lint               # eslint
npm run typecheck          # tsc --noEmit
npm run build              # production build
npm run dev                # dev server

# Full stack
docker compose up --build  # all services
```

---

## Current Blockers

1. **No implementation yet** — Starting Phase 1.1 now
2. **Sandbox environment unknown** — Need to verify Docker availability in deployment target
3. **GitHub API unauthenticated limits** — 60 req/hr; may need token for sustained use

---

## Next Actions (Immediate)

1. Initialize backend project structure with FastAPI, SQLAlchemy, Pydantic
2. Initialize frontend project with Vite, React, TypeScript, Tailwind
3. Create database models and Alembic migration
4. Implement GitHub URL parsing and public repo cloning
5. Build project profiler with framework detection
6. Implement tool runner and first static analysis integration (ESLint/TypeScript)
7. Create rubric v1 configuration and scoring engine
8. Build minimal report UI

---

*This plan is a living document. Update status as work progresses. Defer only when a concrete dependency requires it.*