# FS-00 Deliverable 3 — ISR / Evolution Audit

**Status:** REVIEW DRAFT — no schema change authorized  
**Source commit:** `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`  
**Companion:** Deliverables 1, 2 and 4 in this directory.

## 1. Verdict against the Full-Stack Compiler acceptance criterion

**Current ISR supports a meaningful subset of full-stack architecture semantics, but it does not yet demonstrate complete, lossless, independently verifiable full-stack compilation.** Keep ISR schema frozen during FS-00. This is an audit finding, not permission to add primitives.

The acceptance criterion requires deterministic lowering from validated technology-neutral ISR through Compiler IR into one complete full-stack application, followed by verification, immutable evidence and requirement-to-deployed-artifact lineage.

## 2. Current semantic surface

At the inspected source commit, `isr/core/graph.py` declares 14 node kinds:

`DOMAIN`, `CAPABILITY`, `SERVICE`, `API`, `DATA_MODEL`, `EVENT`, `SECURITY_POLICY`, `INFRASTRUCTURE_TARGET`, `REQUIREMENT_REF`, `FRONTEND_ROUTE`, `FRONTEND_INTERACTION`, `EFFECT`, `INVARIANT`, `CONSEQUENCE`.

It declares 18 edge kinds:

`SATISFIES`, `IMPLEMENTED_BY`, `EXPOSES`, `PERSISTS`, `PUBLISHES`, `CONSUMED_BY`, `DEPENDS_ON`, `SECURED_BY`, `CONTAINS`, `ROUTES_TO`, `INVOKES`, `CAUSES_EFFECT`, `REQUIRES_INVARIANT`, `CONSEQUENCE_OF`, `REQUIREMENT_DEPENDS_ON`, `REQUIREMENT_CONFLICTS_WITH`, `REQUIREMENT_REFINES`, `REQUIREMENT_OWNED_BY`.

Typed behavior payloads exist for service, API, data model, event, security, effect, frontend route, frontend interaction, invariant and consequence semantics. `ISRRevision` binds graph identity/provenance/content hash and validation surfaces.

This is a stronger source model than the older R1 inventory's nine-node description; the historical report must not be treated as current without reconciliation.

## 3. Lowering coverage and preservation risks

The inspected `compiler/core/lowering.py` constructs carriers for data models, events, security policies, APIs, effects, invariants, consequences, effect bindings, services, frontend interactions and routes. It preserves typed behavior payloads for these supported carriers and rejects some ambiguous bindings, including API operations with multiple explicit service bindings and consequences without explicit targets.

However:

- `DOMAIN`, `CAPABILITY`, `INFRASTRUCTURE_TARGET` and `REQUIREMENT_REF` do not become dedicated first-class `CompilationPlan` carriers in the inspected lowerer.
- Requirement relationships (`REQUIREMENT_DEPENDS_ON`, `REQUIREMENT_CONFLICTS_WITH`, `REQUIREMENT_REFINES`, `REQUIREMENT_OWNED_BY`) do not appear as first-class plan relations in the inspected model.
- General `CONTAINS` ownership semantics are not uniformly represented; the lowerer uses it to collect interactions owned by frontend routes.
- The plan carrier for `FrontendInteraction` resolves its target API only when exactly one `INVOKES` target exists; the inspected code does not reject all non-singleton cases, which warrants a loss/ambiguity test.
- The lowering docstring describes a loss-aware projection, but the presence of typed carriers alone does not prove semantic equivalence. Every unsupported or unrepresented construct needs an explicit reject, policy-gated omission or a proven lossless representation.
- Determinism must be tested across mapping order, canonical serialization, seed/backend policy and artifact packaging; the source snapshot alone does not establish byte-identical full-stack output.

## 4. Android benchmark implications

The Android backend is `STRUCTURAL`, has an empty certified feature set, and enforces a static-shell-only check. It rejects service/API/event/security/effect/effect-binding/consequence/invariant/frontend route and interaction constructs, and typed data-model behavior. Consequently it cannot implement the complete ESAP-APP-001 behavior.

