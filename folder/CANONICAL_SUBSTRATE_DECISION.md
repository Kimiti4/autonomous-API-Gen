# Canonical Substrate Decision

**Status:** Accepted. The C-01 substrate fork is decided as Option 1. R1-A is committed; R1-B through R1-F require separate explicit review.

**Authority:** R0 reconnaissance (`folder/R0_RECONNAISSANCE_REPORT.md`) and user acceptance of Option 1 with the C-03 refinement and the 5 architectural corrections.

## Decision

**OPTION 1 — Substrate A is the canonical execution substrate; Substrate B is consolidated onto A.**

The canonical module map is:

| Layer | Canonical |
|---|---|
| ISR | `isr/core` |
| Requirement Graph | `reqgraph/core` |
| Evolution | `evolution/` (root) |
| Compiler IR (current) | `compiler/core/plan.py:CompilationPlan` (stabilization) |
| Compiler IR (target) | future canonical Compiler IR contract (R1-B) |
| Compiler pipeline | Gen-B `compiler/composition.py` (current); Gen-C `constitutional_architecture/compiler/pipeline.py` is the future canonical pipeline (after fail-closed repair) |
| Backend contract | `compiler/core/protocol.py:CompilerBackend` (current) |
| Certification | `certification/` |
| Provenance | existing campaign provenance + ledger |

The constitutional layer (`constitutional_architecture/`) is a governance/specification layer over the canonical substrate, not a second runtime.

## C-03 refinement + BIR as semantic donor

`CompilationPlan` is the stabilization Compiler IR, not the eventual one. The eventual Compiler IR is a future canonical contract.

BIR is a **semantic donor**, not the implementation:

```text
BIR
 │
 ├── useful semantic concepts
 │
 ▼
Canonical Compiler IR specification
 │
 ▼
canonical implementation
 │
 ▼
content hash
serialization
determinism
provenance
```

Content-hash is added to the **canonical Compiler IR contract** (the new implementation), not to BIR. The canonical implementation is a new module. BIR can be retired after its semantic properties are extracted.

## R1-E principle: canonical contracts first, then adapt implementations

R1-E does **not** repair Gen-C defects wholesale. R1-E defines the **canonical contracts** (Verification, Validation, Pass execution, Normalization) first; only then are Gen-C implementations migrated/adapted to those contracts. Gen-C code that cannot satisfy the canonical contract is retired, not patched.

## Semantic-authority invariant

`one canonical ISR` is enforced as a **semantic-authority invariant**, not a directory count: there is exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics. The same principle applies to Compiler IR, Evolution, Backend contract, Requirement Graph, and Provenance.

## Rejected alternatives

- **Option 2 (Substrate B canonical; rewire A to B).** Rejected for evidence continuity. Substrate A has a working campaign runtime, real evolution/crossover, content-addressed ISR provenance, fail-closed certification, 243 Tier A tests, 40 Tier C tests, an intact B3-v2 evidence chain. Substrate B has fail-open validation/verification, semantic loss during normalization, lossy ISR adapters, broken/dead compiler bridge, incomplete transformation recording, filesystem emission inside compilation, multiple backend abstractions. Promoting B would move the system onto a less-proven substrate and invalidate/require the B3-v2 evidence.
- **Option 3 (keep both; typed adapter).** Rejected per audit §39 (NO NEW SOURCE OF TRUTH). Bidirectional adapters recreate the dual-source-of-truth problem.

## Evidence-preservation rationale

The B3-v2 evidence chain is preserved as historical evidence of the old canonical runtime:

```text
B3-v2
  = historical campaign
  = valid evidence for historical substrate

R1 migration
  = transformation

R2 campaign
  = evidence that canonical substrate satisfies its contracts
```

After migration, the new campaign (R2) is the **post-migration certification baseline** — not a re-certification of B3-v2. The historical evidence is not invalidated; a new campaign runs on the new architecture.

## Migration principles

1. Adapters are always `LEGACY → CANONICAL`, never `A ↔ B`.
2. No second source of truth is introduced.
3. Substrate B components are not deleted until every semantic responsibility is mapped to a canonical destination and provenance/evidence impact is recorded.
4. The agent does not "fix" Substrate B defects merely because they exist. First determine whether the component survives canonicalization. No implementation effort is spent repairing a component that the canonicalization plan will retire, unless the repair is explicitly required for migration or safety.
5. The Tier A 243-test suite must continue to pass after every migration step.
6. No historical certification evidence is rewritten.
7. **Canonical contracts are defined first; implementations are migrated/adapted second.** This applies to R1-E and prevents the canonicalization plan from becoming a wholesale Gen-C repair.
8. **BIR is a semantic donor, not the implementation.** Content-hash is added to the canonical Compiler IR contract, not to BIR.
9. **One canonical ISR / Compiler IR / etc. is enforced as semantic authority**, not directory count.

## Forbidden parallel implementations (semantic-authority invariant)

After R1 is complete:

- **ISR:** exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations may exist; none may independently define system semantics.
- **Compiler IR:** exactly one authoritative semantic representation of a compiled architecture's compilation plan. Same semantic-authority principle.
- **Evolution:** exactly one authoritative Evolution engine.
- **Backend contract:** exactly one authoritative backend protocol.
- **Requirement Graph:** exactly one authoritative Requirement Graph.
- **Provenance:** exactly one authoritative Provenance store.
- No bidirectional A↔B adapter.
- No rewriting historical certification evidence.
- No new artifact-emission path that writes to filesystem inside `compile()`.

## Legacy code: temporary existence is permitted

A legacy implementation may still exist temporarily while its replacement is being validated. The condition for temporary existence:

- Explicit `LEGACY` classification.
- Owner (the migration step that retires it).
- Migration destination.
- Dependency boundary (which canonical paths may still reach it).
- Retirement condition.

A legacy implementation without these markings is forbidden.

## Deferred out of R1

- **C-17 (observation lineage via `autonomous-api/`).** Deferred to R2/R3 platform integration phase. `autonomous-api/` is classified as a legacy application/runtime surface; it must not introduce an ISR source of truth. Its final disposition is deferred.
- **C-18 (`pyproject.toml` topology).** Deferred to post-R1 packaging cleanup. First stabilize architecture; then clean packaging.

## Future Compiler IR contract (R1-B)

The eventual Compiler IR is not `CompilationPlan` long-term. The R1-B deliverable defines the canonical Compiler IR contract. `CompilationPlan` is the stabilization implementation; BIR's useful semantic properties are extracted (as references) into the canonical contract's specification; content-hash is added to the canonical Compiler IR.

## Transition

- R1-A (this ADR) is committed as a tracked governance ADR.
- R1-B through R1-F (Establish Post-Migration Certification Baseline) are sequenced per `folder/R1_PLAN.md`.
- **R1-A authorization is not authorization to silently commit every subsequent phase.** Each code-changing gate (R1-B, R1-D, R1-E, R1-F) requires separate explicit review.
- The B3-v2 evidence chain remains valid and is not invalidated.
- `folder/R0_RECONNAISSANCE_REPORT.md` and `folder/R1_PLAN.md` are the untracked planning artifacts that produced this decision. They are kept in the working tree as the decision's provenance.
