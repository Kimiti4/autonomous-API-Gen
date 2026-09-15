# VS-D33 — Observatory State Model / Implementation Contract Definition

**Gate:** VS-D33 · **Objective:** VS1-OBJ-001 · **Mode:** ANALYTICAL + CONTRACT-DEFINITION ONLY
**Upstream (corrected labels — boundary note, history untouched):**
D30 = inventory/reconciliation execution · D31 = implementation scope ·
D31A = UX audit · D31B = visual constitution · D32 = evidence-consistency
adjudication (PASS_WITH_BOUNDS, authoritative baseline).
**Baseline:** branch main, HEAD ba952d4, tree stable (1 pre-existing line).
**Convention ruling (§36):** repo convention is Markdown artifacts + JSON
evidence; no YAML register structure is introduced. Primary contract = this
file; machine companion = `OBSERVATORY_CONTRACT_D33.json` (justified: the
`vertical_slice/*_evidence.json` machine-readable convention).

## 0. Supersession rule (binding)

```text
D30 historical aggregate:   63 / 11 / 23 / 14 / 9  (frozen, never overwritten)
D32 adjudicated aggregate:  65 / 11 / 17 / 15 / 12 (authoritative citation)
```

This artifact cites ONLY the D32 figures. Historical and adjudicated truth stay
separate provenance states. P-005 REMAINS UNRESOLVED (constitutional track).

## 1. Responsibility model (§6)

| ID | PURPOSE | INPUT_AUTHORITY | OUTPUT | RO | MUT | AUTH | EVIDENCE | FAILURE |
|---|---|---|---|---|---|---|---|---|
| R-STATE | inspect system/runtime/governance state | owning services | state views | YES | NO | none (reads header-trust per B-001) | projections | explicit error/unknown |
| R-EVIDENCE | inspect evidence records/bundles | per-system ledgers | evidence views | YES | NO | none | bundle/ledger refs | missing→labeled |
| R-PROVENANCE | trace claims to sources | carried dicts + chains | audit views | YES | NO | none | hash/event refs; unverified labeled | broken→bounded state |
| R-CAPABILITY | inspect capability posture | implementation code | capability views | YES | NO | none | impl + verification refs | visible≠implemented enforced |
| R-CONTRADICTION | surface claim conflicts | paired sources | contradiction views | YES | NO | none | both sources + authority | never hidden |
| R-AUTHORITY | display who may do what | kernel + boundary | authority views | YES | NO | none | kernel/boundary refs | ambiguous stays ambiguous |
| R-HEALTH | inspect liveness signals | endpoints/bus/counters | health views | YES | NO | none | per-signal source | process-alive≠healthy |
| R-CONTROL-REQ | submit governed requests | operator session | audit event (executes nothing) | NO | OBS-LOCAL* | token+clearance+policy | audit trail | fail-closed, rejection visible |
| R-AUDIT | inspect command/role/snapshot history | audit chains/bundles | audit views | YES | NO | none | chain hashes | gap→labeled |

*OBS-LOCAL: R-CONTROL-REQ mutates ONLY observatory-local request/governance
records (command_requested events, workspace roles/snapshots). It NEVER mutates
authoritative systems. No AUTHORIZED_MUTATION over authoritative state exists.

## 2. Source-of-truth boundary (§7)

| DATUM | AUTHORITATIVE SOURCE | DERIVED? |
|---|---|---|
| requirements / ISR | ISR chain via D30A (MEDIUM) | NO |
| capabilities | per-package implementation (LOW) | NO |
| evolution posture | evolution/ engine + promotion audit | NO |
| authorization/governance posture | constitutional kernel; display boundary (OBS-PY-BE) | display projection DERIVED (rule + source fields identified) |
| runtime/health | owning services | derived status DERIVED (derivation = stated projection fn) |
| evidence/provenance | per-system ledgers | audit views DERIVED (recomputed chains labeled ordering-only) |
| configuration effect | env vars consumed at runtime | influence only; constitutional authority UNKNOWN |
| commands | operator intent + boundary decision | audit record DERIVED (request + decision + refs) |
| matrix tallies | D32 recomputation | adjudicated value DERIVED (method stated) |

Nothing the Observatory displays without an entry above exists. Gaps render as
§4 states, never as values.

## 3. State taxonomy (§8) — two axes, upstream preserved

