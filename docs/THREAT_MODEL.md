# VibeGrade — Threat Model

**Version:** 1.0
**Date:** October 11, 2026
**Scope:** MVP (Phases 1-2) — Standalone web application with public repository scanning

---

## 1. System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Browser  │────▶│  VibeGrade Web  │────▶│  GitHub API     │
│   (HTTPS)       │     │  App (FastAPI)  │     │  (Public)       │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  SQLite DB    │         │  Sandbox      │
            │  (Scans,      │         │  (Docker      │
            │   Findings,   │         │   Containers) │
            │   Evidence)   │         └───────────────┘
            └───────────────┘
```

**Trust Boundaries:**
1. **Internet → Web App** — Untrusted users, public internet
2. **Web App → GitHub API** — Outbound only; read-only public data
3. **Web App → Database** — Trusted internal; authenticated
4. **Web App → Sandbox** — **Critical boundary**; untrusted code execution
5. **Sandbox → Host** — Must be fully isolated; no access to host resources

---

## 2. Assets & Sensitivity Classification

| Asset | Sensitivity | Description |
|---|---|---|
| User-submitted repository URLs | Low | Public GitHub URLs; no secrets |
| Cloned repository source code | Medium | Untrusted input; may contain secrets (user's own) |
| Scan results & findings | Low-Medium | Derived data; no source code stored |
| Evidence blobs (tool output) | Low | Normalized findings; sanitized logs |
| Application configuration/secrets | **Critical** | DB credentials, API keys, encryption keys |
| User session tokens | High | Authentication state |
| Sandbox container runtime | **Critical** | Execution environment for untrusted code |

---

## 3. Threat Enumeration (STRIDE)

### 3.1 Spoofing

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| S-1 | User impersonation via stolen session | Medium | High | HttpOnly Secure SameSite=Strict cookies; short expiry; rotation |
| S-2 | GitHub webhook spoofing (future) | Low | Medium | Verify webhook signatures; not applicable to MVP |
| S-3 | Sandbox masquerading as host service | Low | Critical | Network isolation; no metadata service access |

### 3.2 Tampering

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| T-1 | Database injection (SQL/NoSQL) | Low | Critical | Parameterized queries (SQLAlchemy ORM); input validation |
| T-2 | Scan result modification | Low | Medium | Immutable scan records; append-only evidence; audit log |
| T-3 | Repository source tampering during clone | Medium | High | Shallow clone at immutable SHA; verify checksum |
| T-4 | Sandbox escape → host filesystem tampering | Low | **Critical** | Docker isolation; read-only rootfs; no privileged caps; user namespace mapping |
| T-5 | Evidence/log injection (XSS in report) | Medium | High | Sanitize all stored outputs; CSP headers; React auto-escaping |

### 3.3 Repudiation

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | User denies submitting scan | Low | Low | Audit log with timestamp, IP, user agent, repo URL |
| R-2 | Scan result disputed | Low | Medium | Immutable evidence store; reproducible scoring |
| R-3 | Admin action not logged | Low | Medium | Structured audit logging for all privileged operations |

### 3.4 Information Disclosure

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| I-1 | Private repo access via URL manipulation | Medium | High | **MVP: Public repos only**; validate public via API before clone |
| I-2 | Cross-user scan data access | Medium | High | Row-level authorization; user_id on all scan records |
| I-3 | Source code leakage from sandbox | Low | **Critical** | No source code persisted; sandbox ephemeral; logs sanitized |
| I-4 | Application secrets in logs/errors | Medium | High | Structured logging; secret redaction; no debug mode in prod |
| I-5 | Dependency confusion / supply chain | Medium | High | Pin all dependencies; verify hashes; private registry for prod |
| I-6 | Sandbox network access to internal services | Low | Critical | **Default deny egress**; explicit allowlist only for required registries |

### 3.5 Denial of Service

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| D-1 | Resource exhaustion via large repo | High | High | Size limit (500MB); shallow clone; disk quota in sandbox |
| D-2 | CPU/memory exhaustion in sandbox | High | High | **Hard limits**: cgroups (CPU shares, memory max, pids max) |
| D-3 | Time exhaustion (infinite loops) | Medium | High | **Wall-clock timeout** per check (default 120s); subprocess timeout |
| D-4 | Archive bombs / zip slips | Low | High | Safe extraction; path traversal checks; size limits per file |
| D-5 | GitHub API rate limit exhaustion | Medium | Medium | Cache; exponential backoff; respect `Retry-After` |
| D-6 | Concurrent scan queue exhaustion | Medium | Medium | Per-user concurrency limit; global queue with backpressure |

### 3.6 Elevation of Privilege

| ID | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| E-1 | Sandbox breakout → host root | Low | **Critical** | Non-root user in container; drop all capabilities; seccomp profile |
| E-2 | Container → other containers | Low | Critical | User namespace mapping; separate networks per scan |
| E-3 | Tool execution with elevated perms | Low | High | Run all tools as non-root `scanner` user |
| E-4 | Path traversal in file operations | Medium | High | `pathlib` resolution; `resolve()`; validate within workdir |
| E-5 | Dependency installation runs arbitrary scripts | Medium | High | **No `npm install`/`pip install` with arbitrary scripts in MVP**; use `--ignore-scripts` or lockfile-only |

---

## 4. Sandbox Security Requirements (Phase 2)

### 4.1 Container Hardening (Docker)

```dockerfile
# Base principles for scan containers
FROM python:3.12-slim AS base

