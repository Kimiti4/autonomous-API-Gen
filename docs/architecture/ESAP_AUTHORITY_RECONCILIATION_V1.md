# ESAP Authority Reconciliation — FS-00 Remediation Phase 1

**Document ID:** ESAP-ADR-FS00-001  
**Status:** APPROVED IMPLEMENTATION BASELINE — FS-00 A1–A4 IMPLEMENTATION IN PROGRESS  
**Design branch:** `remediation/fs00-authority-reconciliation`  
**Implementation branch:** `remediation/fs00-authority-implementation`  
**Parent audit:** FS-00 Checkpoint 15, commit `15d28b79726bd020e8d39dbbb98dd97f5d56d09e`  
**Scope:** authority ownership, contract/version reconciliation, migration boundaries and fail-closed rules.  
**Change boundary:** approved ISR schema/CompilerIR changes and initial route rewiring are in scope on the implementation branch. Backend retirement, capability promotion, certification upgrades, and artifact publication changes remain out of scope.

---

## 1. Purpose and decision boundary

FS-00 found that ESAP has several substantive compiler subsystems but does not yet enforce one reconciled semantic authority across every production entrypoint. This document establishes the remediation baseline so subsequent code changes do not create another competing graph, ISR or IR.

This is an architecture reconciliation record, not evidence that the proposed end-to-end authority chain is already enforced. A canonical owner, a contract specification, a current implementation, a transitional adapter and a certified production route are distinct things. They must be recorded separately.

**Governing rule:** no implementation may claim universal conformance merely because it imports a canonical model, carries a content hash, appears in a registry, or passes a structural test. Every production route must eventually demonstrate the exact source-bound transformation chain and fail closed on unresolved required semantics.

## 2. Authority decisions and current evidence

| Semantic surface | Canonical owner / contract | Current implementation status | Remediation decision |
|---|---|---|---|
| RequirementGraph | `reqgraph/core`; `folder/CONTRACT_RequirementGraph.md` (D02) | The canonical package defines the four-edge taxonomy: `DEPENDS_ON`, `CONFLICTS_WITH`, `REFINES`, `OWNED_BY`. Other requirement graph models remain in the repository and have active or historical consumers. | Retain `reqgraph/core` as the sole target authority. Treat other graph types as explicit adapters/legacy inputs; do not silently equate their identity, taxonomy or validation semantics. |
| ISR | `isr/core`; `folder/CONTRACT_CanonicalISR.md` (D03) | The D03 contract states 9 node kinds / 8 edge kinds. The inspected `isr/core/graph.py` implements 14 node kinds / 18 edge kinds, including frontend, effect, invariant, consequence and requirement-relationship semantics. | Retain `isr/core` as the sole target authority, but mark D03 schema conformance **UNRESOLVED**. Do not delete the added semantic types or pretend the 9/8 contract describes the current graph. Reconcile through a versioned schema/ADR and migration policy. |
| Canonical CompilerIR | `folder/CONTRACT_CanonicalCompilerIR.md` (D07 + D2–D4 refinement) | The contract explicitly distinguishes the future canonical CompilerIR from the current `compiler/core/plan.py:CompilationPlan` stabilization model. | Retain D07 as the target contract authority. Do not create another competing IR. Keep `CompilationPlan` as the behavioral compiler's transitional typed IR until an ADR either formalizes it as a versioned implementation of D07 or defines the migration to a separate canonical module. |
| Behavioral plan lowering | `compiler/core/lowering.py:isr_to_plan` | A substantive typed, relationship-aware `ISRRevision → CompilationPlan` path exists, with explicit failure for selected ambiguous/unresolved relationships. It is not proven mandatory for all compiler families. | Preserve this path as the reference adapter. Its coverage, loss report and route adoption must be independently tested before universal conformance is claimed. |
| Backend protocol | `compiler/core/protocol.py` and D08 contract | The protocol and a small reference composition root exist; other compiler families retain distinct backend abstractions and registries. | Treat the protocol as the target common backend contract. Existing backend interfaces remain explicit adapters until migrated; no forced target retirement. |
| Artifact / verification / evidence / publication | D09–D12 contracts and `certification/evidence` | Implementations and controls are path-specific; universal quarantine, independent verification and authorized atomic promotion are not established. | Keep these as downstream mandatory gates in the target chain. Do not represent their existence in one path as system-wide enforcement. |

### 2.1 Explicitly rejected shortcuts