AXIS 1 — EVIDENCE MODE (from backend EpistemicStatus, preserved verbatim):
`observed · inferred · unverified` (+ `unknown` shared with Axis 2).
AXIS 2 — STATE (canonical ten, non-collapsible):
`CERTIFIED · QUALIFIED · PARTIAL · PENDING · BLOCKED · UNKNOWN · UNRESOLVED ·
CONTRADICTED · STALE · NOT_APPLICABLE`.
Projection vocabulary (`not_measured · missing · recorded`) maps INTO Axis 2
(not_measured→UNKNOWN with reason; missing→UNKNOWN/PARTIAL per context;
recorded→PENDING-or-stated) — mapped, never renamed at source.
Non-collapse law: UNKNOWN≠FAILED · PENDING≠BLOCKED · PARTIAL≠CERTIFIED ·
UNRESOLVED≠CONTRADICTED · STALE≠INVALID · inferred≠observed · stale≠current.

## 4. Evidence / claim / provenance / identity models (§9–§12)

EVIDENCE OBJECT (minimum): evidence_id · subject_id · source ·
source_location · evidence_type · authority · timestamp_or_version ·
content_hash · scope · classification · provenance · limitations.
Layers kept distinct: evidence ≠ claim ≠ interpretation ≠ decision (separate
objects, linked by refs, never merged).
CLAIM OBJECT: claim_id · claim · subject · evidence_refs · classification
(ESTABLISHED/BOUNDED/INFERRED/HYPOTHESIZED/UNRESOLVED per D32 usage) · scope ·
confidence_basis · contradiction_refs · provenance · status. Evidenceless
claims stay non-authoritative; UI interaction never upgrades classification.
PROVENANCE CHAIN (required shape): representation → derived field → source
record → source artifact → identity/hash → authority. Broken links render as
bounded states (P-001/P-002 carried). Recomputed chains labeled ordering
evidence, never immutable ledgers.
IDENTITY (canonical, display-independent): entity_id · display_name · version ·
content_hash · parent_id · authority · lifecycle_state. Equivalence requires
authoritative evidence — never filename/label/route/similarity inference (R6
carried forward as contract law).

## 5. Contradiction / P-005 / debt models (§13–§15)

CONTRADICTION OBJECT: contradiction_id · subject_id · claim_a/b · source_a/b ·
conflict_type · authority · resolution_status (RESOLVED/BOUNDED/UNRESOLVED) ·
resolution_evidence · remaining_uncertainty. Unresolved stays operator-visible.
Carry-forward: C-001 RESOLVED_BY_EVIDENCE (tallies corrected); C-002
RECONCILED_BUT_BOUNDED (290/291). Zero unresolved contradictions inherited.
P-005 CONTRACT: `{ p005: { status: UNRESOLVED, authority: constitutional-track,
substance_pointer: [folder/D29.md:444, D32 PD-03], substance: NOT_RECORDED } }`.
D33 PASS_WITH_BOUNDS MUST NOT be rendered as P-005 progress. Any view showing
ISR identity MUST be capable of showing the P-005 qualifier.
DEBT OBJECTS (all six LOW, blocking=false unless noted):
DEBT-01 DUP-001 magnitude (needs field diff; acceptance input for contract-test
gate) · DEBT-02 P-005 substance (constitutional track; blocking for NOTHING
here, blocking for ISR-authority claims) · DEBT-03 count exactness
(re-execution unwarranted) · DEBT-04 rendering inferences (need a browser;
OOS for repo gates) · DEBT-05 .env contents (deliberately unexamined) ·
DEBT-06 core interiors below 2 levels (declared breadth limit). LOW means
bounded/non-critical in adjudicated scope — never visually irrelevant (§15).

## 6. Capability / control / HITL / firewall (§16–§19)

CAPABILITY OBJECT: capability_id · name · status · authority · evidence_refs ·
implementation_ref · verification_ref · limitations · dependencies. Enforced
chain: visible≠implemented ≠verified ≠certified ≠production-authorized — each
transition requires its own evidence; UI presence proves nothing.
CONTROLS: READ_ONLY (all reads, stream, search, export, audit views) ·
REQUEST (command submit, workspace save, role grant/revoke — observatory-local
effects only, audit-required) · AUTHORIZED_MUTATION over authoritative state:
NONE EXISTS · FORBIDDEN (production execution, consolidation, authority
redefinition, silent repair, certifying presentation).
HITL CHAIN (never collapsed): human_request → system_validation →
authorization → execution → result → audit. Click ≠ authorization; the
authoritative subsystem decides; the Observatory renders the decision.
FIREWALL: READ inspects state/evidence/provenance/capabilities/metrics/logs/
lineage/health/decisions. MUTATE requires explicit upstream authority, which no
current gate grants over authoritative systems. Controls do not confer
authority by existing.

