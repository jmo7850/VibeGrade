# VibeGrade — Grading Rubric v1.0

**Version:** 1.0
**Status:** Initial hypothesis — subject to calibration
**Date:** October 11, 2026

---

## 1. Rubric Overview

| Dimension | Weight | Code |
|---|---:|---|
| Functional Correctness | 20 | `functional_correctness` |
| Security and Privacy | 15 | `security_privacy` |
| Architecture and Maintainability | 12 | `architecture_maintainability` |
| Testing and Verification | 12 | `testing_verification` |
| Data and Backend Integrity | 10 | `data_backend_integrity` |
| Completeness and Integration | 10 | `completeness_integration` |
| Performance and Efficiency | 6 | `performance_efficiency` |
| Deployment and Operations | 5 | `deployment_operations` |
| Documentation and Reproducibility | 5 | `documentation_reproducibility` |
| Engineering Discipline | 5 | `engineering_discipline` |
| **Total** | **100** | |

**Design Principles:**
- Weights are initial hypotheses, not scientifically validated
- Each dimension has subchecks with individual point allocations
- Applicability rules prevent unfair penalties for irrelevant checks
- Coverage and confidence reported separately from score
- Critical security findings trigger blocker warnings regardless of aggregate score

---

## 2. Dimension Definitions & Subchecks

### 2.1 Functional Correctness (20 pts)

*Does the software actually work as intended?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Build succeeds | `fc.build_success` | 5 | All projects | Build command exit code = 0; artifact produced |
| Entry point executes | `fc.entry_executes` | 4 | All projects | Main binary/server starts without crash |
| Core workflow verified | `fc.core_workflow` | 6 | Web apps, APIs, CLIs, agents | At least one critical user journey passes (test or scripted verification) |
| Error handling present | `fc.error_handling` | 3 | All projects | Try/catch, error boundaries, graceful degradation detected |
| Edge cases covered | `fc.edge_cases` | 2 | All projects | Tests for empty states, invalid input, boundaries |

**Applicability Notes:**
- `fc.core_workflow`: Requires verification engine (Phase 2). In Phase 1, marked `skipped` with evidence "verification engine not available".
- CLI tools: "core workflow" = command runs and produces expected output for test input.

---

### 2.2 Security and Privacy (15 pts)

*Are users and data protected?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Authentication implemented | `sec.auth_present` | 3 | Web apps, APIs, multi-user | Auth middleware, session management, login flow |
| Server-side authorization | `sec.authz_server_side` | 3 | Multi-tenant, RBAC | Permission checks in route handlers; not just UI hiding |
| No secrets exposed | `sec.no_secrets` | 3 | All projects | detect-secrets: 0 findings in tracked files; no `.env` in repo |
| Injection risks mitigated | `sec.injection_safe` | 3 | Apps with input (web, API, CLI) | Parameterized queries; input validation; no `eval`/`exec` |
| Dependency vulnerabilities | `sec.dep_vulns` | 2 | All projects | Trivy/Semgrep: 0 critical/high unpatched CVEs |
| Secure configuration defaults | `sec.config_defaults` | 1 | All projects | No debug mode in prod config; secure headers; TLS config |

**Critical Blocker Rules:**
- Any `critical` severity secret exposure → **Blocker** (readiness warning)
- Any `critical`/`high` injection vulnerability with exploit evidence → **Blocker**
- Authentication bypass with proof → **Blocker**

---

### 2.3 Architecture and Maintainability (12 pts)

*Is the codebase structured for long-term evolution?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Module boundaries respected | `arch.module_boundaries` | 3 | Multi-module projects | No circular imports; clear public APIs; internal vs external |
| Low coupling / high cohesion | `arch.coupling` | 3 | All projects | Fan-in/fan-out metrics; dependency direction analysis |
| No significant duplication | `arch.deduplication` | 2 | All projects | Copy-paste detection (jscpd/semgrep); < 5% duplicated lines |
| Consistent patterns | `arch.consistency` | 2 | All projects | Naming conventions; error handling style; config patterns |
| Appropriate complexity | `arch.complexity` | 2 | All projects | Cyclomatic complexity < 20 per function; file size < 500 lines |

**Applicability Notes:**
- Single-file projects / micro-libraries: `arch.module_boundaries` = N/A (not penalized)
- Prototype/learning projects: `arch.consistency` weight reduced to 1

---

### 2.4 Testing and Verification (12 pts)