# Non-root user
RUN useradd -u 10001 -r -g nogroup -m -d /home/scanner -s /bin/bash scanner

# No capabilities, read-only rootfs where possible
# --cap-drop=ALL --security-opt=no-new-privileges:true
# --read-only --tmpfs /tmp --tmpfs /home/scanner

# Resource limits (enforced at runtime)
# --cpus="2" --memory="2g" --pids-limit=100 --ulimit nofile=1024:1024

# Network isolation
# --network=none  (default)
# --network=scan-net  (explicit allowlist only)
```

### 4.2 Runtime Limits (Per Check)

| Resource | Limit | Enforcement |
|---|---|---|
| CPU time | 120 seconds wall-clock | `timeout` + Docker `--cpus` |
| Memory | 2 GB | Docker `--memory=2g` |
| Processes | 100 | Docker `--pids-limit=100` |
| Disk (workdir) | 5 GB | Docker `--tmpfs` size + host monitoring |
| Open files | 1024 | `ulimit -n 1024` |
| Network | **None by default** | Docker `--network=none` |
| Execution user | `scanner` (UID 10001) | Docker `USER scanner` |

### 4.3 Allowed Network Policies (Explicit Opt-In)

| Purpose | Destination | Protocol | Justification |
|---|---|---|---|
| Package registry | `registry.npmjs.org`, `pypi.org`, `crates.io` | HTTPS | Dependency install (if enabled) |
| GitHub API | `api.github.com` | HTTPS | Not needed for public clone (shallow) |

**Default:** No network access. Network policy is a scan configuration option, not automatic.

---

## 5. Data Handling & Retention

| Data Type | Retention | Deletion Trigger |
|---|---|---|
| Cloned repository | **Zero** (ephemeral) | Immediately after scan completes |
| Scan metadata | 90 days (configurable) | User deletion request; auto-expiry |
| Findings & evidence | 90 days (configurable) | Tied to scan retention |
| Audit logs | 1 year | Compliance requirement |
| User account | Until deletion | User request (GDPR/CCPA) |

**Principles:**
- Source code **never** persisted to database or disk beyond scan lifetime
- Evidence stores **normalized findings only** (file, line, rule, message)
- Logs sanitized: no secrets, tokens, PII, source code snippets > 200 chars

---

## 6. Authentication & Authorization (MVP)

### 6.1 MVP: Anonymous Public Scans
- No authentication required for public repository scans
- Scan linked to **anonymous session** (cookie) or **IP-based** (fallback)
- User can claim scans via email verification (future)

### 6.2 Post-MVP: Authenticated Scans
- Email/password + TOTP MFA (like Fiduciary OS pattern)
- Session: DB-backed, expiring, revocable, throttled login
- Row-level authorization: `scan.user_id = current_user.id`

### 6.3 Private Repository Access (Future)
- GitHub OAuth App installation
- Token stored encrypted (AES-GCM); short-lived; scoped to `repo:read`
- Scan authorized only if token valid and repo accessible

---

## 7. Security Testing Requirements

| Test | Phase | Method |
|---|---|---|
| SQL injection attempts | 1 | Automated (sqlmap) + unit tests |
| XSS in finding display | 1 | Unit tests (React escaping); CSP verification |
| Path traversal in file ops | 1 | Unit tests with malicious paths |
| Sandbox escape attempts | 2 | Custom test suite: procfs, sysfs, capabilities, network |
| Resource exhaustion | 2 | Fork bomb, memory allocation, infinite loop, large files |
| Cross-scan data access | 1 | Integration tests with multiple users |
| Secret leakage in logs | 1 | Log scanning in CI; secret detection in test fixtures |

---

## 8. Incident Response Considerations

| Scenario | Detection | Response |
|---|---|---|
| Sandbox escape suspected | Container monitoring (unexpected processes, network) | Immediate container kill; isolate host; forensic snapshot |
| Source code leaked in logs | Log scanning alerts | Rotate affected secrets; notify users; purge logs |
| Database breach | Audit log anomalies; unexpected queries | Revoke DB credentials; restore from backup; notify |
| Supply chain compromise | Dependency scan failures; SBOM drift | Pin versions; investigate; rebuild images |

---

## 9. Compliance & Privacy

- **GDPR/CCPA**: No PII collected for anonymous scans; email only for account creation (opt-in)
- **Source Code**: Never stored; processed in-memory/ephemeral disk only
- **Audit Trail**: All scan operations logged without sensitive content
- **Data Processing Agreement**: Required for enterprise/private repo features

---

## 10. Residual Risks (Accepted for MVP)

| Risk | Acceptance Reason | Monitoring |
|---|---|---|
| GitHub API rate limits (60/hr unauth) | Public MVP scope; documented limitation | Rate limit headers logged; user-facing notice |
| False positives from static tools | Inherent to static analysis; confidence labeling mitigates | Track FP rate via user feedback |
| No sandbox in environments without Docker | Documented limitation; runtime checks disabled gracefully | Health endpoint reports sandbox availability |
| Unauthenticated scan abuse | Rate limiting per IP; no persistent harm | Monitor scan queue depth; auto-cleanup |

---

*This threat model must be reviewed before Phase 2 (sandbox implementation) and whenever architecture changes.*