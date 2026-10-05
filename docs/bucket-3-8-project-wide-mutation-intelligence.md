# Bucket 3.8 — Project-wide Mutation Intelligence

Bucket 3.8 establishes a read-only impact-planning boundary before ESAP mutates an existing project.

## Guarantees

- Mutations are represented by explicit requests with a reason and target nodes.
- The dependency graph is supplied by governed project state; the planner does not invent dependencies.
- Direct and transitive dependents are computed deterministically.
- Affected architectural layers, obligations, and verification obligations are collected from the impacted nodes.
- Depth-bounded planning is explicitly marked unbounded when known dependents remain outside the requested depth.
- Target-only planning is allowed as a scoped inspection request, but it never claims downstream safety.
- Unknown mutation targets and invalid dependency graphs fail closed.
- Plan digests are deterministic SHA-256 commitments to the complete planning inputs and result.
- Planning never applies a mutation and never authorizes one.

## Governance boundary

An impact plan answers **what could be affected**, not **whether the proposed mutation is correct**.

Therefore the safe-to-apply decision is always false at this layer. A later governed evolution layer must combine this scope with requirement authority, candidate evaluation, implementation, affected-scope verification, regression checks, and certification before admission.

This prevents a locally correct change from silently bypassing downstream verification.

## Dependency semantics

Dependencies are represented as dependent -> dependency.

For a mutation targeting a dependency, the planner walks the reverse dependency closure to identify every known dependent. This supports cross-layer propagation such as:

requirement -> API -> backend/frontend -> documentation

The planner remains architecture-agnostic and does not assume particular technologies.

## Tests

The test suite covers:

- transitive impact discovery;
- cross-layer obligation and verification collection;
- target-only scope;
- bounded-depth detection;
- deterministic plan digests;
- unknown targets;
- invalid self-dependencies;
- duplicate nodes;
- order-independent multi-target planning.

Runtime execution of these tests is not claimed unless an external CI/runtime result verifies them.