## 7. API / UI / metrics / temporal / failure / security / observability (§20–§26)

API CONTRACT (technology-neutral): every operation declares operation_id ·
purpose · input/output schemas · authority · authorization · side_effects ·
evidence_requirements · failure_modes · audit_requirements. Framework choices
are implementation-layer, never constitutional.
UI CONTRACT (semantic): may display/filter/navigate/inspect/compare/trace/
request/confirm. MUST NOT decide/authorize/certify/reconcile/rewrite/repair.
A visualization is never an authority (D31B §§8–9, 15 binding here by reference).
DERIVED METRICS: metric_id · inputs · formula · aggregation · scope · version ·
source · limitations. The D32 aggregate (65/11/17/15/12) is consumed as an
adjudicated value with lineage (D32 §B recomputation); per-component
recomputation requires a canonical derivation rule (none established — any view
recomputing MUST cite D32 method or declare PROPOSED).
TEMPORAL: observed_at / recorded_at / effective_at / version distinguished;
absent timestamps NEVER invented (F-001 law extends: missing time renders as
missing time); history distinguishable from current.
FAILURE (observable, explicit): missing/stale evidence · broken provenance ·
unknown identity · unresolved contradiction · unauthorized action · invalid
input · upstream unavailable · inconsistent state. Substitutions (empty/zero/
false/healthy/unknown) FORBIDDEN unless the contract defines the transform —
none defined. Fail-closed throughout.
SECURITY: authentication · authorization · roles · least privilege · secret
isolation (no passwords/tokens/credentials/private secrets in ANY evidence
representation — GAP-006/P-006 carried as constraint on future ingest/display
work) · auditability · fail-closed. Unknowns stay UNKNOWN/NOT_CERTIFIED;
certification remains NONE.
OBSERVABILITY CONSUMED: health · availability · latency · errors · resources ·
workflow · lineage · recent events. Preserved inequalities: health≠correctness
≠certification≠authorization. Observatory self-health never inferred from
process aliveness (D31 §25 binding here).

## 8. Registers A–J (§28, condensed; machine companion carries full rows)

A. STATE MODEL: §3 axes + transition rule (transitions require evidence events;
no silent reclassification; promotion invariant D30-origin carried).
B. AUTHORITY MATRIX: §2 table (9 datum rows) + R- model §1.
C. EVIDENCE CONTRACT: §4 evidence object + layer separation + secret-isolation.
D. CLAIM CONTRACT: §4 claim object + D32 classification usage + no UI upgrade.
E. IDENTITY CONTRACT: §4 identity object + R6 inference ban.
F. CONTRADICTION REGISTER: object §5 + C-001/C-002 carry-forward + zero
inherited-unresolved statement.
G. DEBT REGISTER: 6 LOW objects §5.
H. CONTROL CONTRACT: §6 classes + firewall + HITL chain.
I. FAILURE CONTRACT: §7 failure classes + substitution ban + fail-closed.
J. HANDOFF CONTRACT: future implementation MUST satisfy — D32 figures cited;
P-005 qualifier renderable; debt visible; invariants I01–I22 held; allowlist
discipline (D31 §21 + PD-02 amendment) inherited; negative-case verification
(D31 §24) inherited; D31B §§4–6/9/15 binding on any UI touch.

## 9. Invariants, traceability, classification (§29–§31)

I01–I22 ADOPTED VERBATIM from the gate (I08 cites 65/11/17/15/12; I09 P-005;
I07 frozen history; I21 technology-free semantics). Each maps: invariant →
D32 finding → D31/D30 evidence → authoritative source (companion JSON §trace).
REQUIRED_BY_EVIDENCE: models §§1–7 as bounded above. REQUIRED_BY_AUTHORITY:
I07/I08/I09/I15–I17 (gate + constitutional order). DERIVED_FROM_EVIDENCE:
taxonomy mappings, control classes, debt objects. PROPOSED_FOR_IMPLEMENTATION:
nothing — D33 proposes zero implementation items (all_OPTION-like content from
D30 OPT-001..007 REMAINS unselected; carried as unselected). OUT_OF_SCOPE:
technologies (§27 list), production execution, certification.

## 10. Completeness + no-implementation tests (§32–§34, self-executed)

