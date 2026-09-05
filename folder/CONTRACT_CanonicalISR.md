# CONTRACT_CanonicalISR (R1-B D03)

**Contract:** `ISR`
**Status:** R1-B Deliverable D03. The most important R1-B deliverable. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `isr/core`

**Invariants this contract satisfies:** INV-B01 (one canonical ISR semantic authority), INV-B03 (ISR is technology-neutral).

---

## 1. Purpose

The `ISR` is the **single authoritative semantic representation of a software system revision**. It is the canonical source of truth for what a system means. Nothing else may independently define ISR semantics.

## 2. Architectural principle (mandatory)

```text
ISR
≠
Architecture Model
≠
Compiler IR
≠
Generated Artifact
```

This principle is enforced by the contract. The four are distinct semantic surfaces. Conflating any two of them is the exact substrate-duplication problem R0 discovered. Each downstream contract (D04 ArchitectureCandidate, D07 CompilerIR, D09 ArtifactSet) **references** an ISR revision by content hash but does not duplicate its semantics.

## 3. Architecture

```text
ISR
├── identity
├── revision
├── nodes
├── relationships
├── semantic properties
├── provenance
└── content hash
```

## 4. Identity

- **Content hash:** SHA-256 over canonical serialization (`compute_content_hash` at `isr/core/identity.py:44-66`).
- **System ID:** stable identifier for the system (not the revision).
- **Revision ID:** UUIDv5 over the system ID + content hash.
- **Schema version:** pinned at construction (e.g. `isr.core.schema.v1`).

## 5. Lifecycle and mutability

- **Frozen.** Pydantic `frozen=True` on every carrier (`isr/core/revision.py:17-61`).
- **Append-only per revision.** A new revision is a new identity; the previous is immutable.
- **`with_system(new_system)`** creates a new immutable revision (`constitutional_architecture/isr/model/isr.py:102-110` equivalent in canonical substrate).
- **Construction fails closed.** Invariant enforcement runs at construction (`isr/core/revision.py:50-52`); any violation raises.

## 6. Node and edge taxonomy (frozen)

The canonical ISR is **flat** with 9 node kinds and 8 edge kinds. Extensions require an ADR.

| NodeType | Semantic |
|---|---|
| `DOMAIN` | A bounded context or problem domain |
| `CAPABILITY` | A system capability (verb-noun) |
| `SERVICE` | A service that exposes capabilities |
| `API` | An API surface |
| `DATA_MODEL` | A data model (entity or aggregate) |
| `EVENT` | A domain event |
| `SECURITY_POLICY` | A security policy (authn, authz, secret handling) |
| `INFRASTRUCTURE_TARGET` | A deployment/infra intent (not a concrete tech) |
| `REQUIREMENT_REF` | A reference back to a RequirementGraph node |

| EdgeType | Semantic |
|---|---|
| `SATISFIES` | source (CAPABILITY/SERVICE) satisfies target (REQUIREMENT_REF) |
| `IMPLEMENTED_BY` | source is implemented by target |
| `EXPOSES` | source (SERVICE) exposes target (API) |
| `PERSISTS` | source (SERVICE/API) persists target (DATA_MODEL) |
| `PUBLISHES` | source (SERVICE) publishes target (EVENT) |
| `CONSUMED_BY` | source (EVENT) is consumed by target (SERVICE/API) |
| `DEPENDS_ON` | source depends on target |
| `SECURED_BY` | source is secured by target (SECURITY_POLICY) |

`EDGE_TYPE_COMPATIBILITY` (`isr/core/graph.py:61-93`) is a hard matrix; mismatch raises `ISRInvariantViolation` (`isr/core/invariants.py:80-90`).

## 7. Forbidden implementation terms (25 terms)

The 25 forbidden implementation terms in `isr/core/invariants.py:16-42` are the technology-leakage guard. Any occurrence in a node's name, attribute, or edge description raises `ISRInvariantViolation` at construction.

The full list includes but is not limited to: `FastAPI`, `React`, `PostgreSQL`, `Docker`, `Kubernetes`, `AWS`, `Azure`, `GCP`, `pytest`, `Playwright`, `SQLAlchemy`, `Rust`, `Axum`, `Kafka`, `Redis`, etc. The exact list is the canonical source of truth in `isr/core/invariants.py:16-42`.