- Do not reduce the current ISR graph to 9/8 simply to match the stale D03 prose.
- Do not expand D03 silently and call the change backward compatible.
- Do not treat the legacy Constitutional ISR, UniversalISR, CAP-001 EngineeringISR or SystemModel as equivalent to canonical `ISRRevision`.
- Do not rename `CompilationPlan` to `CompilerIR` without resolving D07's required fields, source references, schema versioning, provenance and compatibility.
- Do not infer requirement satisfaction from a requirement reference, source hash, model label, generated file or target registration.
- Do not retire a backend or frontend target to conceal missing semantic support. Unsupported work must be refused before generation, while the target remains available for future implementation.

## 3. Target semantic authority chain

The intended common chain is:

```text
Approved source snapshot
        |
        v
reqgraph/core RequirementGraph (immutable revision)
        |
        v
isr/core ISRRevision (versioned, immutable, content-addressed)
        |
        v
Canonical CompilerIR (D07; transitional CompilationPlan adapter only where declared)
        |
        v
Versioned backend adapter + explicit semantic capability subset
        |
        v
Quarantined ArtifactSet
        |
        v
Independent requirement-derived verification
        |
        v
CertificationEvidence bound to all inputs, tools, artifacts and raw results
        |
        v
Authorized atomic publication
```

ArchitectureCandidate / evolution records may participate where the selected compilation route requires them. They must reference the same ISR revision; they must not become an alternative source of system semantics. The chain must not require every route to run one specific campaign synchronously, but every route must satisfy equivalent mandatory preconditions and publication gates.

## 4. Contract reconciliation work required before schema-level approval

### 4.1 RequirementGraph

The D02 package is the intended authority. A migration inventory must enumerate every non-`reqgraph/core` graph model, import, constructor, serializer and route. For each consumer record:

- exact input type and schema/version;
- source provenance and stable requirement-ID mapping;
- relationship types and their semantics;
- validation behavior and failure modes;
- whether the consumer is production-reachable, test-only, migration-only or dead;
- explicit adapter identity and version, if conversion is permitted.

An adapter must reject relationships or fields it cannot preserve. It must emit a deterministic mapping report; it must not silently drop them or synthesize `SATISFIES`/realization edges.

### 4.2 ISR

D03 originally froze 9/8 for schema 1.x. The user approved the A2 schema ADR to preserve those versions as historical contracts and formalize the current 14/18 vocabulary as schema 2.0. The implementation must:

1. inventory every current node/edge kind and compatibility rule;
2. identify which additions are required semantic carriers versus derived/operational metadata;
3. specify schema versioning, canonical serialization, hashing and provenance behavior;
4. define migration/read compatibility for 9/8 revisions and the current 14/18 graph;
5. verify that every edge type and node payload survives construction, serialization, hashing, reload and downstream projection;
6. specify unknown-kind behavior as fail-closed;
7. establish requirement-reference and MUST-requirement coverage rules without falsely treating a reference as satisfaction.

No node/edge kind is removed in this phase. No existing hash is rewritten. Any schema evolution creates a new revision and has explicit migration evidence.

### 4.3 CompilerIR

The user approved A3: implement a distinct, versioned canonical CompilerIR, retain `CompilationPlan` as a transitional execution-plan projection, and preserve source lineage and explicit projection coverage. The initial implementation is `compiler/core/canonical_ir.py`; the D07 contract is updated accordingly. Backend protocols still consume `CompilationPlan`, so direct CompilerIR consumption across all backend families remains open.

## 5. Mandatory adapter contract

Every adapter between an approved source, RequirementGraph, ISR, CompilerIR or backend must expose the following metadata:

- adapter ID and semantic version;
- input contract ID and schema version;
- output contract ID and schema version;
- source commit / immutable input identity;
- input and output canonical hashes;
- deterministic transformation identity and implementation digest;
- preserved, normalized, deferred and rejected source IDs/fields/relationships;
- diagnostics, including unresolved and ambiguous bindings;
- explicit loss classification;
- validation result and the policy that determines whether loss blocks compilation.

**Blocking rule:** any unapproved, unbound or unresolved MUST requirement; any unsupported required semantic; any ambiguous ownership/binding; any unclassified field/relationship loss; or any unknown schema element blocks compilation before backend generation. A warning may not be converted into PASS by an adapter.

## 6. Migration order