D32 material mapped: 20/20 claims · 2/2 contradictions · 5/5 defects ·
6/6 debts · tallies · P-005 · invariants · authority/firewall/control/failure
classes — NOTHING UNMAPPED (else BLOCKED; not triggered). T01–T24 VERIFIED:
T01 D32 identity ba952d4 resolves ✓ · T02 verdict PASS_WITH_BOUNDS ✓ ·
T03 aggregate 65/11/17/15/12 ✓ · T04 D30 frozen values distinguishable (§0) ✓ ·
T05 P-005 UNRESOLVED ✓ · T06 six LOW represented (§5) ✓ · T07 mapping §10 ✓ ·
T08 every state has authority (§§1–2) ✓ · T09/T10 evidence/provenance
requirements (§4) ✓ · T11 identity rule (§4) ✓ · T12/T13 contradiction/
uncertainty representable (§5) ✓ · T14 metric lineage (§7) ✓ · T15/T16/T17
control/authority/fail-closed (§6) ✓ · T18 UI≠authority (§7) ✓ · T19 no tech in
contract (§7 + §27 list honored) ✓ · T20 history immutable (§0) ✓ · T21
supersession preserved (§0) ✓ · T22/T23/T24 no implementation/commits/pushes
(verified §11) ✓.

## 11. Mutation proof + STOP

```text
implementation files changed = 0 · source modified = 0 · deployment = 0 ·
commit = 0 · push = 0 · runtime mutation = 0
artifacts: OBSERVATORY_STATE_MODEL_D33.md (this file) + OBSERVATORY_CONTRACT_D33.json
```

## D33 STOP REPORT

```text
STATUS: PASS
UPSTREAM:
  D30: PASS/CLOSED (frozen; historical tallies retained)
  D31: PASS/CLOSED (scope + allowlist + PD-02 context)
  D31A: ACCEPTED/CLOSED (honesty baseline)
  D31B: COMPLETE (presentation law, binding by reference)
  D32: PASS_WITH_BOUNDS (authoritative adjudication baseline)
D32_BASELINE:
  verdict: CONSISTENT_WITH_BOUNDS
  corrected_aggregate: 65 / 11 / 17 / 15 / 12
  P-005: UNRESOLVED (constitutional track; qualifier renderable, substance not recorded)
  low_knowledge_debt: 6/6 represented as DEBT-01..06
STATE_MODEL:
  states: Axis1 observed/inferred/unverified (+unknown) × Axis2 ten canonical (non-collapsible)
  transitions: evidence-event-gated; promotion invariant carried
  authority_mapping: §2 (9 datum rows; config=influence-only)
EVIDENCE_MODEL:
  evidence_objects: 12-field minimum (§4)
  claim_objects: D32-classified, no UI upgrade
  provenance: 6-link chain; broken links render bounded; recomputed labeled ordering-only
IDENTITY:
  canonical_identity: 7-field, display-independent; equivalence needs authority
  lineage: parent/version/hash required shape
  historical_state_preservation: frozen + adjudicated kept separate (§0)
CONTRADICTIONS:
  represented: C-001 (resolved), C-002 (bounded), object model for future
  unresolved: 0 inherited
  bounded: 1 inherited (C-002)
CONTROLS:
  read_only: all inspection surfaces
  request: command/workspace/role intents (observatory-local effects, audited)
  authorized_mutation: NONE over authoritative state
  forbidden: production/consolidation/authority-redefinition/silent-repair/certifying-UI
SECURITY:
  authentication: token/session bounds preserved
  authorization: roles/clearance/policy bounds preserved
  secret_isolation: ban in representations (GAP-006 constraint carried)
  fail_closed: throughout; unknowns stay UNKNOWN/NOT_CERTIFIED; certification NONE
TRACEABILITY:
  D32_FINDINGS_MAPPED: 20 claims + 2 contradictions + 5 defects + 6 debts + tallies + P-005 (100%)
  D32_FINDINGS_UNMAPPED: none
COMPLETENESS:
  material_findings: all represented
  represented: 100%
  missing: none (BLOCKED not triggered)
IMPLEMENTATION:
  source_changes=0
  implementation=NOT_STARTED
  deployment=0
  runtime_mutation=0
COMMITS: 0
PUSHES: 0
ARTIFACTS:
  docs/observatory/OBSERVATORY_STATE_MODEL_D33.md
  docs/observatory/OBSERVATORY_CONTRACT_D33.json
FINAL: PASS
```