## 8. Semantic properties (the rich semantics that selectively migrate from B)

The rich `constitutional_architecture/isr/model/isr.py:ISR` carries: business_capabilities, requirements, acceptance_criteria, deployment_intents, testing_anchors, documentation_intents, evolution_objectives, protected_regions, evolution_policies, architectural_decisions, security_threats, reliability_requirements, architectural_boundaries, constraints.

**R1-B policy:** semantic properties from the constitutional ISR that are genuinely semantic (e.g. requirement-layer semantic obligation / test / verification distinction, technology-leakage rejection) **may** be selectively migrated into `isr/core/invariants.py` (or a new `isr/core/semantics/`) in R1-D.1. Semantic properties that duplicate downstream contracts (e.g. architecture decisions belong in D04 ArchitectureCandidate; acceptance criteria are already in D02 RequirementGraph) **must not** be migrated.

The rich `System/Module/Entity/Service/Workflow/Interface/Event/Deployment/...` model is **not** the canonical ISR. The canonical ISR is flat (9 NodeType, 8 EdgeType). R1-D.1 selectively absorbs the genuinely-semantic validators; the rich model is retired as runtime.

## 9. Hashing and serialization

- **Serialization:** canonical JSON with sorted keys.
- **Hashing:** SHA-256 over canonical serialization. The hash is the ISR's identity.
- **Provenance hash:** the content hash of the Provenance carrier is included in the ISR's content hash.

## 10. Provenance

`Provenance` (frozen Pydantic at `isr/core/identity.py:18-32`):
- Source (requirement extractor or human author).
- Author.
- Tool versions (extractor, semantic validators).
- Timestamp.
- Source prompt hash (if applicable).

## 11. Failure semantics

- Forbidden-term leakage → `ISRInvariantViolation` (fail-closed).
- Type/edge mismatch → `ISRInvariantViolation` (fail-closed).
- Validation errors → `ISRInvariantViolation` (fail-closed).
- Construction never silently coerces an invalid ISR into a valid one.

## 12. Extension mechanism

- New NodeType / EdgeType require an ADR; do not add them via the contract surface.
- New semantic validators are added in `isr/core/invariants.py` (or `isr/core/semantics/`); they must be fail-closed and must not weaken existing invariants.
- The contract surface is frozen; extensions are versioned.

## 13. Current implementation

`isr/core/{graph,identity,invariants,revision}.py`:
- 9 NodeType, 8 EdgeType (frozen at `isr/core/graph.py:11-32`).
- `ISRRevision` frozen, content-hashed (`isr/core/revision.py:17-61`).
- `compute_content_hash` SHA-256 over canonical JSON (`isr/core/identity.py:44-66`).
- 25 forbidden implementation terms (`isr/core/invariants.py:16-42`).
- `validate_invariants` fail-closed (`isr/core/invariants.py:50-109`).

The current implementation is the canonical implementation; this contract freezes its API.

## 14. Legacy implementations

- `constitutional_architecture/isr/model/isr.py:ISR` (rich System/Module/Entity/... dataclass model). **LEGACY.** Retired as runtime per R1-D.5. Semantic validators from `constitutional_architecture/isr/semantics/*` are selectively migrated to `isr/core/` in R1-D.1 with LEGACY classification per R1-B.D17.
- `constitutional_architecture/core/models/isr.py:UniversalISR` (Pydantic 17-NodeType, 13-EdgeType typed graph). **LEGACY.** Retired as runtime per R1-D.5. Not used by the canonical execution path.

## 15. Migration destination

- Legacy `constitutional_architecture.isr.model.isr.ISR` → LEGACY classification (R1-B.D17); semantic validators selectively migrated to `isr/core/` in R1-D.1; the rich dataclass model is retired as runtime.
- Legacy `constitutional_architecture.core.models.isr.UniversalISR` → LEGACY; retired as runtime; not migrated.
- The canonical ISR (`isr/core/`) remains canonical from inception.

---

*End of D03. Cross-references: D01 (registry), D02 (RequirementGraph precedes ISR), D04 (ArchitectureCandidate references ISR by hash), D07 (CompilerIR references ISR by hash), D11 (CertificationEvidence references ISR via verification), D12 (RuntimeObservation references ISR via reverse lineage).*
