# Source-binding ingestion integration audit

Date: 2026-10-14
Repository: Kimiti4/autonomous-API-Gen
Working branch: hardening/source-binding-ingestion
Base: d0157e7aefb343e384644713ee27867eeb11ae56

## Status

This audit is a blocker record, not a completion claim. No integration or test is marked PASS without execution evidence.

## Confirmed findings

1. The constitutional compiler exposes `compile_source_bound(...)` and the existing source-binding tests cover missing and structurally invalid bindings.
2. The live intent compiler is a different layer: `tiannara.application.intent.IntentCompiler.compile_full` returns `tiannara.domain.models.isr.IntermediateSoftwareRepresentation`, whose typed architecture is held in a `SystemModel`.
3. The constitutional binding validator instead accepts `constitutional_architecture.isr.model.isr.ISR` and reads `isr.system.requirements`. These are distinct ISR contracts. There is no demonstrated, tested adapter between them in the inspected path.
4. The intent path now separates normalized semantic-text identity from exact source-snapshot identity. `IntentCompiler` computes SHA-256 over the exact caller UTF-8 bytes and passes that digest into graph construction on both initial extraction and repair iterations. `SourceProjectionContext` retains the exact bytes (base64-encoded inside the immutable, self-hashed context) and `to_constitutional_source_binding(...)` refuses export unless graph provenance binds the same exact-byte SHA-256. Focused regression tests were added; they have not yet been run.
5. The projection context now has an explicit conversion helper that reconstructs `ConstitutionalSourceBinding` from the frozen bytes and frozen graph, with caller-supplied graph-to-ISR requirement IDs. This closes the byte/hash identity seam only; it does not create the typed-SystemModel-to-constitutional-ISR adapter or route the live generation request through the constitutional compiler.
6. The generic compiler configuration still defaults `require_source_binding=False`; the new fail-closed entry point is not proof that every source-derived orchestration path uses it.
7. `verify_graph_system_model_traceability` in `tiannara/application/compiler/source_coverage.py` explicitly describes structural references, not semantic satisfaction or runtime enforcement. Backend output and verification must consume mandatory obligations, not just hashes or trace labels.

## Required implementation before closure

- Run the new exact-source hash/context/binding-export regression tests, then define and test the trusted semantic source-unit inventory.
- Implement and test an explicit adapter from the intent compiler's typed ISR/SystemModel to the constitutional ISR requirement identity model, or unify the boundary without silently losing requirements.
- Construct the binding only from the trusted snapshot and the graph actually produced from that snapshot; map every mandatory graph node to a real, unique ISR requirement.
- Route all source-derived generation orchestration through the fail-closed compiler API and prevent alternate entry points from returning artifacts.
- Add negative tests for source mutation, provenance mismatch, omitted/duplicated/unknown mappings, ISR projection mutations, direct-path bypass, and cache bypass.
- Add consumer-level tests proving each mandatory obligation affects backend output and that independent verification rejects omitted or altered obligations.
- Run focused pytest suites and the applicable CI workflows; retain failing and skipped results as evidence.

## Evidence state

| Claim | State | Reason |
|---|---|---|
| Correct working branch established | PASS (branch creation only) | Branch created from the exact source-binding test commit listed above. |
| Exact source bytes/hash align across intent graph and projection context | IMPLEMENTED, TESTS ADDED / NOT RUN | Exact caller-byte SHA-256 is used for graph provenance in extraction and repair; context retains bytes and exposes a fail-closed binding export helper. |
| Trusted ingestion constructs a binding and routes through constitutional compilation | UNKNOWN / NOT IMPLEMENTED | The helper can construct a binding when given explicit requirement IDs, but live intent ingestion does not yet provide the typed-ISR adapter or route into the constitutional compiler. |
| All source-derived entry points fail closed | UNKNOWN / NOT IMPLEMENTED | Compatibility default remains permissive; universal call-site routing not demonstrated. |
| Bypass/omission/mutation regressions | PARTIAL | Existing tests cover missing binding, stale source bytes, unknown IDs and invalid mapping; universal bypass and semantic mutations are not covered by verified runs. |
| Mandatory requirements reach backend behavior and verification | UNKNOWN | Structural traceability is not backend/runtime proof. |
| Focused tests and CI green | NOT RUN HERE | This environment cannot resolve github.com for a repository checkout, and no local test runner is connected. A GitHub workflow lookup for the earlier commit returned no pull-request-triggered runs; that is not evidence of green CI. |

## Integrity rule

Do not report this milestone closed, authorize TaskFlow generation, or promote UNKNOWN/NOT RUN evidence to PASS until the required implementation and test runs are complete.
