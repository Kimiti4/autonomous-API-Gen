# Cross-Report Executive Summary — PROD-A01 + EV-A01…EV-A09 (+ Bandit verification)

- **Canonical audited state:** `6e1aa1a` (PR #1 head, `evolution/second-backend-lowering-hardening`); remote `main` tip `1f26e42`.
- **Method:** synthesis only — no new probes; every claim already carries evidence in the linked report.
- **Audience:** release / merge decision for PR #1 and production-readiness posture of the Evolution Engine platform.
- **Companion note:** `docs/BANDIT-FIX-VERIFICATION.md` (EV-A01-001 follow-up; does not restate EV-A02).

---

## 0. One-line verdict

**NOT READY TO MERGE AS A GREEN GATE, and NOT READY FOR PRODUCTION OPERATION.**  
The compiler/evolution core is real and often fail-closed; the **trust chain, security boundary, deployment happy-path, observability loop, change safety, and governance enforcement** each fail their own audit. CI on the PR head is red (`security-scan` + platform tests).

## 1. Sequence scorecard

| Gate | Report | Status | Register | Headline |
|---|---|---|---|---|
| PROD-A01 | `docs/PROD-A01-deployment-inventory.md` | inventory (no PASS/FAIL) | PROD-001…017 class | Platform runtime largely **real**; Deployment Engine library **unwired/simulated**; **zero CD** |
| EV-A01 | `docs/EV-A01-repo-ci-integrity.md` | **RED CI / findings OPEN** | 001…011 | PR-caused Bandit + non-hermetic tests; supply-chain & review controls off; green ≠ certified |
| EV-A02 | `docs/EV-A02-artifact-correctness.md` | **FAIL** | 001…012 | Static evidence can “verify” non-compilable artifacts; promotion binds genome ≠ artifact; Go non-runtime evidence is a stub |
| EV-A03 | `docs/EV-A03-capability-truthfulness.md` | **FAIL** | 001…010 | Capability badges over-claim; `logging_level` false-negative; Go auth fail-open vs Python fail-closed |
| EV-A04 | `docs/EV-A04-security-boundary.md` | **FAIL** | 001…017 | Anonymous `/stream`; 429→500 operator lockout; WS 4401 over-claim; 0/17 published security declarations |
| EV-A05 | `docs/EV-A05-deployment.md` | **FAIL** | 001…014 | No path sets production env; compose cannot inject `ADMIN_API_KEY`; proxy flattens rate limits; `ssl` profile is HTTP-only |
| EV-A06 | `docs/EV-A06-observability.md` | **FAIL** | 001…012 | `traceId` never reaches logs; 12 domain metrics unwired; failed auth never logged; redactor uninstalled |
| EV-A07 | `docs/EV-A07-schema-observation-integrity.md` | **FAIL** | 001…012 | Production observation store: three stacked faults → `/observation/state` 500; dead components green via mocks |
| EV-A08 | `docs/EV-A08-change-safety.md` | **FAIL** | 001…012 | No migrations; no restore; no rollback actuation; no evolve single-flight; CI gates tests, not change safety |
| EV-A09 | `docs/EV-A09-governance.md` | **FAIL** | 001…012 | Governance stacks exist as libraries; **product API constructs none of them**; promotion ungated |
| Bandit track | `docs/BANDIT-FIX-VERIFICATION.md` | **REMEDIATION NOT VERIFIED** | BANDIT-V-001…006 | `6e1aa1a` one-liner does not clear `security-scan`; EV-A02 implications unchanged |

**Aggregate: 8× FAIL (EV-A02…EV-A09) + EV-A01 CI red + Bandit fix ineffective. No gate PASS.**

## 2. What is genuinely real (keep — do not regress)

Recorded across reports so remediation does not tear down working controls:

1. **Deterministic dual-backend generation** (byte-identical Python/Go per genome) and fail-closed compiler boundary (EV-A02 E1/E2/E5).
2. **Real Docker runtime verification** of Python candidates with layered probes and fail-closed fitness (runtime fail ⇒ zero fitness) (PROD-A01 §1.5, EV-A02).
3. **Platform control boundary:** deny-by-default on `/evolve` + `/production/readiness`, WS auth-before-accept, production Settings refuse to start without secrets (PROD-A01 §1.1/§1.4, EV-A04 core).
4. **CI substance:** Postgres integration service, real Go compile+execute job, evidence-manifest check before GHCR push, fail-closed `needs` chains, Bandit gate that actually fails the run (EV-A01 §13).
5. **Contract kernel** (errors/events/provenance, UUIDv7, canonical hashes, lock-correct sequences, 63-test observation suite green) (EV-A07).
6. **Library-grade governance** (Phase 28 kernel, HMAC evidence signing, G-1..G-7 models, kill-switch/interlock tests) — correct as libraries, **unwired** as product (EV-A09).

## 3. Thematic blocker clusters (cross-report)

### A. Truth vs claim (blocks trust in every later stage)
- Static/`verified` can certify uncompilable artifacts; Go evidence is a stub (EV-A02-001, EV-A03-002).
- Capability contract lies (`logging_level`) distort scores (EV-A02-008, EV-A03-001).
- Published security surface documents 0/17 declarations (EV-A04).
- **Consequence:** promotion and “certified” language cannot be taken at face value until per-candidate compile gates + honest evidence exist.

### B. Identity & provenance gaps (blocks audit and rollback)
- No artifact digest at promotion; host paths in records; uncleaned materialize (EV-A02-002…004).
- No migrations/restore; SQLite non-WAL; torn JSON writes (EV-A08-001…005).
- **Consequence:** cannot prove *which bytes* were promoted, cannot safely change schema, cannot restore a backup.

### C. Security posture split (platform vs Go artifact vs docs)
- Platform: fail-closed keys but anonymous `/stream`, rate-limit lockout, silent 401s (EV-A04, EV-A06-003).
- Generated Go: fail-open default credentials; CI signs JWTs with that default (EV-A02-007, EV-A03-007).
- Docs/compose: teach validator-bypassing `SECRET_KEY`, duplicate timing-unsafe middleware, unreachable Postgres URL (EV-A05-003/005).
- **Consequence:** mixed-fleet or Go-target deployments inherit known fail-open auth; operators following the guide worsen the boundary.

### D. Deploy & observe (blocks operating it)
- Zero CD; every documented path stays development-mode; proxy collapses rate limiting; `ssl` terminates no TLS (PROD-A01, EV-A05).
- Error `traceId` orphaned; domain metrics never wired; no failed-auth log (EV-A06).
- Production observation endpoints 500 under the env the deployment guide should use (EV-A07-001).
- **Consequence:** even a correctly built image cannot be operated with a closed loop (detect → record → act).

### E. Change & governance (blocks running it for real)
- No schema migration, no restore, no rollback traffic/DB actuation, no evolve single-flight (EV-A08).
- Product never constructs governance/evidence/lineage subsystems; promotion has no guard; defaults hollow G-6/G-7 (EV-A09).
- **Consequence:** the system can evolve code only by hand-editing prod; promotions are ungated; audit trails die with the process.

### F. Repo/CI integrity (blocks merging “green”)
- PR head red: Bandit B608 fix **ineffective** (`BANDIT-V-002/003`); 2 non-hermetic tests (EV-A01-001/002).
- Supply-chain knobs off; no required review; no PR ever merged; CodeQL only on main + 5 open alerts (EV-A01-005…008).
- Green certification jobs on PR skip publish/certify paths — green ≠ certified (EV-A01-007).

## 4. Merge decision inputs (PR #1)

| Criterion | Evidence | Met? |
|---|---|---|
| PR CI fully green | `security-scan` failure; `test (3.12)` failure; 3.11/3.13 cancelled @ `6e1aa1a` | **No** |
| Bandit remediation verified | `docs/BANDIT-FIX-VERIFICATION.md` — exit 1, nosec counters 0 | **No** |
| Non-hermetic tests fixed | EV-A01-002 still OPEN | **No** |
| No new security regressions vs main | Go fail-open + `/stream` etc. are platform findings; B608 PR-caused | **Mixed** (PR-caused scanner red; broader issues pre-date PR content) |
| Governance/review process | No required review; direct pushes proven | **No** (server-side) |

**Recommendation (evidence-based):** do **not** treat PR #1 as mergeable on green-gate claims until `security-scan` and hermetic tests pass under independent re-run; apply the comment-proven Bandit shape; keep EV-A02 findings intact.

## 5. Remediation priority (ordered, cross-report)

| P | Item | Closes / advances |
|---|---|---|
| P0 | Land effective Bandit fix; re-verify `security-scan` success | EV-A01-001, BANDIT-V-002…004 |
| P0 | Make fail-closed tests hermetic (fixture DB / migrations in test) | EV-A01-002 |
| P0 | Per-candidate `py_compile`/`go vet` in static evidence; delete Go `{verified: True}` stub | EV-A02-001, EV-A03-002 |
| P0 | Stop shipping Go default credentials (env-required) | EV-A02-007, EV-A03-007, EV-A04 carry-over |
| P1 | Auth for `/stream`; fix rate-limit keying + 429 contract; log failed auth; wire `traceId` to loguru | EV-A04-001…, EV-A06-001/003 |
| P1 | Artifact digest at promotion + clean materialize + on-disk manifest | EV-A02-002…004 |
| P1 | Fix observation production path (async binding, `init_db` tables, execute `schema.sql`) | EV-A07-001, EV-A08 schema story |
| P2 | Alembic + backup **restore** drill; evolve single-flight; WAL | EV-A08-001/002/004 |
| P2 | Wire governance/evidence/lineage + promotion guard on product | EV-A09-001 |
| P2 | Deployment happy-path: compose env injection, real TLS profile, proxy-aware rate limit, kill guide’s duplicate middleware | EV-A05-001…007 |
| P3 | Supply-chain: Dependabot, pin actions/bases, require review, CodeQL alerts | EV-A01-005…008 |
| P3 | Zero-CD honesty: document GHCR-stop boundary or implement CD | PROD-A01, EV-A05 |

## 6. Explicit non-goals of this summary

- Does **not** re-open or edit any EV-A0x finding register.
- Does **not** reclassify EV-A02 based on the Bandit attempt (see Bandit track §3).
- Does **not** claim production PASS anywhere; every FAIL stands until its own report is superseded by a new audited state.

## 7. Report index

```
docs/PROD-A01-deployment-inventory.md
docs/EV-A01-repo-ci-integrity.md
docs/EV-A02-artifact-correctness.md
docs/EV-A03-capability-truthfulness.md
docs/EV-A04-security-boundary.md
docs/EV-A05-deployment.md
docs/EV-A06-observability.md
docs/EV-A07-schema-observation-integrity.md
docs/EV-A08-change-safety.md
docs/EV-A09-governance.md
docs/BANDIT-FIX-VERIFICATION.md
docs/EV-EXECUTIVE-SUMMARY.md          ← this file
```