*Is behavior verified automatically?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Test suite exists | `test.suite_exists` | 2 | All projects | Test files detected; test command runs |
| Tests execute & pass | `test.tests_pass` | 4 | All projects | Test runner exit code = 0; > 0 tests executed |
| Meaningful coverage | `test.coverage` | 3 | All projects | Coverage > 60% statements (if measurable); critical paths covered |
| Test quality (assertions) | `test.assertion_quality` | 2 | All projects | No empty tests; specific assertions; no `expect(true).toBe(true)` |
| Integration/E2E tests | `test.integration` | 1 | Web apps, APIs | At least one cross-component test |

**Critical Rule:** Test file existence ≠ points. Points require **execution + pass + meaningful assertions**.

---

### 2.5 Data and Backend Integrity (10 pts)

*Is data handled correctly and consistently?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Schema with constraints | `data.schema_constraints` | 3 | Projects with DB | NOT NULL, UNIQUE, FK, CHECK constraints present |
| Migrations versioned | `data.migrations` | 2 | Projects with DB | Migration files; reversible; no raw SQL in app code |
| API contracts validated | `data.api_contracts` | 2 | APIs | OpenAPI/Schema validation; request/response typing |
| Transaction handling | `data.transactions` | 2 | Projects with DB | Explicit transactions; rollback on error; no partial writes |
| Cross-layer consistency | `data.cross_layer` | 1 | Full-stack | Frontend types match backend; shared schemas |

**Applicability Notes:**
- No database (static site, CLI): `data.schema_constraints`, `data.migrations`, `data.transactions` = N/A
- Weight redistributed to applicable checks

---

### 2.6 Completeness and Integration (10 pts)

*Are features actually finished and connected?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| No dead controls | `comp.no_dead_controls` | 2 | Web apps | No buttons/links with no handler; no unreachable routes |
| No placeholder implementations | `comp.no_placeholders` | 3 | All projects | No `TODO`/`FIXME`/`mock` in production paths; no stub returns |
| No fake APIs | `comp.no_fake_apis` | 2 | Web apps, APIs | No hardcoded responses masquerading as live data |
| Proper loading/error/empty states | `comp.states` | 2 | Web apps | Skeleton loaders; error boundaries; empty state UI |
| Frontend-backend connected | `comp.fe_be_connected` | 1 | Full-stack | API calls reach real endpoints; no mock adapters in prod build |

---

### 2.7 Performance and Efficiency (6 pts)

*Are there measurable performance risks?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| No obvious N+1 queries | `perf.n_plus_one` | 2 | DB-backed apps | ORM query analysis; no loop queries |
| Reasonable bundle size | `perf.bundle_size` | 1 | Web apps | JS bundle < 500KB gzipped (or documented justification) |
| No memory leaks (static) | `perf.memory_static` | 1 | Long-running | No global accumulation; proper cleanup patterns |
| Efficient algorithms | `perf.algorithms` | 1 | All projects | No O(n²) in hot paths without justification |
| Resource cleanup | `perf.cleanup` | 1 | All projects | Connections closed; files closed; timers cleared |

**Evidence Standard:** Static analysis + heuristic detection. Dynamic profiling deferred to Phase 3+.

---

### 2.8 Deployment and Operations (5 pts)

*Can this be deployed and operated reliably?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Reproducible build | `deploy.reproducible_build` | 2 | All projects | Lockfiles committed; Dockerfile deterministic; no `latest` tags |
| Environment config | `deploy.env_config` | 1 | All projects | `.env.example`; no secrets in config; 12-factor compliance |
| CI checks configured | `deploy.ci_checks` | 1 | All projects | CI file present; runs lint/test/build on PR |
| Health/observability | `deploy.observability` | 1 | Long-running services | Health endpoint; structured logging; error tracking |

---

### 2.9 Documentation and Reproducibility (5 pts)

*Can someone else build, run, and understand this?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Setup instructions | `doc.setup_instructions` | 2 | All projects | README with clone, install, run steps that work |
| Run/deploy commands | `doc.run_commands` | 1 | All projects | Clear `dev`, `build`, `start`, `test` commands |
| Architecture/API docs | `doc.architecture` | 1 | Non-trivial projects | ARCHITECTURE.md or equivalent; API docs if API |
| Limitations documented | `doc.limitations` | 1 | All projects | Known issues, unsupported features, scope boundaries |

---

### 2.10 Engineering Discipline (5 pts)

*Does the project follow baseline engineering practices?*

| Subcheck | ID | Points | Applicability | Evidence Required |
|---|---|---:|---|---|
| Dependency hygiene | `eng.dep_hygiene` | 2 | All projects | Lockfiles; no unpinned deps; regular updates; no deprecated |
| Type checking / linting | `eng.type_lint` | 1 | Typed languages | TypeScript strict; mypy; clippy; go vet configured |
| Consistent error handling | `eng.error_handling` | 1 | All projects | Single error pattern; no swallowed exceptions; logging |
| Avoidable complexity | `eng.complexity` | 1 | All projects | No god classes; reasonable function length; DRY |

