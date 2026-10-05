# EV-A09 — Governance

**Audit:** evidence-first production readiness, sequence EV-A01 → … → EV-A08 → **EV-A09 Governance (final)**
**Canonical audited state:** `6e1aa1a` (PR #1 head; main `1f26e42`)
**Scope:** candidate lifecycle governance (G-1..G-7), Phase 28 Governance Kernel / PEP / evidence signing, approval workflows, learning kill-switch controls, certification registry, compiler production gate, marketplace governance gateway, and whether any of it is **enforced on the shipped API** (`autonomous-api/`). Read-only.
**Taxonomy:** `IMPLEMENTED_REAL / IMPLEMENTED_BOUNDED / IMPLEMENTED_SIMULATED / PARTIAL / UNIMPLEMENTED / UNKNOWN` · Confidence `CONFIRMED / INFERRED / UNVERIFIED`.

---

## STATUS: **FAIL**

The workspace contains several **well-built, well-tested governance stacks** — Phase 28 kernel with hash-chained audit and HMAC evidence signing, G-1..G-7 lifecycle invariants, learning kill-switch + human-approval interlocks, compiler certification gates, CBC-1 regression registry. Almost none of it is **wired into the product API**. The shipped service never constructs `GovernanceSubsystem`, `EvidenceSubsystem`, or `LineageSubsystem`; never imports `GovernanceKernel`, `PEPEnforcer`, or `EvolutionPromotionGuard`; evolution runs promote “best” candidates and emit `candidate.promoted` with **no gate, quorum, certification, or promotion guard**. Where the subsystem *is* exercised (tests), two default-config defects hollow out the authority model: empty `recognized_certifiers` **skips G-6 entirely**, and the Executive (allowed by G-5) has **voting weight 0** so can never satisfy G-7. Audit trails default to **in-memory** structures that vanish on restart; production Postgres stores for governance are comment-only. Signing is correct but **opt-in and off by default**.

Register: **EV-A09-001 … EV-A09-012**.

---

## 1. Surface inventory

| Governance layer | Location | Wired to product? | Verdict |
|---|---|---|---|
| Candidate lifecycle subsystem (G-1..G-7) | `autonomous-api/app/governance/subsystem.py` + `core/governance/*` | **No** — construction only in `tests/observation/*` (probe: `NOT_CONSTRUCTED_IN_APP`) | `[UNIMPLEMENTED]` as runtime (001) |
| Evidence / Lineage subsystems | `app/evidence/subsystem.py`, `app/lineage/subsystem.py` | **No** (same probe) | `[UNIMPLEMENTED]` as runtime (001) |
| Governance/Lineage observation projectors | `app/observation/projectors/{governance,lineage}.py` | **No routes** (EV-A07-002) | `[PARTIAL]` (008) |
| Phase 28 `GovernanceKernel` + PDP/PEP | `constitutional_architecture/governance/kernel.py`, `pep/*` | **No** — `kernel_in_app: NONE` | `[IMPLEMENTED_REAL]` library, `[UNIMPLEMENTED]` product wiring (001) |
| `EvolutionPromotionGuard` | `pep/evolution_guard.py` | Tests only (`test_governance_pep.py`) | `[IMPLEMENTED_REAL]` library / unwired (001) |
| `GovernedKernel` evidence wrapper | `governance/integration.py` | Opt-in; marketplace default **off** (`use_governance_extensions=False`) | `[IMPLEMENTED_BOUNDED]` (005) |
| HMAC evidence signing | `governance/evidence_signing.py` | Config-gated; no key → unsigned + warning | `[IMPLEMENTED_REAL]` (010) |
| Approval workflow (timeout DENY) | `governance/approval_workflow.py` | Via kernel only; in-memory store | `[IMPLEMENTED_BOUNDED]` (004) |
| Hash-chained audit | `governance/audit.py` | In-process lists/dicts; no disk backend | `[IMPLEMENTED_BOUNDED]` (004) |
| File-backed constitution versions | `governance/versioning.py` | Exists (fsync+replace); marketplace wires **InMemory** instead | `[IMPLEMENTED_REAL]` unused (010) |
| Governance dashboard | `governance/dashboard/*` | Separate; in-memory sessions + CSRF + role perms | `[IMPLEMENTED_BOUNDED]` (009) |
| Learning safety / kill switch | `learning/governance/{safety,engine,api}.py` | `enable_learning_governance(app)` never called by `autonomous-api` | `[PARTIAL]` (006) |
| Compiler production gate | `compiler/governance/{enforcer,compiler,routes}.py` | Own routes in `compiler` package, not mounted on product API | `[IMPLEMENTED_REAL]` / unwired (001) |
| Marketplace `GovernanceGateway` | `marketplace_plugins/engine.py` | Kernel or reference heuristic; extensions default off | `[IMPLEMENTED_BOUNDED]` (005) |
| Certification registry + regressions | `certification/governance/registry.py` | Hash-chained JSONL under gitignored `release/evidence/` | `[PARTIAL]` (007) |
| Escalation policy | `certification/governance/escalation_policy.py` | Tested (24 tests); certification harness only | `[IMPLEMENTED_REAL]` / not product API (010) |
| Product_factory human-approval policies | `product_factory/**` | Real policy checks in that package; not imported by `autonomous-api` | `[IMPLEMENTED_BOUNDED]` |

---

## 2. The product API is ungoverned

### EV-A09-001 — No governance enforcement on the shipped service: subsystems exist only under test, kernel/PEP/guard never imported by `app/`, evolution promotes without gates
`[UNIMPLEMENTED]` · Confidence **CONFIRMED** (probe + static)

- Probe across `autonomous-api/app/**/*.py`:
  - `GovernanceSubsystem(` / `EvidenceSubsystem(` / `LineageSubsystem(` → **`NOT_CONSTRUCTED_IN_APP`** (non-test construction hits: `[]`).
  - `GovernanceKernel` / `EvolutionPromotionGuard` / `PEPEnforcer` → **`kernel_in_app: NONE`**.
- Grep: only `tests/observation/test_governance_subsystem.py:43` (and sibling evidence/lineage tests) instantiate the subsystems. `main.py` mounts routers, dispatcher, fitness projector — **no governance composition root**, no `configure_governance` analogous to `configure_observation`.
- Actual promotion path (`engine/evolution.py:83-85,108`): fitness comparison → `_emit_update(new_best → candidate.promoted)` → `build_genome_output`. **No call** into G-2 gates, G-7 quorum, certification, or `guard_promote`. `production_gate.py` / `ProductionReadinessAnalyzer` run as *scoring* on the result dict (`evolution.py:108`) — they do not block the run or the DB write of genomes (`:86-88` commits regardless).
- Claim vs reality: `subsystem.py:1-4` — “The ONLY subsystem authorized to advance a candidate's lifecycle state.” Nothing in the running process ever asks it. Lifecycle states (`intake→…→certified`, `contracts/governance.py:18-53`) are contract fiction for the product surface.
- Cross-refs: EV-A07-002 (advertised `platform.observation.candidates`/governance schemas with no routes), EV-A03 capability truthfulness pattern.

---

## 3. Default configuration hollows the invariants

### EV-A09-002 — G-6 certifier allow-list is skipped when `recognized_certifiers` is empty (the default)
`[PARTIAL]` · Confidence **CONFIRMED** (static + source probe)

```python
# subsystem.py:125
if self._certifiers and cmd.certifiedBy not in self._certifiers:
    raise ... "G-6 violated ..."
```
`__init__` defaults `recognized_certifiers=None` → `set()` (`:61`). **Empty set is falsy → the entire G-6 check short-circuits.** Probe: `g6_check_condition True` / `g6_when_empty_set SKIPS enforcement`.

Effect: the documented invariant “recognized certifying authority” is **optional-by-default**. A composition root that forgets to pass certifiers gets a silently open certification path — the opposite of fail-closed (contrast: production auth `validate_auth_config` *does* fail closed).

### EV-A09-003 — Executive can authorize in G-5 but can never carry quorum in G-7; unused `Executive.quorumThreshold=0.6`
`[PARTIAL]` · Confidence **CONFIRMED** (probe)

- G-5 allows deciders ∈ council ∪ `{“executive”}` (`invariants.py:94`).
- G-7 sums **only council voting weights**; missing id → `0.0` (`:109-115`). Probe: `check_g7_quorum_weight(['executive'], CouncilComposition(), 1.0)` → **`DENIED G-7 … weight 0.00 < 1.00`**.
- Subsystem default `quorum_threshold=1.0` (`subsystem.py:55`); `Executive.quorumThreshold=0.6` (`executive.py:7`) is **never read** by the subsystem (dead constant).
- Net: the named Executive role is a **G-5-only fiction** for transition-authorizing approvals — every approve hits G-7 and needs council members who were never registered on the unwired path. Fail-closed for empty council (good accident), broken for the designed Executive override (bad).

---

## 4. Audit and approval durability

### EV-A09-004 — Phase 28 audit, approvals, and default governance stores are process-memory only; restart destroys the hash chain
`[IMPLEMENTED_BOUNDED]` · Confidence **CONFIRMED** (static)

- `AuditFramework.__init__` (`audit.py:26-30`): `_events: List`, `_decision_dossiers/_approvals: Dict` — **no file/DB backend**. `verify_chain()` is real but only over the current process’s list (`kernel.audit_chain_intact`).
- `ApprovalWorkflowEngine` (`approval_workflow.py:31-32`): same pattern.
- App-side: `InMemoryGovernanceEventStore` / `ReferenceStore` (`adapters/memory.py`) — docstring admits “Production backends (PostgreSQL event log + registry tables) implement the same ports” — **those ports have no non-test implementation** (grep: only memory adapter).
- Marketplace extensions path constructs `VersionManager(InMemoryConstitutionVersionRepository(), …)` (`marketplace_plugins/engine.py:67-69`) while the durable `FileBackedConstitutionVersionRepository` (fsync+replace, EV-A08-010) **exists unused there**.
- Consequence: “tamper-evident append-only audit” is true only until the process dies; durable governance audit requires the same missing production adapters as EV-A09-001.

---

## 5. Signing, learning, registry — real code, weak defaults or weak seats

### EV-A09-005 — Evidence signing and `GovernedKernel` are correct but opt-in; marketplace default disables both
`[IMPLEMENTED_BOUNDED]` · Confidence **CONFIRMED**

- `new_evidence_recorder()` without `AUDIT_EVIDENCE_SIGNING_KEY` → unsigned recorder + warning (`evidence_signing.py:28-30`); HMAC roundtrip and backward-compat unsigned tests green (`test_phase28_evidence_signing.py`).
- `GovernanceGateway.__init__(..., use_governance_extensions: bool = False)` (`marketplace_plugins/engine.py:55-79`) — default path is raw kernel or **reference heuristic** (`_evaluate_reference`: three capabilities → REQUIRE_APPROVAL else ALLOW), no evidence ledger, no amendment check.
- Honest docs (integration.py wiring sketch is commented-out). Still: production posture is “governance extensions if someone remembers the flag.”

### EV-A09-006 — Learning kill-switch and approval API: solid interlocks, **no auth on routes**, never mounted on the product app
`[PARTIAL]` · Confidence **CONFIRMED** (static)

- `LearningSafetyEngine` correctly blocks on kill switch, evidence quality failure, rate limits; flags `required_human_approval` for critical security / high pressure / governance bundles (`safety.py:36-69`). Design matches AGENTS (feedback → governance, not raw ISR mutation).
- `learning/governance/api.py` exposes `/evaluate`, `/sync`, `/approvals/*`, **kill-switch activate/deactivate** with **no `Depends(require_auth)` / API-key check** in the module (routes are plain handlers; `enable_learning_governance` only wires engine state).
- Nothing in `autonomous-api` calls `enable_learning_governance` or imports `learning.governance` (grep: learning consumers are tests + `certification` + `release/gates`). **Product API has no kill switch.** (EV-A08-008 feature-flag gap reinforced from the governance angle.)

### EV-A09-007 — Certification governance registry is hash-chained but lives on a gitignored path; local chain is not an audit system of record
`[PARTIAL]` · Confidence **CONFIRMED**

- `DEFAULT_PATH = "release/evidence/cbc1-governance.jsonl"`; header: “Per .gitignore, `release/evidence/` is gitignored. The registry file is **regenerated from the policy log** on every run; auditors archive their own copies.” (`.gitignore:27`).
- CI release gates **do** upload `release/evidence/` as artifacts with 90-day retention and fail if `aggregate.yaml` ≠ CERTIFIED (`v1.4-release-gate.yml`, `cbc1-release-gate.yml`) — good episodic capture (010) — but the cross-phase regression ledger is not a durable, independently verifiable store between runs.
- `detect_regressions()` logic is real and tested (`tests/cbc1/test_governance_registry.py`).

### EV-A09-008 — Governance decisions are invisible on the product API (projector + adapter unrouted)
`[PARTIAL]` · Confidence **CONFIRMED** (EV-A07-002 cross-ref)

`GovernanceProjector` / `GovernanceObservationAdapter` exist; no `observation_routes` handler serves them; capabilities still advertises `platform.observation.candidates` governance-shaped schemas. Even if subsystem were wired, operators could not read decisions over HTTP without new routes.

---

## 6. Dashboard and separate-plane governance

### EV-A09-009 — Governance dashboard: reasonable web controls (session TTL, CSRF compare_digest, role permissions), in-memory sessions, kernel still authoritative for mutations — but not part of the product deployment
`[IMPLEMENTED_BOUNDED]` · Confidence **CONFIRMED** (static)

`dashboard/auth.py` — `secrets.token_urlsafe` session+CSRF, TTL re-check, `secrets.compare_digest` on CSRF, permission split (`read`/`approve`/`revoke_exception`/`verify_integrity`), docstring: every mutation re-checked by kernel. Limits: `_sessions` dict in memory; users from `DashboardConfig`; not composed into `autonomous-api` deployment (EV-A05 topology has no dashboard gov seat).

### EV-A09-010 — What is genuinely strong (positives)
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

- **G-1..G-7 invariant functions** with dedicated tests (`test_governance_subsystem.py`: quorum weight, gate satisfaction, transition legality, waiver accountability) — when *called*, they raise correctly (probe confirmed G-7 denial).
- **Phase 28 kernel flow** evaluate → require approvals → finalize → audit dossier reconstruct; approval **timeout policy DENY_ON_TIMEOUT**; exception revoke with audit event (`kernel.py:160-225`).
- **Hash-chained audit** recompute + `verify_chain` / `audit_chain_intact` (`audit.py:57-58`, `kernel.py:236+`); content-addressed decision dossiers.
- **HMAC-SHA256 evidence signing** with chain_link in the signed domain, env-injected keys, explicit non-repudiation caveat, asymmetric seam via `EvidenceSigner` protocol — production-grade crypto hygiene for a symmetric design (`evidence_signing.py` module docstring + tests).
- **`GovernedKernel.amendment_authorized` fail-closed**: no version manager / no ratified head / missing ref → `False` (`integration.py:65-77`).
- **Evidence E-1/E-2** enforced at write with tests; **lineage invariants** tested; **escalation policy** six triggers data-driven with 24 tests (AGENTS).
- **Compiler gate** denies unknown backends / uncertified production targets with audit emitter (`compiler/governance/enforcer.py`); wired into `compiler.governance.routes` for that package.
- **Product-factory** real human-approval requirements for fee/ranking/curation/refund thresholds (policy flags default True).
- **Learning package discipline**: `feedback_compiler` “does not mutate the ISR directly”; feedback flows governance-first (AGENTS constraint held on inspection).
- **CI evidence chains** archive ledgers and enforce `verdict: CERTIFIED` + empty failed_gates before calling a release certified.
- **Fail-closed production auth/config** (EV-A04/EV-A08 positives) is the only *actually mounted* control plane on the product API — security boundary works; lifecycle governance does not.

### EV-A09-011 — Escalation and certification governance are real but seat-bound to harnesses
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

Escalation events, infra-storm learn-only side-channel, registry regressions — all tested and coherent **inside** `certification/` + `release/` gates. No path from a live `/evolve` failure or platform incident into these components (no emitter in `autonomous-api`). Separate-plane governance, correctly isolated from auto-evolution (master prompt §13), but therefore also non-responsive for the product’s runtime.

### EV-A09-012 — Control-plane authority summary (cross-cutting)
`[PARTIAL]` · Confidence **INFERRED** (composition of 001–007)

Only enforcement actually live on PR#1 `6e1aa1a` for the shipped API: **admin API-key middleware on `/evolve*` + observation routes**, boot-time production validators, fitness fail-closed on build/runtime failure (EV-A02/A03), production readiness *scoring*. Everything marketed as “constitutional governance,” “only subsystem authorized to advance lifecycle,” “promotion guard,” and “kill switch” is **library-ready, test-covered, and unwired**. That is the same shape of finding as EV-A05 (deploy story without actuation) and EV-A07 (capabilities without servers) — now for the authority model itself.

---

## 7. Verification appendix (evidence log)

- **Probe** `Temp/opencode/ev09` (inline system Python, `sys.path` → `autonomous-api`):
  - `g6_check_condition True` · `g6_when_empty_set SKIPS enforcement (truthy short-circuit on empty set)`
  - `g7_executive_alone_empty_council DENIED G-7 … 0.00 < 1.00` · `g7_exec DENIED GovernanceInvariantError`
  - `governancesubsystem_construction_non_test []`
  - `kernel_in_app NONE` (no `GovernanceKernel`/`EvolutionPromotionGuard`/`PEPEnforcer` under `app/`)
  - `EvidenceSubsystem(` / `LineageSubsystem(` / `GovernanceSubsystem(` → `NOT_CONSTRUCTED_IN_APP`
- **Static reads:** `app/governance/{subsystem,observation_adapter,adapters/memory}.py` (full), `app/core/governance/{invariants,executive,commands,events,ports}.py`, `app/evidence/subsystem.py`, `app/main.py` (full), `kernel.py` (full 240), `evidence_signing.py:1-80`, `approval_workflow.py:1-100`, `audit.py:1-100`, `integration.py` (full), `pep/evolution_guard.py:1-80`, `learning/governance/{safety,api,engine}.py`, `marketplace_plugins/engine.py:1-100`, `compiler/governance/enforcer.py:1-80`, `certification/governance/registry.py:1-80`, `dashboard/auth.py:1-80`, `tests/test_phase28_evidence_signing.py` (head), `adapters/memory.py` (full).
- **Greps:** subsystem/kernel/guard construction sites; `from app.governance` (tests only); `learning.*include_router` (self demos only); `enable_learning_governance` callers (none in product); `CompilerGovernanceEnforcer` consumers (compiler package only); `.gitignore` `release/evidence/`.
- **Not probed:** live dashboard login; real Council registration flow over HTTP (no HTTP surface); non-repudiation with external verifier; concurrent approval races (in-memory single-thread tests cover happy path).

---

## 8. Conclusion & sequence close-out

**FAIL.** Governance is the final gap and it is structural: the workspace can *describe* and *unit-test* authority without *exercising* it on any request the product serves. Must-fix order:

1. **Wire or stop claiming:** composition root must construct evidence/governance/lineage subsystems (Postgres ports, not memory adapters), route read APIs, and put `EvolutionPromotionGuard` (or equivalent) on the promote seam — or strike lifecycle/guard language from product docs/capabilities (EV-A03 style).
2. **Fail closed on defaults:** G-6 must deny when `recognized_certifiers` is empty; wire or delete `Executive.quorumThreshold`; give Executive an explicit G-7 path or remove the role.
3. **Durable audit:** swap `AuditFramework`/`ApprovalWorkflowEngine`/governance event store to file-backed (reuse `FileBackedConstitutionVersionRepository` pattern) or Postgres; stop wiring InMemory version repos where FileBacked exists.
4. **Kill switch on the product:** mount learning-style kill switch (authenticated) or a platform `MAINTENANCE`/`EVOLVE_DISABLED` gate — currently zero runtime brakes beyond process kill (EV-A08).
5. **Signing:** default-on signing in production when a key is present is already there; require the key in `ENVIRONMENT=production` if evidence is a compliance control (align with EV-A05 secret injection).
6. **Registry durability:** promote `cbc1-governance.jsonl` out of pure gitignore regeneration — CI artifact alone is episodic.

### Sequence status

| Gate | Report | Status | Register |
|---|---|---|---|
| EV-A01 | `docs/EV-A01-repo-ci-integrity.md` | (prior) | 001..011 |
| EV-A02 | `docs/EV-A02-artifact-correctness.md` | (prior) | 001..012 |
| EV-A03 | `docs/EV-A03-capability-truthfulness.md` | FAIL | 001..010 |
| EV-A04 | `docs/EV-A04-security-boundary.md` | FAIL | 001..017 |
| EV-A05 | `docs/EV-A05-deployment.md` | FAIL | 001..014 |
| EV-A06 | `docs/EV-A06-observability.md` | FAIL | 001..012 |
| EV-A07 | `docs/EV-A07-schema-observation-integrity.md` | FAIL | 001..012 |
| EV-A08 | `docs/EV-A08-change-safety.md` | FAIL | 001..012 |
| **EV-A09** | **`docs/EV-A09-governance.md`** | **FAIL** | **001..012** |

**Bandit-fix verification track** remains separate (PR #1 head last known `6e1aa1a`; main `1f26e42`).

*(End of EV-A01…EV-A09 sequence. Optional follow-ups: consolidated executive summary across nine reports; collaborator remediation re-audit when PR #1 moves.)*