| Sequence | Work package | Required output | Exit condition |
|---|---|---|---|
| A1 | RequirementGraph consumer inventory | Exact consumer/route matrix for canonical and noncanonical graph types | Inventory complete for identified models; full production reachability remains open |
| A2 | ISR schema reconciliation | Versioned registry, 1.x compatibility, 2.0 taxonomy, migration and dual identity | Implemented on remediation branch; CI/test evidence pending |
| A3 | CompilerIR reconciliation | Distinct canonical CompilerIR and transitional CompilationPlan projection | Initial model, lineage, content hash and route integration implemented; full backend migration open |
| A4 | Adapter enforcement | Projection report, explicit loss partition, backend constraints and capability gate | Initial report/gate and two route integrations implemented; universal enforcement open |
| A5 | Route adoption | Incremental migration of each production compiler entrypoint | Each route proves approved source → graph → ISR → IR before generation |
| A6 | Publication integration | Common quarantine, independent verification and authorization contract | Every artifact publication route is gated; bypass tests demonstrate refusal |

A1–A3 are prerequisites for broad route rewiring. A4 may be designed in parallel, but it must implement the approved contracts rather than invent a new semantic authority.

## 7. Acceptance tests required

The remediation is not complete until automated tests demonstrate at least:

1. canonical RequirementGraph construction, immutability, stable identity and deterministic serialization;
2. explicit rejection of unknown relationship types, dangling references, cycles and invalid ownership;
3. ISR schema-version compatibility, all current node/edge kinds, edge endpoint compatibility, behavioral payload validation and deterministic hashing;
4. round-trip preservation of every supported semantic field and relationship;
5. loss-report completeness for unsupported/unknown fields and relationships;
6. MUST requirement coverage from source through ISR and CompilerIR;
7. refusal on missing/ambiguous source bindings, unsupported MUST semantics and unknown schema versions;
8. proof that every production route invokes the mandatory adapters before generation;
9. proof that direct materialization and publication paths cannot bypass verification and authorization;
10. negative controls that deliberately remove a required field, relationship, binding or gate and demonstrate a blocking failure.

Tests must be independent of the adapter implementation where practical. A test that merely checks a file exists, a function returns a model, or a hash is present is not semantic acceptance.

## 8. Current phase status

| Item | Status |
|---|---|
| Select target RequirementGraph owner | DECIDED: `reqgraph/core` |
| Select target ISR owner | DECIDED: `isr/core` |
| A1 RequirementGraph model/consumer inventory | COMPLETE FOR IDENTIFIED MODELS; production reachability and migration remain open |
| Reconcile D03 with actual 14/18 schema | APPROVED; schema registry, 1.x/2.0 validators, migrations and revision envelope implemented on branch; tests pending |
| Select final CompilerIR implementation | APPROVED; canonical CompilerIR and transitional plan projection implemented on branch; full backend migration open |
| Inventory every live consumer and production route | PARTIAL — A1 inventory published; complete route reachability remains open |
| Implement mandatory adapters across all routes | PARTIAL — canonical boundary adopted by Campaign A and authorization campaign; other routes open |
| Enforce universal loss/completeness gate | PARTIAL — CompilerIR projection partition and backend compatibility gate implemented; universal route coverage not established |
| Enforce universal quarantine and publication gates | NOT ESTABLISHED |

**A1 artifact:** [ESAP RequirementGraph Consumer Inventory](ESAP_REQUIREMENT_GRAPH_CONSUMER_INVENTORY_V1.md). It identifies five materially different graph/IR representations and their direct consumers; it does not yet establish full production route reachability.

**A2 artifact:** [ISR Schema Reconciliation ADR](ESAP_ISR_SCHEMA_RECONCILIATION_ADR_V1.md). Approved by the user. The implementation branch adds the single registry, strict schema-version/taxonomy validation, deterministic 1.x→2.0 migration, and a separate provenance-bound revision hash. CI evidence is pending.

**A3 artifact:** [CompilerIR Reconciliation ADR](ESAP_COMPILER_IR_RECONCILIATION_ADR_V1.md). Approved by the user. The implementation branch adds the canonical CompilerIR, source lineage and projection report; `CompilationPlan` remains transitional.

**A4 artifact:** [Adapter Enforcement](ESAP_ADAPTER_ENFORCEMENT_V1.md). The initial report/gate exists and two identified production routes use it. System-wide route enforcement and runtime proof remain open.

**Current outcome:** A1–A4 are approved and their initial implementation is on `remediation/fs00-authority-implementation`. No compiler target is retired, and no backend capability or certification status is upgraded.

## 9. Governance and change control

This document does not supersede the canonical contract registry or D02/D03/D07. The A2 and A3 conflicts have approved ADRs and are being reconciled in the implementation branch; implementation/test evidence remains pending. Any further schema or semantic-authority change requires its own versioned ADR, compatibility tests and independent review. The human governance authority remains the approval point for changes to constitutional or canonical semantic authority.

**Change control:** the approved implementation branch contains runtime/schema changes. This design document records the authority boundary; it does not itself certify those changes.
