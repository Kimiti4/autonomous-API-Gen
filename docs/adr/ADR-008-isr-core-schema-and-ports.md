# ADR-008: Intermediate Software Representation (ISR) Core Schema & Ports

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-26 |
| **Relates to** | Constitution (Foundational Principle), ADR-001..007 (v1.1 Observation Boundary) |
| **Scope** | `isr/core/`, `isr/ports/`, `isr/adapters/` |

## 1. Context & Problem

The platform's mission is to evolve competing software architectures. However,
architecture cannot be evolved if it is represented as source code, framework
configurations, or mutable object trees. The Constitution mandates that the
**Intermediate Software Representation (ISR)** is the canonical source of truth.

We need a formal, immutable, technology-agnostic data model that represents
software architecture as a typed directed graph, enforceable by invariants,
and accessible via technology-independent ports.

## 2. Decision

The ISR is defined as an **immutable, content-addressed, typed directed graph**.

- **Identity:** `revision_id` (lineage tracking) is strictly separated from
  `content_hash` (semantic commitment).
- **Graph Semantics:** Architecture is represented as `Node`s (Domains,
  Capabilities, Services, APIs, DataModels, Events, SecurityPolicies,
  InfrastructureTargets, RequirementRefs) and `Edge`s (satisfies,
  implemented_by, exposes, persists, publishes, consumed_by, depends_on,
  secured_by), preserving semantic relationships rather than nested objects.
- **Invariants:** Enforced at the boundary, fail-closed at construction:
  - *Identity* — every node has a stable identity within the system lineage.
  - *Referential integrity* — every edge references existing nodes.
  - *Type validity* — each edge type constrains its source/target node types.
  - *No implementation leakage* — core graph nodes/edges cannot contain
    implementation primitives (`FastAPI`, `React`, `PostgreSQL`, `Kubernetes`,
    `Terraform`, `AWS`, `Docker`, …). Those belong to compiler/backend mappings.
  - *Determinism* — equivalent semantic content produces identical canonical
    representation and hash (sorted keys, stable JSON serialization).
  - *Immutability* — revisions are never mutated in place; evolution derives
    new candidate revisions from a parent.
  - *Provenance completeness* — every revision declares an explicit derivation
    origin (`created_by`, ISO-8601 `created_at`; `parent_revision_id=None`
    denotes genesis).
- **Ports:** Interaction occurs via `ISRReader` (queries) and `ISRStore`
  (persistence). The evolution port is reserved for v1.3 — v1.2 defines the
  extension point without pretending the Evolution Engine exists.
- **Storage Independence:** The core knows nothing of Postgres, Neo4j, or
  EventStore. Adapters implement the `ISRStore` port; graph semantics do not
  imply graph-database storage.
- **Schema Evolution:** Three-tier versioning (Contract Version → ISR Schema
  Version → ISR Revision) so deterministic migration can connect schema
  generations without silent semantic change.

## 3. The v1.2 Boundary Statement

> **The ISR is the single semantic source of truth for software architecture.**
> Everything else (Requirement Graph, Evolution Engine, Compiler Backends,
> Observation Dashboard) is a transformation, consumer, or projection of the ISR.

```text
Problem → Requirement Graph → ISR Genesis → Canonical ISR → Evolution
        → Candidate ISR → Validation → Compiler Backend → Generated System
        → Runtime Observation → Evidence / Feedback ──→ Evolution
```

The dashboard is not special; it is one consumer of ISR projections.

## 4. Requirement References (ADR-009 boundary)

The ISR permits provenance references to requirements
(`Provenance.requirement_refs`) and a lightweight `REQUIREMENT_REF` node type
carrying only `ref_id`. It deliberately does **not** define requirement
semantics (ambiguity, priority, stakeholder, acceptance criteria, dependency
graph). Those belong to ADR-009 (*Requirement Graph → ISR Genesis Protocol*),
which must answer: *what evidence permits the platform to claim that an ISR
actually represents the user's requirements?*

## 5. Consequences & Trade-offs

- **Benefit:** The Evolution Engine can perform graph transformations
  (mutation/crossover) without parsing source code or framework ASTs.
- **Benefit:** Compiler backends map graph nodes to implementation details;
  the core remains pure.
- **Trade-off:** Graph-based representation requires a canonicalization layer
  for deterministic hashing, adding complexity to serialization.
- **Trade-off:** Strict invariants mean backend mappings must be maintained in
  separate projection layers, not inside ISR nodes themselves.

## 6. v1.2 Certification Gates (pre-registered)

| Gate | Question |
|---|---|
| G0 | Is the v1.2 artifact inventory complete? |
| G1 | Is the ISR schema deterministic? |
| G2 | Are graph invariants enforced? |
| G3 | Is canonical hashing deterministic? |
| G4 | Is provenance complete and verifiable? |
| G5 | Is persistence technology-independent? |
| G6 | Can ISR revisions be reconstructed exactly? |
| G7 | Can v1.1 observation consume the real ISR? |
| G8 | Can invalid ISR states be rejected? |
| G9 | Can schema evolution occur without semantic corruption? |
| G10 | Can a Requirement Graph produce a valid genesis candidate? *(shared with ADR-009)* |

Unit-level coverage for G1–G5 and G8 lands with the substrate
(`tests/test_isr_substrate_v12.py`). G6–G10 are wired into the v1.2 gate
orchestrator as implementation completes; G10 remains an integration boundary
shared with ADR-009.
