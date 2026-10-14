# Cross-pipeline obligation projection status

**Status:** implementation started; certification remains blocked  
**Scope:** compiler-neutral ESAP platform, not a TaskFlow-only adapter  
**Updated:** 2026-10-14

## Objective

The compiler must accept different product specifications and target languages/compilers without requiring a new governance framework for each app. A single source-bound obligation contract must carry requirements across analysis, architecture, target selection, generation, tests, runtime evidence, and certification.

The universal projection is deliberately independent of language, framework, backend, and application domain. TaskFlow, the ledger, the capstone, and future applications should supply different source requirements and explicit semantic decisions, while sharing the same projection and enforcement contract.

## Implemented in this increment

- `tiannara/application/compiler/obligation_projection.py` deterministically projects every canonical `RequirementGraph` node into a framework-neutral `CompilerObligationRecord`.
- Each record binds to the source graph ID/hash and carries the requirement statement, acceptance criteria, rationale, kind/domain, and strength/applicability.
- Required `MUST` requirements are kept in the projection's authoritative required-ID set. `SHOULD` and `COULD` remain optional obligations; they are not silently upgraded to mandatory.
- No consumer, enforcement point, implementation, or successful evidence is invented. Projected records stay `UNKNOWN`, without a consumer binding or enforcement point.
- Projection verification recomputes the expected records and manifest hash from the active graph instead of trusting the supplied projection hash.
- Obligation hashes now bind acceptance criteria and rationale as well as the previously hashed semantic fields, so changing acceptance criteria changes the obligation hash.
- `source_bound_certification.py` verifies the graph-to-projection binding and requires the reviewed suite's required IDs to equal the projection's required IDs exactly before any evidence lookup. It uses the graph hash—not the ISR hash—as the source identity at this boundary.
- Adversarial tests cover policy mismatch before evidence reads, source graph mismatch, projection tampering, and the rule that unimplemented obligations remain UNKNOWN.

## Required invariants

1. **One source identity:** the projection must match the exact active RequirementGraph and its content hash.
2. **No omission:** every graph node must map to exactly one obligation; duplicate IDs and missing records block.
3. **No semantic weakening:** statements, acceptance criteria, rationale, priority/strength, and applicability must equal the canonical projection.
4. **No invented proof:** projection status is `UNKNOWN` until a concrete consumer and independently verified execution evidence exist.
5. **Backend neutrality:** obligation IDs and meanings must not depend on target language, framework, database, cloud, or compiler.
6. **Parity:** every generation pipeline must consume the same projection contract; adapters may translate it but cannot remove or weaken obligations.
7. **Evidence separation:** source projection is not runtime enforcement and cannot itself certify a generated application.

## Known integration gap — do not certify

The universal projector and source-bound certification bridge are not yet connected end-to-end to every live compiler entry point. In particular, the existing integrity gate receives caller-provided obligation records and uses `CompilationResult.isr_hash` as the expected source-graph hash. Those are different identities unless an explicit, verified graph-to-ISR binding proves otherwise. The TaskFlow snapshot adapter also remains a separate upstream path and must be reconciled with this shared contract rather than becoming a parallel obligation framework.

The next step is to introduce a trusted source context that carries canonical snapshot identity, graph identity/hash, validated semantic-resolution evidence, and the recomputed obligation projection into both compiler pipelines. Then wire that context into the mandatory integrity gate so the legacy caller-supplied-record path cannot authorize a TaskFlow or other universal-profile compile. Certification must reject absent or mismatched context before looking at runner evidence. Every target adapter must declare how each required obligation is represented and enforced, and acceptance evidence must bind to the exact generated build and runtime consumer.

## Universal senior-developer readiness bar

Before the compiler is described as ready to develop TaskFlow, the ledger, capstone, or another app, it must demonstrate a repeatable process that:

- resolves ambiguities and records human-approved decisions instead of inheriting unsafe schema defaults;
- preserves all functional, security, data-integrity, operational, UX, and deployment requirements across language/compiler adapters;
- generates maintainable architecture and idiomatic target-language code;
- runs static analysis, type checking, unit, integration, negative/security, migration, and end-to-end tests as applicable;
- verifies authentication/authorization and tenant boundaries, transaction semantics, idempotency, auditability, error handling, secrets, and operational health where required;
- performs real builds and runtime tests, with traceable evidence bound to exact source, build, environment, and consumer;
- blocks release on unsupported semantics, missing tests, failing checks, source drift, or incomplete evidence;
- records known limitations and never represents simulations, metadata presence, or hashes alone as proof of behavior.

Passing the TaskFlow trial must validate this reusable process. It must not create a TaskFlow-specific shortcut that has to be rebuilt for the ledger or capstone.
