# VibeGrade — Testing Strategy

**Version:** 1.0
**Date:** October 11, 2026

---

## 1. Test Pyramid

```
        ┌─────────────┐
        │   E2E       │  ← Few: Critical user journeys (scan → report)
        ├─────────────┤
        │ Integration │  ← Medium: API contracts, service interactions
        ├─────────────┤
        │   Unit      │  ← Many: Pure functions, scoring, normalization
        └─────────────┘
```

**Target Distribution:** 70% Unit / 20% Integration / 10% E2E

---

## 2. Test Organization

### 2.1 Backend (`backend/tests/`)

```
tests/
├── unit/
│   ├── test_scoring.py           # Scoring engine (PRIORITY 1)
│   ├── test_rubric.py            # Rubric loading & applicability
│   ├── test_normalization.py     # Finding normalization from tools
│   ├── test_deduplication.py     # Finding deduplication logic
│   ├── test_profiler.py          # Project type detection
│   └── test_evidence.py          # Evidence store queries
├── integration/
│   ├── test_api_scans.py         # Scan CRUD + status transitions
│   ├── test_report_generation.py # Report endpoint data shape
│   ├── test_intake_github.py     # GitHub URL parsing, cloning
│   └── test_static_analysis.py   # Tool runner + output parsing
├── fixtures/
│   ├── repos/                    # Test repositories (cloned/copied)
│   │   ├── minimal_ts/           # Minimal TypeScript project
│   │   ├── minimal_py/           # Minimal Python project
│   │   ├── with_issues/          # Known findings for detection tests
│   │   └── clean/                # Should produce minimal findings
│   ├── tool_outputs/             # Canned tool outputs for parsing tests
│   │   ├── eslint.json
│   │   ├── tsc.json
│   │   ├── semgrep.json
│   │   └── trivy.json
│   └── rubrics/
│       └── v1.yaml               # Test rubric (subset of production)
└── conftest.py                   # Pytest fixtures, async config
```

### 2.2 Frontend (`frontend/tests/`)

```
tests/
├── unit/
│   ├── components/               # Component rendering + props
│   ├── hooks/                    # Custom hook behavior
│   └── utils/                    # Pure utility functions
├── integration/
│   ├── pages/                    # Page-level with mocked API
│   └── api/                      # TanStack Query integration
└── e2e/
    └── scan_flow.test.ts         # Playwright: submit URL → view report
```

---

## 3. Scoring Engine Tests (PRIORITY 1)

**Must pass before any UI depends on scoring.**

### 3.1 Test Cases

| Test | Description | Fixture |
|---|---|---|
| `test_max_score_all_pass` | All applicable checks pass → 100 | `clean` repo |
| `test_weighted_dimension_scores` | Dimension scores match rubric weights | Synthetic findings |
| `test_partial_credit_heuristic` | Heuristic findings = 50% penalty | Mixed findings |
| `test_applicability_excludes_na` | N/A checks excluded from denominator | `cli` project (no DB checks) |
| `test_missing_evidence_not_pass` | Skipped checks = 0 points, reduce coverage | Tool timeout fixture |
| `test_duplicate_finding_single_penalty` | Same defect across tools → one penalty | Duplicate fixture |
| `test_critical_blocker_detection` | Critical security finding → blocker flag | `with_issues` repo |
| `test_coverage_calculation` | Coverage = evidenced / applicable | Partial evidence fixture |
| `test_confidence_calculation` | Weighted by finding confidence | Mixed confidence fixture |
| `test_deterministic_reproducibility` | Same input → identical output | Fixed fixture |
| `test_rubric_version_isolation` | v1.0 vs v1.1 produce different scores | Two rubric versions |

### 3.2 Running Scoring Tests

```bash
cd backend
uv run pytest tests/unit/test_scoring.py -v
uv run pytest tests/unit/test_rubric.py -v
uv run pytest tests/unit/test_deduplication.py -v
```

---

## 4. Repository Intake Tests

### 4.1 Test Cases

| Test | Description |
|---|---|
| `test_valid_github_urls` | Various URL formats resolve to owner/repo |
| `test_invalid_urls_rejected` | Non-GitHub, malformed, empty |
| `test_private_repo_detected` | API returns 404 → eligibility failed |
| `test_size_limit_enforced` | Mock large repo → rejected |
| `test_commit_sha_resolved` | Branch name → immutable SHA |
| `test_malicious_filename_handling` | Path traversal in clone → sanitized |

### 4.2 Fixtures

Use real small public repos for integration tests:
- `https://github.com/octocat/Hello-World` (tiny)
- `https://github.com/pallets/flask` (medium, Python)
- `https://github.com/vercel/next.js` (large, TypeScript) — **only for manual/slow tests**

---

## 5. Static Analysis Integration Tests

### 5.1 Tool Runner Tests

```python
# tests/integration/test_static_analysis.py
async def test_eslint_runs_and_parses(tmp_path):
    # Write known problematic JS file
    # Run eslint via tool runner
    # Assert normalized findings match expected

async def test_semgrep_security_rules(tmp_path):
    # Write file with SQL injection pattern
    # Run semgrep
    # Assert finding with rule_id "sql-injection"

async def test_tool_timeout_handled(tmp_path):
    # Mock slow command
    # Assert CheckStatus.ERROR with timeout evidence
```

### 5.2 Canned Output Tests (Fast, No Tool Installation)

```python
# tests/unit/test_normalization.py
def test_eslint_json_parsing():
    raw = load_fixture("eslint.json")
    findings = normalize_eslint(raw)
    assert findings[0].rule_id == "no-unused-vars"
    assert findings[0].severity == Severity.MEDIUM
```

---

## 6. Verification Engine Tests

