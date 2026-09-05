# CONTRACT_ArchitectureCandidate (R1-B D04)

**Contract:** `ArchitectureCandidate`
**Status:** R1-B Deliverable D04. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `evolution/core`

**Invariants this contract satisfies:** INV-B04 (Architecture Model is distinct from ISR), INV-B07 (Evolution does not depend on backend technology).

---

## 1. Purpose

The `ArchitectureCandidate` is the representation consumed by the evolution engine. It **must reference a Canonical ISR revision** and **must not become another ISR**.

## 2. Architectural principle (mandatory)

```text
ArchitectureCandidate
        ↓
must reference
        ↓
Canonical ISR revision
```

The contract enforces this by including the ISR revision's content hash as a non-derivable field. An ArchitectureCandidate without a valid ISR revision reference is rejected at construction. The ArchitectureCandidate's own semantics are about **architecture decisions, topology, and component boundaries** — they do not duplicate ISR semantics.

## 3. Architecture

```text
ArchitectureCandidate
├── candidate identity
├── parent identity
├── ISR revision reference
├── architecture decisions
├── topology
├── component boundaries
├── constraints
├── objectives
├── fitness / evaluation metadata
├── provenance
├── lineage
├── deterministic serialization
└── content identity
```

## 4. Identity

- **Candidate ID:** UUIDv5 over the ArchitectureCandidate's content hash.
- **Parent ID:** the candidate(s) this was derived from (may be empty for seed candidates).
- **ISR revision reference:** the **content hash of the canonical ISR revision** this architecture is for. A candidate may reference at most one ISR revision.

## 5. Lifecycle and mutability

- **Frozen per candidate.** A new candidate is a new identity; the previous is immutable.
- **Append-only per generation.**
- The `Genome` model in `evolution/core/genome.py` (chromosomes+genes) is the de facto ArchitectureCandidate today; the contract formalizes it as `ArchitectureCandidate` in R1-D.3.

## 6. Architecture decisions and topology

- **Architecture decisions:** a sequence of named decisions (e.g. `use_event_sourcing = true`, `expose_graphql = false`). Decisions are technology-neutral; they reference backend capabilities abstractly.
- **Topology:** the component graph (services, repositories, event buses) and the relationships among them.
- **Component boundaries:** explicit boundaries (e.g. bounded contexts, deployment units) — referenced, not defined.
- **Constraints:** hard limits (e.g. `max_components = 50`, `must_not_depend_on = [...]`).
- **Objectives:** fitness objectives (e.g. `minimize_latency`, `maximize_throughput`).

## 7. Field classification

| Field | Classification |
|---|---|
| Candidate ID | **semantic** (identity) |
| Parent ID(s) | **semantic** (lineage) |
| ISR revision reference (content hash) | **semantic** (non-derivable) |
| Architecture decisions | **semantic** (the architecture) |
| Topology | **semantic** (the architecture) |
| Component boundaries | **semantic** |
| Constraints | **semantic** |
| Objectives | **semantic** |
| Fitness / evaluation metadata | **derived** (computed from evaluation) |
| Provenance (operator, seed, timestamp) | **observational metadata** |
| Serialization (deterministic JSON) | **derived** |
| Content hash (SHA-256) | **derived** |

## 8. Hashing and serialization

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization. The hash is the candidate's identity.

## 9. Provenance

- Parent candidate identity (or empty for seeds).
- Evolution operation identity (which operator produced this candidate).
- Seed/randomness metadata.
- Timestamp.
- Evolution run ID.

## 10. Failure semantics

- Construction without a valid ISR revision reference → `ArchitectureCandidateInvalidISRReference`.
- Construction that produces a non-ISR representation (i.e., that defines system semantics independently of the referenced ISR) → `ArchitectureCandidateSemanticDuplication` rejected.
- Evaluation failure does not destroy the candidate; the candidate is recorded with `evaluation_status = FAILED` and the failure metadata.

## 11. Extension mechanism

- New decision kinds (e.g. `use_specific_pattern = X`) are added by extending the decisions schema; the contract surface is frozen.
- New topology primitives require an ADR.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation

`evolution/core/genome.py` (Genome with chromosomes+genes) operates on `isr.core.revision.ISRRevision`. The Genome is the de facto ArchitectureCandidate today. R1-D.3 will formalize this as a typed `ArchitectureCandidate` module under `evolution/core/`.

## 13. Legacy implementations

- `constitutional_architecture/engine/individual.py` and the Substrate B Evolution engine (`constitutional_architecture/engine/evolution_engine.py`). **LEGACY.** Retired as runtime per R1-D.5 with LEGACY classification per R1-B.D17. Semantic properties (e.g. mutation operators, crossover operators) are selectively migrated to `evolution/core/`.

## 14. Migration destination

- Legacy Substrate B Evolution engine → LEGACY classification (R1-B.D17); semantic operators selectively migrated to `evolution/core/` in R1-D.3.
- The canonical ArchitectureCandidate (`evolution/core/`) is formalized in R1-D.3.

---

*End of D04. Cross-references: D01 (registry), D02 (RequirementGraph), D03 (ISR), D05 (EvolutionOperation), D06 (EvolutionRecord), D07 (CompilerIR references ArchitectureCandidate).*
