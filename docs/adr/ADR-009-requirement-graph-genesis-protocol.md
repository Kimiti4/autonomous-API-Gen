# ADR-009: Requirement Graph → ISR Genesis Protocol

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-26 |
| **Relates to** | Constitution (Foundational Principle, Multi-Agent Collaboration), ADR-008 (ISR Core), ADR-002/006 (v1.1 Accountability & Evidence) |
| **Scope** | `reqgraph/core/`, `genesis/` |
| **Supersedes** | — (new boundary) |

## 1. Context

The Constitution mandates: *Requirements should never directly generate source
code. All work must flow through the ISR.* But the ISR cannot be conjured — it
must be **derived** from problem-space knowledge with auditable justification.
v1.1 certified an accountability/evidence plane; ADR-008 certified the ISR
substrate. The missing link is a constitutional genesis protocol that transforms
a problem representation into a valid `ISR₀` (lineage root) while producing
certifiable evidence that the derivation is faithful.

## 2. Problem

Define the pipeline:

```text
Problem Statement → Requirement Extraction → Requirement Graph
   → Consistency/Completeness → Genesis Mapping → ISR Candidate
   → Genesis Validation → Canonical ISR₀
```

subject to:

- The Requirement Graph is a **distinct problem-space model**, never merged
  with the ISR.
- Genesis is **deterministic** and **traceable**: every ISR element is justified
  by a requirement or an explicit constitutional default.
- The claim "ISR₀ represents the requirements" is backed by **evidence records
  consumable by the v1.1 accountability plane**, not by assertion.
- No evolution/mutation semantics are defined here (reserved for v1.3).

## 3. Decision

### 3.1 Requirement Graph as a separate constitutional model

Problem-space nodes (functional/non-functional requirements, domain concepts,
stakeholders, constraints) with identity, priority, acceptance criteria,
ambiguity score, and source traceability.  Edges encode `depends_on`,
`conflicts_with`, `refines`, `owned_by`.  The graph is immutable,
content-addressed, and carries its own schema version (distinct from the ISR
schema version).

### 3.2 Consistency/Completeness gate before genesis

Genesis is **fail-closed** on: dangling edges; functional requirements lacking
acceptance criteria; ambiguity above threshold without a resolution ref;
unresolved conflicts; and problem-space implementation leakage (same
forbidden-term invariant as the ISR).  Unresolved items either block genesis
or are escalated to governance with an explicit resolution ref.

### 3.3 Deterministic, evidence-carrying Genesis Mapping

A versioned, pure mapping `(RequirementGraph, MappingSpecVersion,
ConstitutionalDefaults) → ISRGraph + CoverageReport`.  Traceability lives in
the **evidence layer** (CoverageReport maps requirement_id → isr_node_ids),
keeping the ISR graph itself clean of requirement ids.  **Constitutional
defaults** (security, observability, testing, deployment, documentation facets)
are injected when requirements are silent, each tagged
`derivation_ref = "constitution:<rule>"` so user-derived vs constitution-derived
provenance is always distinguishable.

### 3.4 Genesis Evidence Model → v1.1 accountability

`GenesisEvidence` aggregates `CoverageReport`, `ConsistencyReport`,
`ValidationRecord` (ADR-008 invariants), and applied constitutional defaults,
all content-addressed.  A projection maps these 1:1 to v1.1 `EvidenceRecord`s
(`genesis-coverage`, `genesis-consistency`, `genesis-validation`), so the
genesis claim is certifiable by the already-certified accountability plane.
**This is the answer to the evidence question.**

### 3.5 Ports, not implementation

`RequirementReader`/`RequirementStore` for the graph; `GenesisMapper`/
`GenesisValidator` protocols with a reference deterministic implementation.
The seam to v1.3 (`genome construction consumes ISR₀ + RequirementGraph`) is
reserved, not defined.

## 4. Alternatives

- **A. Free-form LLM requirement→ISR translation (no graph).** Rejected: no
  determinism, no traceability, no validation boundary; cannot answer the
  evidence question; violates auditable provenance.
- **B. Unified Requirement+ISR model.** Rejected: couples problem/solution
  space; evolution would mutate requirements; explicitly forbidden by prior
  ordering.
- **C. Eager full mapping (requirements fully determine architecture).**
  Rejected: Constitution mandates evolving *competing* candidates; genesis
  must produce a neutral, valid seed (`ISR₀`), leaving architectural decisions
  to the evolution genome.

## 5. Consequences

- **Benefit:** The Evolution Engine can operate on a valid ISR₀ without
  re-deriving it from requirements.
- **Benefit:** Every ISR element is traceable to a requirement or a
  constitutional default, answering the evidence question.
- **Trade-off:** Explicit Requirement Graph adds upfront modelling cost →
  buys determinism, traceability, and a validation boundary.
- **Trade-off:** Deterministic core may under-use LLM creativity → mitigated
  by letting agents *propose* mappings/requirements that are validated and
  recorded as evidence, while the committed mapping stays deterministic.

## 6. v1.2 Certification Gates (shared boundary)

| Gate | Question | Verification |
|---|---|---|
| **G10** | Can a Requirement Graph produce a valid genesis candidate? | Integration: build `RequirementGraph` → reference mapper → assert `ISRRevision` passes ADR-008 invariants, coverage complete, `content_hash` deterministic across runs. |
| **G11** | Is genesis evidence certifiable by the v1.1 accountability plane? | Assert `project_to_v11_evidence` output matches v1.1 `EvidenceRecord` shape and preserves `content_hash` chain. |

**Reserved for v1.3:** genome construction consumes `ISR₀ + RequirementGraph`;
mutation/crossover semantics operate on the ISR only.  ADR-009 defines the
seam, not the engine.
