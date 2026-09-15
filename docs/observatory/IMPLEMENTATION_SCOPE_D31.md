# VS-D31 — Observatory Implementation Scope Definition

**Gate:** VS-D31 · **Objective:** VS1-OBJ-001
**Mode:** ANALYTICAL / SCOPE-DEFINITION / NON-IMPLEMENTING
**Upstream:** VS-D30 STOP REPORT, STATUS: PASS (D30A = VS-D29 PASS/HOLD alias)

This document is a contract for implementation. It is not an implementation.

---

## 1. Gate identity

D31 converts the accepted D30 inventory into a bounded, auditable implementation
scope. It makes only the architectural selections listed in section 30, each
evidence-backed and reversible. Everything else remains explicitly unresolved.

## 2. Upstream evidence

```text
VS-D30 STOP REPORT — STATUS: PASS
HEAD: ba952d4
D30 ARTIFACT: docs/observatory/INVENTORY_RECONCILIATION.md (666 lines, 20 sections)
  16 surfaces · 30-entry evidence ledger · 4 duplication candidates ·
  7 gaps · 10 architectural questions · 7 options, 0 selected
```

D30 findings are carried forward in section 6 of the D31 prompt without
alteration. Where D30 recorded UNKNOWN, D31 preserves UNKNOWN unless section 30
of this document explicitly selects otherwise. Historical Elixir/Phoenix/OTP/ETS
material was verified absent from first-party code (D30 E-006) and is used only
as rejected-assumption records (section 29).

## 3. Baseline

```text
branch: main
HEAD: ba952d4 (vs1: D18 runtime interpretation, D19 evolution decision, D20 post-decision closure)
working-tree: M evidence/factory.jsonl (1 insertion; pre-existing, untouched)
D31 tracked implementation modifications: 0 (this artifact is the sole creation)
```

## 4. Architectural principles

```text
P1  Observatory is projection + observation + explanation + governed control surface.
P2  ISR remains constitutional. Evidence remains authoritative. Unknown remains unknown.
P3  No second source of truth: display, read, and derived surfaces never originate authority.
P4  Configuration influences; it never constitutes. (configuration influence = PRESENT
    implies nothing about constitutional authority.)
P5  Contracts are technology-neutral until repository evidence binds a technology.
P6  Preserve working behavior unless evidence demonstrates material defect.
P7  Uncertainty is represented, never invented away. (unknown -> false/zero/healthy
    is forbidden in all implementation scope.)
P8  Security and epistemic correctness must survive a hostile or bypassing client.
P9  Smallest sufficient increment; adapters over infrastructure; tests over scaffolding.
```

## 5. Current Observatory boundary

```text
IN SCOPE (may be adapted per allowlist, section 21):
  OBS-PY-BE  observatory/backend/        observation, store, projections, API, commands
  OBS-PY-FE  observatory/frontend/       presentation + proxied control only
  OBS-ADAPTER observatory/adapters/tiannara/  observe-only bridge (conforms, never commands)

ADJACENT (read/investigate; modify only via explicit later decision):
  CORE-CERT  certification/              observability infrastructure, candidate evidence input
  CORE-EVO   evolution/                  candidate source (bus + observability API present, unwired)
  CORE-LEARN learning/                   candidate source (telemetry + observability present, unwired)
  CORE-CONST constitutional_architecture/ constitutional authority (never an implementation target)

OUT OF SCOPE (frozen; section 22):
  OBS-EX (design history) · CORE-COMPILER/KNOWLEDGE/CIV/PF internals ·
  EXT-API, EXT-DASH · generated/** · vertical_slice/** · evidence/** · release/**
```

## 6. Source authority model