### 6.1 Phase 1 (Subprocess)

| Test | Description |
|---|---|
| `test_install_command_runs` | `npm ci` succeeds in fixture |
| `test_build_failure_captured` | Broken TypeScript → exit code ≠ 0 |
| `test_test_output_parsed` | Jest output → pass/fail counts |
| `test_timeout_enforced` | Infinite loop → killed at 120s |

### 6.2 Phase 2 (Docker Sandbox) — Future

| Test | Description |
|---|---|
| `test_container_isolation` | No access to host `/etc/passwd` |
| `test_network_denied` | `curl http://169.254.169.254` fails |
| `test_memory_limit` | Allocate 3GB in 2GB limit → OOM kill |
| `test_cpu_limit` | Busy loop → throttled |
| `test_pid_limit` | Fork bomb → blocked at 100 processes |
| `test_non_root_user` | `whoami` = `scanner` (UID 10001) |

---

## 7. API Contract Tests

```python
# tests/integration/test_api_scans.py
async def test_create_scan_returns_id(client):
    resp = await client.post("/api/v1/scans", json={"repo_url": "https://github.com/octocat/Hello-World"})
    assert resp.status_code == 201
    assert "scan_id" in resp.json()

async def test_scan_status_transitions(client, scan_id):
    # Poll until complete
    # Assert status goes: pending → profiling → analyzing → scoring → complete

async def test_report_includes_all_sections(client, completed_scan_id):
    resp = await client.get(f"/api/v1/scans/{completed_scan_id}/report")
    data = resp.json()
    assert "score" in data
    assert "findings" in data
    assert "dimensions" in data
    assert "coverage" in data
    assert "confidence" in data
```

---

## 8. Frontend Tests

### 8.1 Component Tests (Vitest + React Testing Library)

```typescript
// tests/unit/components/ScoreCard.test.tsx
test("renders score with correct grade color", () => {
  render(<ScoreCard score={87} grade="B" />);
  expect(screen.getByText("87")).toBeInTheDocument();
  expect(screen.getByText("B")).toHaveClass("text-teal-400");
});

test("shows blocker warning when critical findings exist", () => {
  render(<ScoreCard score={92} grade="A" criticalBlockers={1} />);
  expect(screen.getByText(/critical blocker/i)).toBeInTheDocument();
});
```

### 8.2 E2E Tests (Playwright)

```typescript
// tests/e2e/scan_flow.test.ts
test("submit public repo → see report", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[name="repo_url"]', "https://github.com/octocat/Hello-World");
  await page.click('button[type="submit"]');
  await expect(page.locator('[data-testid="scan-progress"]')).toBeVisible();
  await expect(page.locator('[data-testid="report-score"]')).toBeVisible({ timeout: 120000 });
});
```

---

## 9. Test Fixtures

### 9.1 Repository Fixtures (Committed to Repo)

```
backend/tests/fixtures/repos/
├── minimal_ts/           # package.json, tsconfig.json, src/index.ts
├── minimal_py/           # pyproject.toml, src/main.py
├── with_issues/
│   ├── sql_injection.py  # Raw SQL concatenation
│   ├── hardcoded_secret.ts # API key in source
│   └── unused_var.js     # ESLint detectable
└── clean/
    └── well_structured/  # Passes all checks
```

### 9.2 Tool Output Fixtures

Committed JSON files representing real tool output for parser testing.

---

## 10. Validation Commands

### 10.1 Backend

```bash
cd backend

# Install deps
uv sync

# Lint
uv run ruff check .

# Type check
uv run mypy .

# Unit tests (fast)
uv run pytest tests/unit -v --tb=short

# Integration tests (require tools installed)
uv run pytest tests/integration -v --tb=short -k "not slow"

# All tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Security scan (bandit)
uv run bandit -r app/
```

### 10.2 Frontend

```bash
cd frontend

# Install deps
npm install

# Lint
npm run lint

# Type check
npm run typecheck

# Unit tests
npm run test

# E2E tests (requires running backend + frontend)
npm run test:e2e

# Build verification
npm run build
```

### 10.3 Full Stack (Docker Compose)

```bash
# Start all services
docker compose up --build -d

# Run backend tests against containerized DB
docker compose exec api uv run pytest tests/ -v

# Run frontend E2E against containerized stack
docker compose exec frontend npm run test:e2e

# Cleanup
docker compose down -v
```

---

## 11. CI/CD Pipeline (Future)

```yaml
# .github/workflows/ci.yml (planned)
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd backend && uv sync
      - run: cd backend && uv run ruff check .
      - run: cd backend && uv run mypy .
      - run: cd backend && uv run pytest tests/unit -v
      - run: cd backend && uv run pytest tests/integration -v
      - run: cd backend && uv run bandit -r app/

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run typecheck
      - run: cd frontend && npm run test
      - run: cd frontend && npm run build

  e2e:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up --build -d
      - run: docker compose exec frontend npm run test:e2e
```

---

## 12. Test Data Principles

1. **No production secrets** in fixtures
2. **Deterministic** — same input always produces same output
3. **Minimal** — smallest repo/code that exercises the behavior
4. **Documented** — each fixture has a `README.md` explaining what it tests
5. **Safe** — no malicious code that could execute outside tests
6. **Versioned** — fixture format changes tracked with test updates

---

## 13. Coverage Targets

| Module | Target |
|---|---|
| Scoring Engine | 100% |
| Rubric Loading | 100% |
| Finding Normalization | 95% |
| Deduplication | 95% |
| API Endpoints | 90% |
| Orchestrator | 85% |
| Frontend Components | 80% |
| Overall | 85% |

---

*Run tests frequently. Fix failures immediately. Never commit failing tests.*