The benchmark requires an actual native app, candidate-bound runtime UI tests, before/after durable-state assertions, process relaunch, offline emulator execution, negative-case coverage, source-to-plan lineage, independent semantic verification and reproducible CI. No end-to-end APK/emulator evidence was established in this audit session. Unit tests using fake subprocesses or synthetic APK ZIPs are not runtime evidence.

Benchmark-specific missing semantics requiring explicit contracts before implementation include:
- case-insensitive local search behavior and oracle;
- durable local-store guarantees and observable state;
- process death/relaunch lifecycle;
- offline behavior;
- UI state/interaction semantics and accessibility selectors;
- acceptance oracles and independent semantic verifier binding.

These are benchmark requirements, not a recommendation to add ISR primitives during FS-00. First determine whether existing typed contracts can express them; otherwise FS-01 must define and govern any schema evolution after this gate.

## 5. Evolution boundary

The evolution engine can construct candidate genomes and decision spaces, but the existence of candidate/mutation/fitness modules does not prove that a candidate preserves the ISR contract, that an evolved design is compilable, or that a proposed self-modification is authorized.

Required safeguards:
- evolution proposes candidates; it does not authorize its own protected schema/compiler changes;
- candidates must bind to parent ISR/genome hashes and explicit mutation operators;
- unknown semantics or missing verification evidence are not accepted as valid fitness improvements;
- certification consumes security obligations and evidence; it must not invent ISR security requirements post hoc;
- a generated artifact's fitness cannot substitute for correctness, security or constitutional approval;
- mutation and rollback must be replayable and auditable.

## 6. Lineage and evidence findings

The target lineage is `requirement_id → requirement_graph_node → isr_node → compiler_ir_node → backend_artifact → deployed_instance`.

Current source provides identity/hash structures and campaign provenance/verifier surfaces, but this audit has not established a complete authoritative, immutable chain spanning every step through a deployed Android instance. `autonomous-api/app/main.py`'s `_DbGenerationProvider.get_isr()` raises `NotImplementedError`, an explicit ISR observation gap. This is not enough to conclude all lineage is absent; it is enough to prevent claiming the observation surface is complete.

Unknown/corrupt/missing evidence must not yield PASS. The backend must reject unsupported semantics; the orchestration/certification boundary must quarantine partial output and retain source, plan, repository, verifier and runtime hashes.

## 7. Findings register

| ID | Finding | Severity | Required disposition |
|---|---|---|---|
| ISR-A01 | Historical R1 node inventory is stale relative to current 14-node/18-edge source | High | Reconcile all older inventory assertions against pinned current source |
| ISR-A02 | Several ISR node kinds and requirement relationships lack first-class plan representation | Critical | FS-01 contract must define complete coverage or explicit fail-closed behavior |
| ISR-A03 | `CONTAINS` is not represented as general ownership in the plan | High | Specify ownership mapping and test preservation |
| ISR-A04 | Frontend interaction target ambiguity may not fail closed for non-singleton targets | High | Add negative test and contract requirement in a later authorized implementation phase |
| ISR-A05 | CompilationPlan is transitional/stabilization IR, not proven canonical full-stack IR | Critical | Resolve in Compiler Architecture ADR and FS-01 |
| ISR-A06 | Android backend is structural-only and refuses benchmark behavior | Critical | Build behaviorally capable backend only after FS-00/FS-01 authorization |
| ISR-A07 | No candidate-bound end-to-end Android runtime evidence established | Critical | Obtain real SDK/Gradle/emulator or approved cloud runner evidence; never simulate |
| ISR-A08 | Complete requirement-to-deployed-instance lineage not demonstrated | Critical | Define evidence contract, verify every edge and expose lineage query |
| ISR-A09 | Observation API ISR binding raises NotImplementedError | High | Assign owner and reconcile with authoritative ISR store |
| ISR-A10 | Evolution fitness/candidate existence does not prove governance or semantic preservation | High | Bind proposals to constitutional authorization and independent verification |

## 8. Required follow-on contract topics

- FS-01: ISR and Compiler IR schema IDs/versions, canonical forms, hashes, node/edge coverage, behavior contracts, unknown-kind policy and migration/versioning.
- FS-02: orchestrator inputs/outputs, deterministic backend selection, composition, partial failure/quarantine, evidence integrity and retry/idempotency.
- FS-03: backend family input obligations, artifact manifest, build/runtime/negative tests, independent semantic verification and evidence schema.
- Certification: verifier identity, anti-vacuity, unknown-state handling, source/candidate binding and immutable verdict record.
- Evolution: proposal versus approval authority, parent-child lineage, rollback and reproducible candidate evaluation.

