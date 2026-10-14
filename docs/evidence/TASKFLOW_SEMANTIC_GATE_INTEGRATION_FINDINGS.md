# TaskFlow Semantic Gate Integration Findings

**Status:** INTEGRATION BLOCKED — the fail-closed primitive exists, but it is not yet a production compiler gate.

## What was inspected

- `experiments/taskflow-native/provider_free/native_adapter.py`
- `experiments/taskflow-native/provider_free/typed_isr_gate.py`
- `experiments/taskflow-native/README.md` and `evaluate.py`
- `tiannara/application/intent/compiler.py` (`IntentCompiler.compile_full`)
- `tiannara/application/compiler/project_compiler.py` (`ProjectCompiler.compile_intent`)
- `constitutional_architecture/compiler/pipeline.py`
- `constitutional_architecture/compiler/backends/backend_selector.py`
- `constitutional_architecture/compiler/passes/validation_pass.py`
- `compiler/kernel.py`

## Latest implementation increment

- Added `experiments/taskflow-native/provider_free/taskflow_semantic_contract.py` with a compiler-owned mandatory field set covering identity/authentication, workspace scope, role permissions, data relationships, task lifecycle, session revocation, API and frontend contracts, persistence, idempotency/audit identity, operations/deployment, and verification traceability.
- The provider-free adapter now emits a graph-ID/hash-bound `SemanticResolutionRecord` whose mandatory fields are all explicitly `UNRESOLVED`; it also exposes the unresolved field list. This is useful negative evidence and does not enable generation.
- The guarded typed-ISR transition now rejects records that attempt to weaken the authoritative field set before checking graph binding and resolution completeness.
- Focused tests now cover the initial unresolved ledger and caller-weakened contract rejection. Focused GitHub Actions run 38181827484 passed 25 tests in 0.58s on PR merge ref head abdd86a6e62e8dc52c9604d3fb7b7ee571b15f3e.

## Verified boundaries

1. The provider-free native adapter builds a deterministic `RequirementGraph`, preserves source traceability, emits an explicit unresolved semantic ledger, and currently returns `system_model=None`, `typed_isr=None`, and `generation_allowed=False`. It does not invoke a live model builder or select a backend.
2. `build_taskflow_typed_isr()` validates a graph-bound `SemanticResolutionRecord` before invoking its supplied SystemModel builder callback. This proves a local transition boundary only; callers can bypass the helper.
3. The repository contains more than one compiler path. The constitutional pipeline consumes `constitutional_architecture.isr.model.isr.ISR`; the universal compiler consumes a `CompilationRequest` and validates its ISR payload before backend lookup. Neither currently receives the TaskFlow `RequirementGraph` plus its graph-bound semantic-resolution ledger. The live application path is `ProjectCompiler.compile_intent` → `IntentCompiler.compile_full`; `IntentCompiler` synthesizes `SystemModel` immediately after graph validation, before `ProjectCompiler` derives requirements and selects backends. A gate added only in `ProjectCompiler` would be too late.
4. The constitutional validation pass currently catches exceptions and reports the ISR as valid in degraded mode. That behavior is not a substitute for a mandatory semantic gate and must not be treated as evidence that the TaskFlow gate is integrated.
5. The native trial's own README describes a genuine run as requiring a configured reasoning provider. No provider-free generation or application certification is claimed here.

## Why direct wiring is unsafe right now

5. Production integration must add a TaskFlow-specific pre-synthesis hook at the `IntentCompiler` graph-to-SystemModel boundary (or an equivalent orchestration path that owns the graph before synthesis). It must carry the exact graph-bound ledger forward and require the same validated context before backend planning. Checking only a `generation_allowed` boolean or validating after `compile_full` returns is insufficient.

Adding a check only to a generic backend selector would be insufficient: the selector has no authoritative TaskFlow graph/ledger to validate. Inventing a graph hash from a different ISR payload, reconstructing semantics after backend choice, or translating missing semantics into defaults would break the provenance and fail-closed guarantees.

## Required next integration contract

Before claiming completion, the live TaskFlow orchestration must carry the exact immutable snapshot-derived graph and its resolution ledger through these explicit stages:

1. Verify snapshot identity and canonical graph hash.
2. Derive the mandatory semantic-field set from the compiler contract (not caller-selected omissions).
3. Resolve each field from the snapshot or a recorded, explicitly approved human decision; otherwise mark it unresolved.
4. Reject unresolved or graph-mismatched records **before SystemModel construction and before backend discovery/selection**.
5. Construct the typed ISR from the gated SystemModel, preserving lineage and graph/hash references.
6. Make the backend selector consume only the gated artifact (or an unforgeable validated compilation context), not a caller-supplied boolean such as `generation_allowed=true`.
7. Test negative paths with spies proving that neither the model builder nor backend registry/selector was called; test positive paths only with a complete, graph-matching resolution record.
8. Run the bounded TaskFlow generation trial and independently verify generated API, frontend, tenancy, authentication, persistence, runtime behavior, and end-to-end traceability. Keep every unrun result `UNKNOWN`.

## Latest projection-contract hardening

The TaskFlowSemanticProjection contract now carries a mapping of every mandatory field to its exact reviewed value. The model must preserve that mapping in SystemModel.extensions["taskflow_semantic_values"]; the compiler rejects missing/extra fields, changed values, and a SystemModel whose requirements_ref does not match the active graph ID and content hash. Focused tests cover preservation and tampering.

