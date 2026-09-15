# VS-D36 — Observatory Implementation Slice 01 Definition & Authorization

**Gate:** VS-D36 · **Objective:** VS1-OBJ-001 · **Mode:** ANALYTICAL / AUTHORIZATION-ONLY
**Upstream (file-native names, no relabeling):** D30 inventory/reconciliation
CLOSED · D31 implementation scope CLOSED · D31A UX audit CLOSED · D31B visual
constitution COMPLETE · D32 adjudication CLOSED (65/11/17/15/12) · D33 state
contract CLOSED · D34 command protocol CLOSED · D35 readiness CLOSED
(READY_WITH_BOUNDED_GAPS).
**Baseline:** branch main, HEAD ba952d4, tree stable (1 pre-existing line).
**D36 implements nothing.** It proves the slice, bounds it mechanically, and
grants D37 slice-scoped authority (§17). Target sites spot-verified read-only
2026-09-12 (store.py:200-242; routes.py:145-177; workspaces.ts:121 with zero
UI call-sites; projections_genomes.py:140 fallthrough; console duplicate
Server-Workspaces block verbatim).

## 1. INC-01 scope (§5 — per-target proof, all 7)

| ID | PATH | WHY_THIS_FILE | UPSTREAM_CONTRACT → OBLIGATION | EXPECTED → FORBIDDEN | COMPANION_TEST → VERIFICATION → ROLLBACK |
|---|---|---|---|---|---|
| T1 | tests/observatory/test_backend_adapter_contract.py (NEW) | only unbound drift risk (DUP-001/GAP-005) has no test home; DEC-001 names backend record, adapter conformer | D31 DEC-001 + D35 N-01 → assertions DERIVED from both vocabularies (field diff = test-writing step 1; DEBT-01 input) | vocab/marker/identity/timestamp parity tests → NO production edits, NO shared package, NO invented version scheme | file itself → D37 runs green + mutation testing of mirror (change one side → red) → delete file |
| T2 | observatory/backend/store.py AND api/routes.py (narrow) | ValueError escapes _normalize_timestamp (store.py:200, called :239/:242) through gateway to 500 | D31 C-06/C-11 + D35 N-02 → invalid since/until yields 400 + reason | typed error + 400 mapping (location = IMPLEMENTATION_CHOICE, identical observable) → NO semantic change to search, NO new failure states | extend test_store_batch/test_api search cases → 400+reason asserted; 500-path test removed/updated → revert hunk |
| T3 | observatory/frontend/lib/workspaces.ts (read) + app/workspaces/page.tsx (wire) | audit() exists (:121), zero call-sites (verified) | D31 C-02/GAP-004 + D35 N-03 → hook existing client into existing view | audit section rendering via existing proxy → NO new endpoints, NO auth changes, NO audit-client redesign | extend test_frontend_boundary surface assertions → call-site asserted statically → revert hunk |
| T4 | observatory/backend/projections_genomes.py (2–3 lines) | `return "observed"` fallthrough (:140) contradicts sibling unknown-defaults (F-003) | D31 C-05/F-003 + D35 N-04 + D31B gray direction → absence yields `unknown` | default-string change only → NO logic restructure, NO other projection touched | sibling-consistency tests across 6 projection modules + negative unknown cases → revert hunk |
| T5 | tests/observatory/*.py companions (extend, none new exc. T1) | D31 §24 enumerates negative cases per touched path | D35 N-05 → unknown/missing/not_measured/contradicted/unavailable/invalid/unauthorized/forbidden/unverified per T2–T4 paths | assertions only → NO production code in test files beyond fixtures | themselves → suite green → revert hunk |
| T6 | docs/observatory/INC01_DEPLOYMENT_CONSTRAINTS_D37.md (NEW, D37-written) | B-001/B-002/B-003 must be recorded where implementers look | D31 §20 item 6 + D35 N-06 → proxy-only assumption, token effect, UI-filtering non-boundary | prose record of extant posture → NO posture change, NO new mechanism | reviewable diff (prose) → content matches D35 §11 → delete file |
| T7 | observatory/frontend/app/console/page.tsx (duplicate block ONLY) | two identical Server-Workspaces Sections (verified verbatim) | PD-02 amendment (D32-recorded) + D35 N-07 → remove SECOND block, keep first | deletion of duplicated JSX block → NO other console change, NO behavior change (both render same panel) | boundary assertion (single occurrence) → count==1 → revert hunk |

MUST_DEFINE verification (§11): all seven WHY/EXACT/FORBIDDEN/TEST/ROLLBACK
answered above with zero new architectural decisions → MUST_DEFINE stays EMPTY
(re-verified, not repeated). Any target failing proof would be EXCLUDED (none failed).

## 2. Allowlist, forbidden, frozen (§7)

```text
AUTHORIZED TO ADD: tests/.../test_backend_adapter_contract.py;
  docs/observatory/INC01_DEPLOYMENT_CONSTRAINTS_D37.md (T6, D37-written)
AUTHORIZED TO MODIFY (narrow purpose-bindings §1): store.py (T2 mapping);
  api/routes.py (T2 mapping); workspaces page.tsx (T3 wiring);
  projections_genomes.py (T4 default); console/page.tsx (T7 duplicate block ONLY)
AUTHORIZED TO TEST: tests/observatory/*.py (extend for T1–T5)
AUTHORIZED TO DOCUMENT: T6 file only
FORBIDDEN TO MODIFY: everything else, explicitly including domain.py semantics,
  governance engines, bus, config, adapters prod code, all core packages,
  generated/**, vertical_slice/**, evidence/**, release/**, EXT dirs, .env*,
  lockfiles, CI, disclaimer texts, D31B-cited UI copy outside T3/T7
FROZEN PATHS (byte-stability §3): D30–D35 artifacts (7 MD + 4 JSON);
  domain.py; governance.py; workspace_governance*.py; bus.py; config.py;
  adapters/** prod; console/page.tsx EXCEPT T7 hunk (hunk-scoped stability)
```

Slice CANNOT touch: ISR semantics, constitutional authority, Evolution Engine,
frozen contracts, certification/deployment authorities, unrelated subsystems,
out-of-INC-01 security boundaries, production state (no mechanism exists in
scope to reach any of them; allowlist permits no path).

## 3. Frozen-path byte-stability + reversion test (§§8/21, mechanical, D38-inherited)

Predicate (all three mandatory; any failure → INC-01 verification FAIL):
```text
P1: git diff --name-only ∩ (ALLOWLIST_COMPLEMENT) = ∅
    i.e. every changed/added path ∈ §2 ADD/MODIFY/TEST/DOCUMENT sets
P2: frozen paths byte-identical (git diff --quiet -- <frozen-set>;
    T7 exception: console/page.tsx diff MUST equal exactly the duplicate-block
    deletion hunk, verified by `git diff -U0` shape: one contiguous removal)
P3: full applicable suite green on canonical profile (python -m pytest)
```
Human inspection supplements; never substitutes. Reversion = `git checkout --`
allowlisted hunks / delete added files (each target's ROLLBACK column §1).

## 4. No-silent-promotion proof (§9) + gaps (§10)

| D35 item | Class | INC-01 exposure | Permitted → Forbidden → Future owner → Verification |
|---|---|---|---|
| idempotency keys | CURRENT_GAP | NONE (no side-effect impl) | record gap → invent keys/assume semantics → future command gate → P1 (no such code) |
| schema binding | CURRENT_GAP | T1 pins behavior WITHOUT versioning | assert parity → invent version scheme → AQ-009 gate → T1 contains no version field |
| bound confirmation | CURRENT_GAP | NONE (no command UI impl) | preserve gap → build confirmation → future control gate → P1 |
| version-pinned authority | CURRENT_GAP | NONE | preserve → assume versions → future gate → P1 |
| mutation executor | CURRENT_GAP (fail-closed) | NONE (T3/T7 are reads/display) | preserve fail-closed → wire executor → future gate → P1 + fail-closed tests |
| UNKNOWNs (deployment/Council/CEL/PII/rendering) | UNKNOWN | NONE encountered | carry → assume/silence → respective gates → P1 + negative tests |
| R25/R26 PROPOSED | PROPOSED | NONE | labeled → contracted → future gates → P1 |
| N-27/N-28 future-only | FUTURE_GATE | NONE in INC-01 | owned downstream → absorbed now → future gates → P1 |

Forbidden transformations (all six) prevented POSITIVELY: P1 makes absorption
structurally impossible (no path outside allowlist exists to carry it); T5
negative tests assert gap-preserving behavior; P2 freezes the contracts that
would otherwise be "fixed" opportunistically.

## 5. Requirements reconciliation (§12 — count reconciles with D35: 7)

D35 N-01..N-07 ↔ T1..T7 one-to-one (N-01→T1, N-02→T2, N-03→T3, N-04→T4,
N-05→T5, N-06→T6, N-07→T7). Each: target §1, contract source cited, obligation
stated, test named, evidence = P1–P3 predicates. Zero additional requirements;
zero DERIVED_REQUIREMENT items needed (no mechanical derivation arose).

## 6. Security / command / state / human / failure / versioning / observability (§§13–19)

- SECURITY: INC-01 acquires/exposes no secrets (no secret-bearing paths in
scope); broadens no authority (role/clearance code untouched); UNKNOWN-auth
stays denied (untouched paths); submission≠execution preserved (no command
paths); confirmation/audit reqs untouched (gaps preserved); no deployment
authority created; no authoritative mutation (only workspace DISPLAY wiring +
local test/audit records). D34 fail-closed laws binding; S01–S15 unaffected
(no security mechanism altered).
- COMMAND: INC-01 handles READS + local display wiring only (observation class);
no submission/authorization/execution/result paths touched; distinctions
submission≠execution, timeout≠nonexecution, UNKNOWN≠success, DENIED≠PENDING
vacuously preserved (nothing in scope can violate them — verified by P1).
- STATE/IDENTITY/PROVENANCE: consumes D33 taxonomy/identity/6-link chain; T4
changes a VALUE (`observed`→`unknown`), never the model; recomputed-vs-
authoritative distinction untouched; frozen/adjudicated separation untouched;
no second source of truth creatable within allowlist.
- HUMAN: no view→authority, request→execution, display→certification
transformation in scope; D34 confirmation gap preserved, not repaired.
- FAILURE: T2 maps one 500-path to contracted 400 (existing state, not new);
all other modes use frozen states; no new semantic failure invented.
- VERSIONING: four required-now obligations untouched; state_version not
promoted; protocol-vs-availability distinction preserved (T1).
- OBSERVABILITY (D37 evidence): implementation diff (P1) + frozen verification
(P2) + suite result (P3) + per-target test identities (T1–T5) + constraint doc
(T6) + boundary assertion (T7). Layer attribution exact; UI-presence≠capability
holds (T3 asserts call-site, not capability).

## 7. Test plan (§20) + anti-accident register (§22, condensed)

TESTS: A scope (P1) · B frozen (P2) · C consumption (T1 parity incl. DEBT-01
field diff; T3 call-site; T4 sibling-consistency) · D behavior (400+reason;
audit render; unknown badge; single panel) · E negative (D31 §24 list per path;
forbidden-change assertions) · F fail-closed (auth-config on/off pinning where
touched; no-permissive-drift) · G full suite canonical · H invariants (22 + D34
laws regression via existing suites staying green).
ANTI-ACCIDENT (IF X → WHERE DECIDED / OWNER / WHY OUT): state semantics→D33 §3
· identity→D33 §4+R6 · authority→D31 §6/D33 §2 · authZ→D34 §8 · lifecycle→D34
§10 (+N-27 future) · mutation→fail-closed law (no executor) · provenance→D33 §4
· security→D34 S-matrix · versioning→D33 §7/D34 §28 (state_version future) ·
transport/storage/framework→OUT (firewall) · deployment→UNKNOWN/fail-closed ·
secrets→ban+N-28 future · UI semantics→D31B §§4-6/9/15 · future execution→N-27
gate · PENDING→N-27 gate (do NOT invent exit edge if encountered).

## 8. P-005 / debts / contradictions / invariants / traceability (§§23–27)

P-005 UNRESOLVED; no INC-01 target depends on it (dependency scan: 0 hits) —
preserved, implementation impact NONE. DEBT-01 consumed (T1 input) REMAINS
OPEN until tests exist · DEBT-02 = P-005 rule · DEBT-03/04/05/06 carried, no
INC-01 exposure. C-001/C-002 preserved; INC-01 introduces no contradiction
(P1-bounded diff cannot contradict frozen contracts; verified at D38 by P2).
Invariants: 22/22 + D34 laws + D35 readiness laws applicable-and-held (no law
exercised beyond reading, except T4's value change which I05-classifies as
preserved-unknown — the law's INTENT). Traceability: D35 N-01..N-34 terminate —
7→targets, 12 (contracts/invariants/tallies/P-005/debts/C-register)→D37
verification + frozen preservation, 9 (deferred AQs/PROPOSED/convergence/
freshness/persistence/transport)→future owners with reason, 6
(out-of-scope tech/production/certification)→excluded with reason. Orphans: 0.
Absorbed: 0. Ambiguity in THIS artifact: normative SHOULD/MAY uses re-scanned —
0 material ( prohibitions + bounded permissions only).

## 9. Authority decision (§28) + D37 grant (§29)

```text
STATUS: AUTHORIZED_WITH_BOUNDS
BOUNDS (explicit, proven irrelevant to INC-01):
  B1 N-27 PENDING-exit | DERIVED_REQUIREMENT | irrelevant: no command paths in
     allowlist (P1-enforced) | future owner: command-execution gate |
     verification: P1 + §6 command-vacuity proof
  B2 N-28 secure-reference | DERIVED_REQUIREMENT | irrelevant: no secret-bearing
     paths in scope (P1-enforced) | future owner: secret-capable-command gate |
     verification: P1 + secret-ban tests untouched-green
  B3 deployment-UNKNOWN | UNKNOWN | irrelevant: no deploy paths (none exist in
     scope) | future owner: deploy gate | verification: P1
D37 IMPLEMENTATION AUTHORITY: GRANTED — strictly limited to §2 allowlist +
  §1 requirements + §7 tests + §6 evidence. NOT authority for: redesign, ISR/
  authority/constitutional change, production deployment, new executors,
  new certification/deployment authorities, P-005, future-gate questions.
  D37 IMPLEMENTATION IS AUTHORIZED ONLY WITHIN THE D36 INC-01 BOUNDARY.
```

## 10. Accounting (§33) + STOP (§34)

```text
HEAD ba952d4 (before/after identical) · tree: 1 pre-existing line ·
porcelain delta from D36: +3 analytical artifacts, 0 source changes ·
source=0 runtime=0 execution=0 deployment=0 authority=0 ISR=0 commits=0 pushes=0
```

## VS-D36 STOP REPORT

```text
STATUS: AUTHORIZED_WITH_BOUNDS
UPSTREAM: D30/D31/D31A/D31B/D32/D33/D34/D35 all consumed frozen (labels per §2)
INC-01_SCOPE: 7 targets (T1 new test; T2 400-mapping; T3 audit wiring; T4 F-003;
  T5 negative companions; T6 constraint doc; T7 duplicate removal)
TARGET_COUNT: 7 (proof-complete 7/7; exclusions 0)
TARGET_PROOF: §1 table (13 fields × 7; MUST_DEFINE re-verified EMPTY)
ALLOWLIST: §2 ADD(2)/MODIFY(6 files, purpose-bound)/TEST/T6-DOCUMENT
FORBIDDEN_PATHS: §2 (domain semantics, engines, bus/config, adapters prod,
  core pkgs, generated, vertical_slice, evidence, release, EXT, env, locks, CI,
  disclaimers, non-T3/T7 UI copy)
FROZEN_PATHS: §2 (7 MD + 4 JSON contracts; semantic cores; T7 hunk-scoped)
CONTRACT_CONSUMPTION: §1 per-target chains (§6 audit: 13 contract families)
NO_SILENT_PROMOTION: §4 matrix (positive prevention via P1 + frozen P2 + T5)
D35_CURRENT_GAPS: 5 carried, exposure NONE, fail-closed preserved
MUST_DEFINE_BEFORE_IMPLEMENTATION: EMPTY (re-verified)
IMPLEMENTATION_REQUIREMENTS: 7/7 reconciled with D35 (N-01..N-07)
SECURITY: §6 (no secret/authority/audit surface altered; S-matrix unaffected)
COMMAND_CONTROL: §6 (reads/display only; distinctions vacuously preserved)
STATE_IDENTITY_PROVENANCE: §6 (consume-only; T4 value-only; no second truth)
HUMAN_CONTROL: §6 (no transformations; confirmation gap preserved)
FAILURE_RECOVERY: §6 (T2 contracted mapping; no new states)
VERSIONING: §6 (required-now untouched; nothing promoted)
OBSERVABILITY: §6 (diff + frozen + suite + test identities)
TEST_PLAN: §7 A–H
REVERSION_TEST: P1+P2+P3 (§3; D38-inherited, non-judgment)
ANTI_ACCIDENT_REGISTER: §7 (16 entries + N-27 rule)
P-005: UNRESOLVED, dependency-free, preserved
KNOWLEDGE_DEBT: 01 consumed-as-input (open till tests exist); 02–06 carried
CONTRADICTIONS: C-001/C-002 preserved; new 0; unresolved 0
INVARIANTS: 22/22 + D34/D35 laws held; failed 0
TRACEABILITY: 34/34 terminated; orphans 0; absorbed 0
AMBIGUITY: 0 material
D37_AUTHORITY: GRANTED (bounded §9)
IMPLEMENTATION: all-zero (§10)
ARTIFACTS:
  docs/observatory/OBSERVATORY_IMPLEMENTATION_SLICE_D36.md
  docs/observatory/OBSERVATORY_IMPLEMENTATION_SLICE_D36.json
  docs/observatory/OBSERVATORY_IMPLEMENTATION_AUTHORIZATION_D36.json
COMMITS: 0
PUSHES: 0
FINAL: AUTHORIZED_WITH_BOUNDS — D37 IMPLEMENTATION IS AUTHORIZED ONLY WITHIN
  THE D36 INC-01 BOUNDARY.
```