## 9. FS-00 status

**ISR/Evolution Audit: PARTIAL; acceptance criterion not demonstrated.** Do not change ISR schema or add backend semantics in this phase. Reconcile these findings with Deliverables 1, 2 and 4 and submit for independent review.


## 8. Phase 31 / B3-v2 closeout reconciliation

The Phase 31 closeout ADR records B3-v2 as **NOT_CERTIFIED**: 443 trials completed against a planned 936 before the 12-hour runtime budget expired. This is a campaign verdict, not proof that all Phase 31 implementation is invalid; equally, passing Tier A / certification tests does not upgrade the B3-v2 campaign verdict. The closeout states the ledger chain is intact and distinguishes Phase 31 implementation completeness from B3 campaign certification.

**Effect on FS-00:** the B3-v2 verdict is an input to this ISR/Evolution audit, not the FS-00 output. It does not authorize schema changes or imply evolutionary/compiler capability is certified. The evidence supports keeping the ISR schema frozen during FS-00 and treating candidate/evolution-to-ISR transformations as requiring explicit lineage and verification. Any future claim that relies on B3 certification must remain blocked until a separately authorized campaign achieves its acceptance target and produces verified evidence.

**Evidence reference:** `folder/PHASE31_CLOSEOUT_ADR.md`, sections 2–3 (443 completed; NOT_CERTIFIED; runtime budget exhausted) and the ledger/chain integrity record. No new campaign was run in this audit.


## 9. Multiple ISR model families and system-wide authority gap

This audit must not be interpreted as proof that root-level `isr/core` is the sole ISR used throughout the repository. Source searches and existing architecture inventories identify **at least three** model families:

1. **Root-level typed ISR:** `isr/core/{graph,revision,identity}.py` defines `ISRGraph` and content-addressed `ISRRevision`. The newer root-level compiler path lowers this revision through `compiler/core/lowering.py`; root-level requirement graph, genesis, evolution and certification paths consume it.
2. **Constitutional architecture ISR:** `constitutional_architecture/isr/model/isr.py` and related graph/serialization/semantic modules define a richer `ISR` consumed by `constitutional_architecture/compiler/compiler_context.py`, `constitutional_architecture/isr/isr_graph.py`, and `tiannara/application/evolution/isr_capability_audit.py`.
3. **UniversalISR:** `constitutional_architecture/core/models/isr.py` defines `UniversalISR`, consumed by `constitutional_architecture/core/contracts/compiler.py`, `constitutional_architecture/compilers/*`, the core orchestrator and Tiannara compilation projection/conformance surfaces. The R1 compiler inventory identifies the per-category compiler framework as a separate runtime producing `CompilationBundle` and bypassing root `CompilationPlan`.

The root-level compiler, constitutional Gen-C pipeline and per-category compiler runtime have distinct contracts and input types. Existing repository records differ in how they label the authoritative substrate, so a single system-wide canonical ISR/compiler path is **not demonstrated**. The earlier R1 audit's recommendation to retire legacy paths is a documented proposal, not permission in this FS-00 task to delete them or silently convert data.

**Required resolution before FS-00 can close:**

- obtain the authorized architectural decision identifying the constitutional source of truth and disposition of each ISR/compiler family;
- enumerate production producers/consumers, persistence adapters, serializers, migrations, hashes and provenance paths for all families;
- map each compiler runtime's inputs, outputs, active entry points, tests, generated artifacts and certification status;
- document and test any conversion as a versioned semantics-preserving adapter, including security policy, requirement references, effects/invariants/consequences, deployment intents and evolution metadata;
- prove unknown/unrepresentable constructs block conversion rather than disappear;
- define compatibility, retirement and rollback plans, and update Deliverables 1–4 consistently.

No ISR schema changes, model consolidation or legacy retirement are authorized by this finding. **System-wide ISR/compiler authority: UNRESOLVED; Architectural Evidence, Contract Completeness and Boundary Integrity remain PARTIAL.**
