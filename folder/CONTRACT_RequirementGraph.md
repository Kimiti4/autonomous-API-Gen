# CONTRACT_RequirementGraph (R1-B D02)

**Contract:** `RequirementGraph`
**Status:** R1-B Deliverable D02. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `reqgraph/core`

**Invariants this contract satisfies:** INV-B02 (RequirementGraph precedes ISR construction).

---

## 1. Purpose

The `RequirementGraph` is the typed semantic bridge from requirements to ISR construction. It is the **first canonical contract** in the chain; nothing downstream may produce or modify requirements.

## 2. Architecture

```text
RequirementGraph
├── requirements
├── relationships
└── graph identity
```

## 3. Identity

- **Graph ID:** content hash (SHA-256) over canonical serialization of all requirements and edges.
- **Requirement ID:** UUIDv5 derived from a content-addressed input (e.g. statement + acceptance criteria). Stable across revisions.
- **Edge ID:** content hash over (source requirement ID + edge type + target requirement ID + ordering index).

## 4. Lifecycle and mutability

- **Frozen at construction.** Pydantic `frozen=True` equivalent.
- **Append-only per revision.** A new graph revision is a new identity; the previous is immutable.
- **Validation at construction.** Cycle, conflict, dangling reference errors raise; partial graphs are not returned.

## 5. Edge types — explicit assessment

The four existing relationship classes are explicitly assessed below. **No new edge types are added in R1-B merely for completeness.** Adding a new edge type requires an ADR.

| Edge type | Semantic | Required? | R1-B verdict |
|---|---|---|---|
| `DEPENDS_ON` | source depends on target for some property | yes | **KEEP** |
| `CONFLICTS_WITH` | source and target are mutually exclusive | yes | **KEEP** |
| `REFINES` | source is a refinement of target (more specific) | yes | **KEEP** |
| `OWNED_BY` | source is owned by target (e.g. a stakeholder, team) | yes | **KEEP** |

The audit referenced 8 edge types (`REFINES, DEPENDS_ON, CONFLICTS_WITH, SATISFIES, CONSTRAINS, TRACES_TO, DUPLICATES, RELATES_TO`). Four of those (`SATISFIES, CONSTRAINS, TRACES_TO, DUPLICATES, RELATES_TO`) are **not** in the current canonical implementation (`reqgraph/core/graph.py:25-44`). They are not added by R1-B. If a future program needs them, it is an ADR-gated change.

## 6. Field classification

| Field | Classification |
|---|---|
| Graph ID | **semantic** (identity of the graph) |
| Requirement ID | **semantic** (identity of the requirement) |
| Edge type | **semantic** (defines the relationship semantics) |
| Requirement content (statement, acceptance_criteria, priority, source_refs) | **semantic** |
| Ambiguity score, resolution_ref | **derived** (computed) |
| Source provenance (extractor, prompt hash, timestamp) | **observational metadata** |
| Serialization (deterministic JSON) | **derived** |
| Content hash (SHA-256) | **derived** |

## 7. Validation rules

- **Cycle handling:** Acyclic graph required; cycle detected → `RequirementGraphCycle` raised.
- **Conflict semantics:** `CONFLICTS_WITH` edges are surfaced in queries; the contract does not auto-resolve them.
- **Refinement semantics:** `REFINES` is a partial order; transitive closure is queryable but not stored.
- **Ownership semantics:** `OWNED_BY` is required for top-level requirements; missing ownership → validation error.
- **Dangling reference:** edge referencing a non-existent requirement → `RequirementGraphDanglingReference` raised.

## 8. Hashing and serialization

- **Serialization:** deterministic JSON over sorted requirement IDs, sorted edge tuples, and stable requirement content.
- **Hashing:** SHA-256 over canonical serialization.

## 9. Provenance

- Source requirement text.
- Source extractor identity (which RequirementExtractor produced this graph; today this is manual).
- Source prompt hash (if applicable).
- Timestamp.
- Author/owner.

## 10. Failure semantics

- Construction errors raise; partial graphs are not returned.
- Validation errors raise with the specific rule violated.
- The contract never silently coerces an invalid graph into a valid one.

## 11. Extension mechanism

- New edge types require an ADR; do not add them via the contract surface.
- New requirement kinds (e.g. non-functional requirements with new fields) require an ADR.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation

`reqgraph/core/graph.py:25-44` (4 edge types: `DEPENDS_ON`, `CONFLICTS_WITH`, `REFINES`, `OWNED_BY`).
- `RequirementNode` carries `kind, statement, priority, acceptance_criteria, ambiguity_score, resolution_ref, source_refs`.
- `RequirementEdgeType` enum (line 39-44) is the 4-edge taxonomy.
- `validate_requirement_graph` enforces acyclicity and reference validity.

The current implementation is the canonical implementation; this contract freezes its API.

## 13. Legacy implementations

None observed in the canonical execution path. The audit referenced 8 edge types that are NOT in the canonical implementation; that is not a "legacy implementation" but a misstatement of the audit.

## 14. Migration destination

n/a (canonical from inception). No migration required.

---

*End of D02. Cross-references: D01 (registry), D03 (ISR construction consumes RequirementGraph).*