---

## 3. Scoring Mechanics

### 3.1 Applicability & Denominator Adjustment

For each scan, the **applicable denominator** is computed:

```
applicable_points = sum(subcheck.points for subcheck where applies(project_type, project_config))
```

A subcheck is **not applicable** if:
- Project type lacks the capability (e.g., no database → DB checks N/A)
- Project size/scope makes check unreasonable (e.g., single-file script → module boundaries N/A)
- Tool support unavailable for language (e.g., no Semgrep rules for language)

**Score Calculation:**

```
raw_score = sum(earned_points for applicable subchecks)
percentage = (raw_score / applicable_points) * 100
final_score = round(percentage)
```

### 3.2 Partial Credit

| Outcome | Credit |
|---|---|
| Check passes (evidence confirms) | 100% of subcheck points |
| Check fails (evidence confirms defect) | 0% |
| Check skipped (tool error/unavailable) | 0% (counts against coverage) |
| Check not applicable | Excluded from denominator |
| Heuristic finding (likely but unverified) | 50% penalty of severity weight |
| Verified defect (execution confirmed) | 100% penalty |

### 3.3 Coverage Calculation

```
coverage = (applicable_checks_with_evidence / total_applicable_checks) * 100
```

- "Evidence" = at least one tool ran and produced a result (pass/fail/error)
- "Skipped" (tool unavailable) → reduces coverage
- "Not applicable" → excluded from both numerator and denominator

### 3.4 Confidence Calculation

```
confidence = weighted_average(
  finding.confidence_weight * finding.severity_weight
  for all findings in scan
)
```

| Confidence Level | Weight |
|---|---:|
| `verified` (execution confirmed) | 1.0 |
| `likely` (static analysis + pattern) | 0.7 |
| `heuristic` (pattern only) | 0.4 |
| `info` (recommendation) | 0.2 |

Reported as percentage (0-100%). Low confidence = findings are mostly heuristic.

---

## 4. Grade Bands

| Score Range | Grade | Readiness Verdict |
|---|---|---|
| 90-100 | A | **Production Ready** — Strong evidence across all dimensions |
| 80-89 | B | **Near Production** — Minor gaps; address top findings |
| 70-79 | C | **Functional MVP** — Works but has identifiable weaknesses |
| 60-69 | D | **Prototype** — Significant gaps; not production suitable |
| 0-59 | F | **Not Ready** — Critical failures; major rework needed |

**Readiness Modifiers:**
- **Critical Blocker Present** → Verdict capped at "Not Production Ready" regardless of score
- **Coverage < 50%** → Verdict: "Insufficient Evidence" (score unreliable)
- **Confidence < 40%** → Verdict: "Low Confidence" (mostly heuristic findings)

---

## 5. Critical Blocker Definitions

A **Critical Blocker** is a finding that:
1. Has `severity = critical` AND `confidence = verified` OR `likely`
2. Falls in Security dimension (`sec.*`)
3. Represents an exploitable vulnerability or data exposure

**Effect:** Report displays prominent "🚨 CRITICAL BLOCKER" banner. Readiness verdict forced to "Not Production Ready". Score still calculated but contextualized.

---

## 6. Rubric Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-10-11 | Initial release; 10 dimensions, 42 subchecks |

**Future Versions:** Must preserve v1.0 for historical comparison. New versions add/modify subchecks with clear changelog. Scoring engine must accept `rubric_version` parameter.

---

## 7. Calibration Plan (Post-MVP)

1. **Benchmark Suite** (Phase 5): 20-30 representative projects with known quality levels
2. **Ground Truth**: Expert manual grading of benchmark projects
3. **Metrics**: Precision/recall for findings; score correlation with expert judgment
4. **Adjustment**: Weight tuning based on evidence; documented in rubric v1.1+

---

## 8. Rubric as Data (Machine-Readable)

The rubric is stored as `rubric/v1.yaml` (see implementation). This enables:
- Versioned, inspectable scoring rules
- Non-developer review of criteria
- Automated testing of scoring engine
- Future UI for custom rubric authoring

```yaml
# Example structure (abbreviated)
version: "1.0"
dimensions:
  - code: functional_correctness
    weight: 20
    subchecks:
      - id: fc.build_success
        points: 5
        applies: ["all"]
        evidence: ["build_exit_code"]
      - id: fc.core_workflow
        points: 6
        applies: ["web_app", "api", "cli", "agent"]
        evidence: ["verification_result"]
```

---

*This rubric is a living document. Calibration against real projects will drive evidence-based adjustments.*