# VibeGrade

> **Evidence-driven software quality and production-readiness evaluation for AI-built applications.**

VibeGrade evaluates whether a software project actually works, is engineered responsibly, and how much evidence supports that conclusion. It distinguishes between impressive prototypes, functional MVPs, well-tested applications, and production-ready systems.

## Current Status

**Phase 1: Functional MVP** — Core grading engine implementation in progress.

- [x] Competitor research (`docs/COMPETITOR_ANALYSIS.md`)
- [x] Threat model (`docs/THREAT_MODEL.md`)
- [x] Grading rubric v1.0 (`docs/GRADING_RUBRIC.md`)
- [x] System architecture (`docs/ARCHITECTURE.md`)
- [x] Implementation plan (`docs/IMPLEMENTATION_PLAN.md`)
- [ ] Backend (FastAPI) — **in progress**
- [ ] Frontend (React + TypeScript)
- [ ] Static analysis integration
- [ ] Verification engine (build/test)
- [ ] Scoring engine with rubric v1.0
- [ ] Report dashboard

## Quickstart (Development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for sandbox execution in Phase 2)
- `uv` (recommended) or `pip` for Python package management

```bash
# Clone and enter
git clone https://github.com/jmo7850/VibeGrade.git
cd VibeGrade

# Backend setup
cd backend
uv sync                    # or: pip install -e .
cp .env.example .env       # Configure as needed
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env       # Configure VITE_API_URL
npm run dev
```

### Environment Variables

See `.env.example` in each package for required configuration.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   API       │────▶│  Core       │
│  (React/TS) │     │  (FastAPI)  │     │  Engine     │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────┴──────┐     ┌──────┴──────┐
                    ▼             ▼     ▼             ▼
             ┌───────────┐ ┌───────────┐ ┌───────────┐
             │ Repository│ │ Static    │ │ Verifica- │
             │ Intake    │ │ Analysis  │ │ tion      │
             └───────────┘ └───────────┘ └───────────┘
                           │                   │
                    ┌──────┴───────────────────┴──────┐
                    ▼                                 ▼
             ┌─────────────────┐             ┌─────────────────┐
             │ Evidence Store  │────────────▶│ Finding Analysis│
             │ (SQLite/Postgres)             │ & Scoring       │
             └─────────────────┘             └─────────────────┘
```

See `docs/ARCHITECTURE.md` for detailed component boundaries and data flows.

## Grading Rubric (v1.0)

| Dimension | Weight |
|---|---:|
| Functional Correctness | 20 |
| Security and Privacy | 15 |
| Architecture and Maintainability | 12 |
| Testing and Verification | 12 |
| Data and Backend Integrity | 10 |
| Completeness and Integration | 10 |
| Performance and Efficiency | 6 |
| Deployment and Operations | 5 |
| Documentation and Reproducibility | 5 |
| Engineering Discipline | 5 |
| **Total** | **100** |

**Key Principles:**
- Deterministic, reproducible scoring from stored evidence
- Applicability-aware (no unfair penalties for irrelevant checks)
- Coverage and confidence reported separately from score
- Critical security blockers override aggregate score
- Versioned rubric — historical comparisons preserved

See `docs/GRADING_RUBRIC.md` for complete subchecks, scoring mechanics, and grade bands.

## Security

VibeGrade treats every submitted repository as **untrusted input**.

- **Phase 1:** Subprocess execution with timeouts; no network access; size limits
- **Phase 2+:** Docker sandbox with CPU/memory/pids limits, network isolation, non-root user, read-only rootfs
- **Never:** Source code persisted; secrets exposed to scans; cross-scan data access

See `docs/THREAT_MODEL.md` for complete STRIDE analysis and mitigations.

## Project Structure

```
VibeGrade/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic (orchestrator, analyzers, scoring)
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   ├── pyproject.toml
│   └── .env.example
├── frontend/               # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-level pages
│   │   ├── hooks/          # Custom React hooks
│   │   ├── api/            # API client (TanStack Query)
│   │   ├── types/          # TypeScript types
│   │   └── main.tsx
│   ├── tests/              # Frontend tests
│   ├── package.json
│   └── .env.example
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── COMPETITOR_ANALYSIS.md
│   ├── GRADING_RUBRIC.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── THREAT_MODEL.md
│   └── TESTING.md
├── rubric/                 # Versioned rubric configurations
│   └── v1.yaml
├── docker-compose.yml      # Local development stack
└── README.md
```

## Documentation

| Document | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | System design, component boundaries, data flows |
| `docs/COMPETITOR_ANALYSIS.md` | Researched competitor capabilities & differentiation |
| `docs/GRADING_RUBRIC.md` | Complete rubric v1.0 with subchecks & scoring mechanics |
| `docs/IMPLEMENTATION_PLAN.md` | Phased milestones, acceptance criteria, current status |
| `docs/THREAT_MODEL.md` | STRIDE threat analysis, sandbox security requirements |
| `docs/TESTING.md` | Test strategy, fixtures, validation commands |

## Supported Project Types (MVP)

| Type | Detection | Static Analysis | Verification |
|---|---|---|---|
| Web App (Next.js, Vite, React, Vue, Svelte) | ✅ | ESLint, TS, Semgrep | Build + Test |
| API (FastAPI, Express, Django, Flask, Go, Rust) | ✅ | Semgrep, Trivy | Build + Test |
| CLI Tools | ✅ | Semgrep, Trivy | Build + Test |
| Libraries | ✅ | Semgrep, Trivy | Build + Test |
| AI Agents (LangChain, CrewAI, etc.) | ✅ | Semgrep, Trivy | Build + Test |
| Mobile (Expo, React Native, Flutter) | ✅ | Semgrep | Build only |

## Roadmap

- **Phase 1:** Functional MVP — Public GitHub repo scanning, static analysis, build/test verification, deterministic scoring, report dashboard
- **Phase 2:** Secure Runtime Verification — Docker sandbox, resource limits, user workflow verification
- **Phase 3:** Product-Aware Evaluation — Project-type rubrics, architecture analysis, placeholder detection
- **Phase 4:** Remediation & Regression — Fix tracking, agent prompts, before/after comparison
- **Phase 5:** Benchmarking & Expansion — Calibration suite, CLI scanner, CI integrations

## Contributing

This is an active development project. See `docs/IMPLEMENTATION_PLAN.md` for current priorities.

## License

MIT License — see `LICENSE` file (to be added).

---

**VibeGrade** — *Does this project actually work, is it engineered responsibly, and how much evidence supports that conclusion?*