| Domain | Authoritative source | Read surface | Derived surface | Display surface | Confidence |
|---|---|---|---|---|---|
| requirements | ISR (D30A-accepted chain) | owning services | observatory projections | OBS-PY-FE | MEDIUM |
| ISR | D28-recorded hash (definition use) | vertical_slice records | none in observatory | OBS-PY-FE | MEDIUM |
| capabilities | implementation code per package | package APIs | none centralized | OBS-PY-FE | LOW |
| evolution | evolution/ engine + promotion audit | /v1/evolution/* | observatory evolution view | OBS-PY-FE | MEDIUM |
| authorization | constitutional kernel (real); display boundary (OBS-PY-BE) | kernel; deps/governor | authorization_state projection | OBS-PY-FE | MEDIUM |
| governance | CORE-CONST kernel; GovernanceBoundary (display only) | kernel; gateway | governance_state projection | OBS-PY-FE | MEDIUM |
| runtime state | owning services | /health/live per service | runtime_health projection | OBS-PY-FE | LOW (aggregate) |
| evidence | per-system ledgers | SQLite/JSONL/bundles | overviews | OBS-PY-FE | MEDIUM |
| provenance | source dicts + recomputed chains | API JSON | provenance audit view | OBS-PY-FE | LOW |
| health | per-service endpoints | same | derived status | OBS-PY-FE | MEDIUM |
| configuration | env vars consumed at runtime | config modules | none | n/a (influence only) | HIGH (influence) |
| commands | UI intent → proxy → boundary → audit event | audit trail | command_requested/rejected | OBS-PY-FE | HIGH (path) |

Rule: any future implementation that would let a Display-surface value flow back
as an Authoritative-source input is FORBIDDEN (second-source-of-truth creation).

## 7. Contract map

Twelve contracts. Each states producer/consumer, identity, authority, epistemic
handling, failures, security, provenance, versioning. No code is written here.

```text
C-01 Source Contract      producers: owning services (CORE-*) · consumer: OBS-ADAPTER or future bridge
  Observability feeds are pulled, never pushed by authority. Sources MUST NOT depend on the
  observatory. Identity: source-defined. Authority: source owns semantics. Versioning: source-declared;
  absent versioning is recorded, not assumed (AQ-009).
C-02 Adapter Contract     producer: OBS-ADAPTER · consumer: OBS-PY-BE ingest
  Adapter conforms to the backend vocabulary (DEC-001). Redaction before transport. Bounded local
  queue; drops counted, never silent. Failure taxonomy retryable/permanent preserved.
C-03 Observation Contract producer: OBS-PY-BE ingest · consumer: store + projections + UI
  Minimum honest representation: known / unknown / missing / not_measured / contradicted /
  observed / inferred / unverified. Forbidden transforms (P7): unknown->false, unknown->zero,
  unknown->healthy, missing->empty-success, unmeasured->zero, unverified->certified.
C-04 Event Contract       producer: constructors (backend + conforming adapter) · consumer: store
  Envelope + identity (evt-{category}-{sha256[:24]}) + content hash REQUIRED. Correlation/
  causation carried, propagation best-effort (UNKNOWN end-to-end). No broker introduced.
  Dedupe (same id+hash) and conflict (same id, different hash) preserved as-is.
C-05 Projection Contract  producer: pure projection functions · consumer: gateway/API
  Events-in/state-out, no I/O, no fabrication. Sibling projections MUST agree on absence
  semantics (F-003 alignment in INC-01). Rebuild-from-events remains a property, not a procedure.
C-06 Query Contract       producer: store search · consumer: console/export/audit
  Limit-only pagination preserved. Invalid bounds map to 400 (GAP-003, INC-01), never 500.
  Export CSV/JSON field sets are stable display contracts once implemented against.
C-07 Live-Update Contract producer: AsyncEventBus + polling sources · consumer: OBS-PY-FE
  SSE retained as-is; 5s polling retained as-is (DEC-003). No topics, no stream auth, no
  reconnect semantics in INC-01 (REQUIRES_DECISION for later; AQ-003 deferred).
C-08 Evidence Contract    producer: ledgers/bundles · consumer: provenance views, auditors
  Bundles (audit-bundle-v1, workspace-export-v1) are stable formats. Recomputed chains MUST be
  labeled as ordering evidence, never as immutable ledgers (P-002 constraint).
C-09 Provenance Contract  producer: constructors → store → projections · consumer: audit views
  Displayed claims REQUIRE source identity + transform identity + verification status fields
  present in the view model (status may be `unverified` — the value MUST exist, P-001/P-005).
  Carried dictionaries MUST be labeled unverified until a verification path exists.
C-10 Governance/Command Contract  producer: UI intent · consumer: backend boundary → audit event
  Enforcement point is backend code (never UI filtering — B-003). Trusted-proxy identity MUST be
  documented as an exposure assumption wherever it is relied upon (B-002). No production command
  execution authorized by this scope.
C-11 Error Contract       all boundaries: named failures unavailable / timeout / invalid_response /
  process_crashed / unknown_failure with observable representation + epistemic consequence +
  audit consequence each. Fallbacks MUST NOT conceal uncertainty (section 14 of D30 is the input).
C-12 Security Contract    authentication / authorization / session / API+stream access / secrets /
  PII / logging / redaction / audit. Observed behavior is bounded, never certified
  (certification = NONE carried from D30). Unknowns stay UNKNOWN or NOT_CERTIFIED.
```

## 8. Observation model

The Observatory may observe: service health/read endpoints, event ingest streams,
ledgers and bundles, governance/audit projections, workspace artifacts. It may
represent: measured values with source identity; absence via the eight
C-03 states; contradictions as contradictions. It MUST NOT represent: inferred
values as observed (F-001 constraint: constructed timestamps labeled or
avoided); absent actors as named principals beyond the documented
`anonymous/observer` display convention (F-002 preserved, labeled);
unmeasured fitness as zero; unverified provenance as certified.

## 9. Event model

REQUIRES no change in INC-01. Disposition per element: envelope IMPLEMENTED
(preserve); identity IMPLEMENTED (preserve); hash IMPLEMENTED (preserve);
persistence IMPLEMENTED (preserve SQLite append); deduplication IMPLEMENTED
(preserve); correlation/causation PRESERVE_AS_IS (carry; propagation stays
UNKNOWN); ordering PRESERVE_AS_IS (rowid/timestamp; no guarantee claimed);
replay IMPLEMENT_LATER (GAP-001; need unproven — investigation first);
broker OUT_OF_SCOPE (explicitly: no broker may be introduced by the next gate);
versioning REQUIRES_DECISION (AQ-009; contract tests in INC-01 pin current
behavior without inventing a version scheme).

## 10. Read-model model

Source of truth: owning services + event store (per domain, section 6).
Projection owner: OBS-PY-BE projection modules. Rebuild responsibility: none
assigned (no procedure exists; property only). Staleness representation:
REQUIRED wherever SSE drops or 5s polls feed a view — views MUST be able to
show `stale`/`unknown-freshness` once a later increment provides the signal;
INC-01 does not add the signal (deferred, section 25 signal list marks it
missing). Failure behavior: projection None → 404 preserved; assert-paths
(partial, D30 section 10) MUST gain explicit mapping before any surrounding
refactor (constraint on later gates, not INC-01 work).

## 11. Live-update model

Retain SSE + retain polling (DEC-003; working behavior, no material defect
evidenced). Adapt neither. Add nothing in INC-01. Deferred with explicit owner
questions: topics (does any view need selective subscription? unproven),
reconnect semantics (server-side contract undefined), stream authorization
(blocked on AQ-010 exposure answer — cannot be safely scoped blind).

## 12. Failure semantics

F-001..F-004 become constraints: F-001 PRESERVE_AS_IS + tests pinning
timestamp behavior + C-03 labeling where displayed; F-002 PRESERVE_AS_IS
(reads) with B-001/B-002 exposure documentation; F-003 IMPLEMENT_NOW
(align genome/gene/chromosome absence to `unknown`, sibling-consistent, with
tests); F-004 PRESERVE_AS_IS (deny-default engine keeps benign display
defaults; any change REQUIRES_DECISION). GAP-003 (search-bound 500) becomes
400-mapping in INC-01 per C-06/C-11. Every later implementation boundary MUST
fill the C-11 triple (representation + epistemic consequence + audit
consequence) for all five named failures.

## 13. Epistemic model

End-to-end preservation chain for INC-01 and beyond: source state → adapter
(no collapse: drops counted, invalid rejected+logged) → ingest (no collapse:
invalid→400, empty batch→accepted/0 explicitly) → store (no collapse: conflicts
→409) → projection (no collapse: eight C-03 states) → API (no collapse:
unknown serialized, never omitted silently) → UI (no collapse: badges for all
eight states; raw render labeled where redaction absent). Negative tests for
unknown/missing/not_measured/contradicted/unavailable/timeout/invalid/
crashed/unauthorized/forbidden/unverified are REQUIRED in the verification
contract (section 24) for every touched path.

## 14. Provenance model

P-001 (unverified carried dicts): IMPLEMENT_NOW the labeling (C-09 status
fields in view models for touched views), mechanism IMPLEMENT_LATER.
P-002 (recomputed chain): PRESERVE_AS_IS + labeling constraint (C-08); stored
ledger REQUIRES_DECISION (DUP-004 convergence question).
P-003 (vocab drift): IMPLEMENT_NOW via contract tests (GAP-005/DEC-001).
P-004 (saved-trace disclaimer): PRESERVE_AS_IS (must survive redesign —
frozen UI text).
P-005 (ISR ambiguity): preserved from D30A; OUT_OF_SCOPE for observatory
implementation (constitutional track owns it).
P-006 (verbatim payloads): IMPLEMENT_LATER (GAP-006; secrecy overhaul needs
threat model — AQ-008/AQ-010 first).

## 15. Governance boundary

Command path fixed (UI → proxy → require_operator → safe-mode → boundary →
audit event; executes nothing). Enforcement point: backend code. UI filtering:
convenience only (B-003 recorded as permanent constraint). Trusted-proxy:
explicit exposure assumption (B-002; deployment documentation in INC-01,
section 20 item 6). Workspaces: disabled-by-default + governed service
preserved as-is. Production command execution: NOT AUTHORIZED by this scope
or the next gate.

## 16. Security boundary

Bounds (not certifications): token-gated writes when configured; session
httpOnly+HMAC for proxy routes; server-side-only backend token; marker
redaction + workspace secret scan at intake; audit trails on commands, roles,
snapshots. Explicit non-bounds: reads/stream unauthenticated-capable (B-001);
no client redaction; verbatim payload storage; PII posture UNKNOWN; .env
contents unexamined. Any security property not evidenced: UNKNOWN or
NOT_CERTIFIED. No security work in INC-01 beyond documentation + pinned tests.

## 17. Duplication decisions

```text
DUP-001 (vocab mirror): DEC-001 — backend domain.py is the contract of record;
  adapter conforms. Mechanism: ADAPT-via-tests (contract-conformance suite in
  INC-01), NOT consolidation (no shared package — preserves deployment decoupling;
  reversible). Drift risk retired by binding, not by merging.
DUP-002 (marker sets): PRESERVE_AS_IS + contract tests assert documented sets;
  convergence REQUIRES_DECISION (recall measurement needed first).
DUP-003 (secret mechanisms): PRESERVE_AS_IS; convergence REQUIRES_DECISION
  (threat model first, AQ-008).
DUP-004 (ledger plurality): SEPARATE declared for INC-01 horizon (each ledger fits
  its system); shared-verifier properties INVESTIGATE (later gate).
INV-001 (autonomous-api dirs): INVESTIGATE (names-only; no candidacy).
INV-002 (governance dashboards): SEPARATE by layer (constitutional vs display);
  convergence OUT_OF_SCOPE.
OBS-EX: SEPARATE permanently as design history (non-authoritative).
```

## 18. Gap prioritization

```text
GAP-005 contract binding   | IMPLEMENT_NOW  | highest drift risk; zero prod-code risk
GAP-003 search-bound 500   | IMPLEMENT_NOW  | honest-failure defect; tiny blast radius
GAP-004 audit UI hookup    | IMPLEMENT_NOW  | completes an existing contract; UI-only
F-003 (from findings)      | IMPLEMENT_NOW  | sibling-consistency; projection-only + tests
GAP-006 payload secrecy    | IMPLEMENT_LATER| needs threat model (AQ-008/AQ-010)
GAP-002 cursors            | IMPLEMENT_LATER| no correctness defect evidenced
GAP-007 serve path         | IMPLEMENT_LATER| investigate operations reality first (docs step in INC-01: record, don't solve)
GAP-001 replay             | IMPLEMENT_LATER| need unproven; investigation before scope
```

Priority order followed constitutional impact > epistemic risk > security >
authority ambiguity > correctness > coupling > cost (UI value never led).

## 19. Architectural-question disposition

```text
AQ-001 persistence suitability | evidence-recorded (single file, WAL) | DEFERRED, non-blocking
AQ-002 transport future        | evidence-recorded (bus + HTTP)      | DEFERRED, non-blocking
AQ-003 live-update adequacy    | evidence-recorded (SSE + poll)      | DEFERRED, non-blocking (DEC-003 retains)
AQ-004 UI exposure model       | evidence-recorded (direct reads)    | DEFERRED, non-blocking (documented B-001)
AQ-005 authority convergence   | ambiguous preserved                 | DEFERRED, non-blocking (no authority change scoped)
AQ-006 ownership boundaries    | DEC-001 resolves vocab only         | PARTIAL, remainder deferred
AQ-007 ISR ambiguity           | inherited from D30A                 | DEFERRED (constitutional track owns)
AQ-008 redaction boundary      | evidence-recorded                   | DEFERRED, blocks GAP-006 only (which is LATER)
AQ-009 schema versioning       | INSUFFICIENT_EVIDENCE preserved     | DEFERRED; contract tests pin behavior w/o versioning
AQ-010 deployment exposure     | evidence-recorded (proxy assumption)| DEFERRED, blocks stream-auth only (not in INC-01)
```

Blocking count for INC-01: 0. Any scope beyond INC-01 re-enters triage against
this table; deferred questions are not permission.

## 20. First implementation increment (INC-01: "Contract binding + honest failures")

Smallest meaningful observation-integrity increment. Six items, all reversible,
no new infrastructure, no authority change:

```text
1. Backend↔adapter vocabulary contract tests (GAP-005, DEC-001). New test file;
   asserts category/severity/epistemic sets, identity construction, timestamp rules,
   redaction-marker documentation. Zero production-code change.
2. Search-bound error mapping (GAP-003). Invalid since/until → 400 with reason;
   preserves limit-only semantics. Narrow store/routes change + tests.
3. Workspace audit UI hookup (GAP-004). Wire existing audit() client to the
   workspaces view. Frontend-only + tests/boundary update.
4. F-003 alignment (genome/gene/chromosome absence → unknown) + sibling-consistency
   tests + negative epistemic tests for touched projection paths.
5. Negative-test accompaniment for every touched path (unknown/missing/not_measured/
   contradicted/unavailable/invalid/unauthorized per section 24 minimum).
6. Deployment-constraint record (B-001/B-002/B-003) as documentation accompanying
   the increment — proxy-only exposure assumption, token configuration effect,
   UI-filtering non-boundary. No code.
```

Rationale: demonstrates actual observation honesty (drift bound, failures
honest, unknowns rendered) with near-zero blast radius. Explicitly NOT in
INC-01: replay, cursors, secrecy overhaul, ledger convergence, new source
wiring, stream auth/topics/reconnect, persistence changes, any consolidation.

## 21. File allowlist (next implementation gate ONLY)

```text
MODIFY (narrow purpose binding; any wider change exceeds scope):
  tests/observatory/test_adapter.py, test_adapter_batch.py, test_adapter_runtime.py (extend)
  observatory/backend/store.py            (GAP-003 mapping only)
  observatory/backend/api/routes.py       (GAP-003 mapping only, if handler-side)
  observatory/backend/projections_genomes.py (F-003 alignment only)
  observatory/frontend/lib/workspaces.ts  (GAP-004 hookup only)
  observatory/frontend/app/workspaces/page.tsx (GAP-004 hookup only)
  tests/observatory/test_frontend_boundary.py (GAP-004 surface assertions)
CREATE (only these):
  tests/observatory/test_backend_adapter_contract.py (GAP-005 suite)
DOCUMENTATION (only this artifact + deployment-constraint note in increment):
  docs/observatory/IMPLEMENTATION_SCOPE_D31.md (this file)
CONFIGURATION: none permitted.
TESTS for touched paths: required companions (section 24), same files above.
```

## 22. Frozen paths (next gate MUST NOT modify)

```text
observatory/backend/domain.py        (contract of record — assert against, never alter semantics)
observatory/backend/governance.py, bus.py, config.py (semantics; tests may read)
observatory/backend/workspace_governance*.py, workspaces_store.py, workspace_service.py
observatory/backend/gateway.py, projections*.py (except projections_genomes.py per §21)
observatory/adapters/               (all production code — conformance target, not edit target)
generated/**  constitutional_architecture/**  certification/**  tiannara/**
compiler/** knowledge/** civilization/** evolution/** product_factory/** learning/**
vertical_slice/**  evidence/**  release/**  autonomous-api/**  dashboard/**  reasoning-ui/**
folder/**  docs/observatory/* (except this artifact)  .env*  lockfiles  CI configs
UI disclaimer texts (console saved-trace notice; workspace secrets warning)
```

## 23. Dependency policy

```text
new Python dependency: NONE (stdlib + fastapi/pydantic/httpx suffice for INC-01)
new frontend dependency: NONE (next/react suffice)
new infrastructure/storage/transport/service/runtime: NONE (explicitly: no broker,
  no new database, no cache, no queue — evidence establishes no necessity)
```

Any future proposal must record: insufficiency of existing capability; security,
operational, licensing, failure implications; migration/removal path. D31
installs nothing.

## 24. Test/verification contract

Required for the implementation gate (semantics, not HTTP-status theater):

```text
contract tests (backend↔adapter vocab, identity, timestamp rules, marker sets documented)
projection tests (F-003 alignment; sibling-consistency across all six projection modules)
epistemic-state tests (unknown / missing / not_measured / contradicted preserved per touched path)
failure-semantics tests (unavailable / timeout / invalid_response / process_crashed /
  unknown_failure mapping on touched boundaries; GAP-003 400 case)
provenance tests (C-09 status fields present; unverified labeled; P-004 disclaimer intact)
governance boundary tests (existing suites must stay green; no boundary change permitted)
authorization tests (token-on/token-off behavior pinned where touched; B-001 documented)
SSE/live-update tests: none required (mechanism untouched; DEC-003)
security/redaction tests (workspace scan + command redaction suites stay green)
determinism tests (contract suite order-independent; identical repo state → identical results)
regression tests (full tests/observatory/ green; canonical pytest profile unchanged)
```

Negative cases REQUIRED per touched path: unknown, missing, not_measured,
contradicted, unavailable, timeout, invalid_response, process_crashed,
unauthorized, forbidden, unverified evidence.

## 25. Operational observability requirements

Minimum signals to distinguish (missing ones marked MISSING — later increments):

```text
source unavailable/timeout      MISSING (no source health aggregation) — later
adapter failure                 PRESENT (sent/dropped/failed counters + failure JSONL)
projection failure              PARTIAL (None→404; assert-paths unmapped) — constraint §10
query failure                   PRESENT (HTTP error mapping; GAP-003 closes 500 path)
SSE failure                     MISSING (no server-side disconnect/failure signal) — later
frontend fetch failure          MISSING (fetch-error paths unsurveyed) — later
authorization failure           PRESENT (401/403 + audit events on commands/roles)
stale data                      MISSING (no freshness signal) — later
unknown data                    PRESENT (eight-state model end-to-end)
```

The Observatory MUST NOT report itself healthy solely because its HTTP process
is alive (constraint on all future status/health work).

## 26. Explicit non-goals

D31 and the scoped increment do NOT: implement beyond INC-01; refactor; rename;
delete; consolidate; install dependencies; change configuration; change runtime
behavior beyond the four narrow fixes; change authority; execute commands;
deploy; certify security/performance/production-readiness; commit; push.

## 27. Deferred decisions

All REQUIRES_DECISION items (ledger convergence, replay need, persistence
suitability, transport future, authority convergence, schema versioning,
redaction convergence, stream auth/topics/reconnect, new-source wiring,
staleness signaling, stored-payload secrecy mechanism) plus all ten AQs except
the AQ-006 partial. Deferred ≠ denied; each names its owning future question.

## 28. Risks

```text
R-01 Contract tests pin behavior but cannot prevent intentional divergence —
  mitigated by review convention, not by this scope.
R-02 F-001/F-002/F-004 preservation keeps known warts visible — accepted;
  hiding them would be the larger risk.
R-03 Single-file SQLite remains unassessed under concurrent writers (AQ-001).
R-04 Direct-backend exposure remains a deployment fact outside repo control
  (AQ-010); scope documents the assumption but cannot enforce it.
R-05 Scope creep (wiring new sources early) is the likeliest integrity failure;
  allowlist + frozen paths are the guardrails.
```

## 29. No design-reference leakage (rejected assumptions)

Rejected as current-implementation assumptions (not philosophically; evidence
absent): Elixir, Phoenix, OTP, ETS, PubSub, GenServer, Kafka, Redis,
PostgreSQL, WebSockets, Sentinel/Omega/ASC/Crucible modules. Future adoption
remains possible only via a later architecture gate with evidence and need.
D30 E-006/E-007/E-008 are the standing evidence.

## 30. Architectural decisions (bounded selections; all others REQUIRES_DECISION)

```text
DEC-001 backend-owns-vocab   | backend domain.py is contract of record; adapter conforms
  via tests | evidence: ingest enforces (de facto authority), mirror observed |
  alternatives: shared package (rejected: coupling), adapter-owns (rejected: no
  enforcement point) | tradeoff: documentation burden | reversibility: full (tests only)
DEC-002 no-new-infrastructure | evidence: all INC-01 items satisfiable with current
  stack | reversibility: full
DEC-003 retain-live-mechanism | SSE + 5s poll retained | evidence: working, no material
  defect | reversibility: full
DEC-004 collapse-triage      | F-003 fixed; F-001/002/004 preserved+labeled+pinned |
  evidence: §11 findings | reversibility: full
DEC-005 authority-separation | display boundary and kernel stay separate; config≠authority
  rule binding | evidence: §6 matrix | reversibility: full (no code moved)
```

## 31. Evolution boundary

```text
evolution_execution = NONE
optimization = NONE
production = NONE
```

D31 defines candidate scope only. No candidate architecture beyond section 30;
no migration; no optimization.

## 32. D31 conclusion

The next implementation gate can begin with a bounded contract: six reversible
items (INC-01), seven modify-targets plus one new test file, explicit frozen
paths, zero new dependencies, and a verification contract that tests honesty
rather than HTTP success. Authority stays where D30 found it. Unknowns stay
unknown. The Observatory remains a surface, not a source.