This is intentionally described as **semantic-value preservation**, not proof that a backend implements those values. Carrying reviewed decisions inside the ISR prevents silent loss at the model boundary, but the actual domain/API/data/security mapping and backend consumption still need an explicit, tested projector. No concrete TaskFlow projector is being claimed by this change.

## Current disposition

- Authoritative mandatory field set and graph-bound unresolved ledger: **IMPLEMENTED, focused CI PASS (25 tests)**.\n- Semantic-resolution model and local pre-builder guard: **IMPLEMENTED, focused CI PASS (18 tests)**.
- Production pre-synthesis gate: **PARTIAL** — resolved semantics must pass an explicit projection contract that preserves exact reviewed values and graph binding. Concrete domain/API/data/security projection and the trusted provider-free ProjectCompiler path are not implemented.
- Backend-planning revalidation: **IMPLEMENTED when `ProjectCompiler(taskflow_semantic_gate=True)` is used; default mode remains generic**.
- TaskFlow generation and certification: **NOT RUN / UNKNOWN**.
- PR remains draft and unmerged.


## Downstream-consumption audit (next integration blocker)

Inspected `tiannara/domain/models/system_model.py`, `tiannara/application/intent/synthesis.py`, `tiannara/application/compiler/derivation.py`, and `tiannara/application/compiler/project_compiler.py` on the PR branch.

The current downstream boundary is narrower than the semantic projection contract:

- `SystemModel` has typed structures for capabilities, domains, services, API operations, data models, security, infrastructure, deployment, testing, and operational policies. It has no first-class typed structures for the full TaskFlow frontend state-transition contract, workspace/role permission matrix, session revocation contract, detailed request/response/error schemas, or per-capability negative-case traceability.
- The generic `synthesize_system_model()` still uses requirement-kind counts and keyword heuristics. It does not accept the TaskFlow resolution ledger; it can choose default authentication, authorization, consistency, deployment, and testing postures.
- `derive_compilation_requirements()` chooses artifact families from coarse presence checks: services cause backend/frontend/infrastructure/deployment requirements, data models cause database requirements, and a non-empty system name causes documentation requirements. It does not inspect `extensions["taskflow_semantic_values"]`, and it does not prove that a selected backend consumes individual reviewed semantics.
- Therefore, embedding the 15 reviewed values in `extensions` is useful for provenance but is not a semantic-to-artifact projection. A successful typed-model construction would still not prove that generated code implements the review.

### Required order of work

1. **Define a versioned TaskFlow semantic payload** with explicit typed shapes for each of the 15 paths. Fields whose values are not grounded in the canonical snapshot must remain unresolved until a reviewer supplies an approved decision; do not fill them from SystemModel defaults.
2. **Extend the technology-agnostic model contract** only where existing typed fields cannot express the reviewed requirement (notably role/action authorization, workspace scoping, session invalidation, API/error contracts, frontend transitions, and verification trace links). Keep these types free of implementation-stack names.
3. **Implement a deterministic projector** from the validated ledger into those typed structures. It must reject unknown keys, unsupported values, invalid references, and contradictory decisions. It must not infer unspecified relationship cardinalities, field schemas, or permission rules.
4. **Add downstream consumption contracts** so derivation/backend planning can state which typed semantics each artifact family and backend is required to implement. A backend that cannot demonstrate coverage must be ineligible, not silently selected.
5. **Add mutation/negative tests** proving that changing each reviewed semantic changes the corresponding typed model or blocks compilation, and that omitted or unsupported semantics stop before backend discovery. Then run focused CI.
6. Only after the above gates pass and a trusted reviewer envelope is available should the bounded TaskFlow generation trial run. Independently inspect generated source and execute API, frontend, authorization/tenancy, persistence, session-revocation, idempotency, and runtime checks. Keep all unexecuted claims `UNKNOWN`.

This audit is a design/implementation boundary finding, not a claim that the projector or application has been implemented. The correct current status remains **generation blocked; certification UNKNOWN**.


## Trusted-suite policy hardening (2026-10-14)

The trusted obligation suite policy now rejects configuration drift at construction:
- Consumer-binding keys must exactly equal the reviewed required-obligation ID set.
- Scenario-policy keys must exactly equal that same set.
- Required scenario IDs must be non-empty, non-blank, and unique per obligation.
- Adversarial regression tests cover extra consumer bindings and duplicate required scenarios.

This prevents stale or extra policy entries from silently coexisting with the authoritative required set. It does **not** make caller-provided obligation records authoritative, nor does it prove semantic-to-artifact consumption. CI for commit `47e965f3349e64a95ddd7fe79372639a25e36577` was queued at the time of this update; no pass is claimed until results complete.

## Remaining source-authority blocker

The live integrity gate currently receives a `TrustedObligationCertificationRequest` independently of the TaskFlow snapshot-derived `RequirementGraph` and `SemanticResolutionRecord`. Its configured suite defines required IDs, but it cannot independently prove that each record's statement, source graph identity, and semantic meaning are the canonical projection of the active TaskFlow snapshot. The current generic integrity gate also passes `CompilationResult.isr_hash` as the expected source-graph hash; that is only valid if an explicit, verified graph-to-ISR identity binding exists, which the TaskFlow path has not yet established.

Therefore the next implementation must introduce a trusted, immutable projection context carrying the canonical snapshot identity/hash, graph identity/hash, and validated semantic-resolution record into obligation projection and certification. It must derive obligation content from that context (not accept it as caller-authored truth), and certification must compare the context to the compilation source before evidence is considered. No caller-supplied hash or boolean alone may establish that binding. Until this context is integrated and tested across the live compiler path, TaskFlow generation remains blocked and certification remains UNKNOWN.
