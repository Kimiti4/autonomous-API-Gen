# TaskFlow Semantic Gate Integration Findings

**Status:** INTEGRATION BLOCKED — the fail-closed primitive exists, but it is not yet a production compiler gate.

## What was inspected

- `experiments/taskflow-native/provider_free/native_adapter.py`
- `experiments/taskflow-native/provider_free/typed_isr_gate.py`
- `experiments/taskflow-native/README.md` and `evaluate.py`
- `constitutional_architecture/compiler/pipeline.py`
- `constitutional_architecture/compiler/backends/backend_selector.py`
- `constitutional_architecture/compiler/passes/validation_pass.py`
- `compiler/kernel.py`

## Verified boundaries

1. The provider-free native adapter builds a deterministic `RequirementGraph`, preserves source traceability, and currently returns `system_model=None`, `typed_isr=None`, and `generation_allowed=False`. It does not invoke a live model builder or select a backend.
2. `build_taskflow_typed_isr()` validates a graph-bound `SemanticResolutionRecord` before invoking its supplied SystemModel builder callback. This proves a local transition boundary only; callers can bypass the helper.
3. The repository contains more than one compiler path. The constitutional pipeline consumes `constitutional_architecture.isr.model.isr.ISR`; the universal compiler consumes a `CompilationRequest` and validates its ISR payload before backend lookup. Neither currently receives the TaskFlow `RequirementGraph` plus its graph-bound semantic-resolution ledger.
4. The constitutional validation pass currently catches exceptions and reports the ISR as valid in degraded mode. That behavior is not a substitute for a mandatory semantic gate and must not be treated as evidence that the TaskFlow gate is integrated.
5. The native trial's own README describes a genuine run as requiring a configured reasoning provider. No provider-free generation or application certification is claimed here.

## Why direct wiring is unsafe right now

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

## Current disposition

- Semantic-resolution model and local pre-builder guard: **IMPLEMENTED, CI UNKNOWN**.
- Production orchestration integration: **NOT IMPLEMENTED**.
- Backend-selection enforcement: **NOT IMPLEMENTED**.
- TaskFlow generation and certification: **NOT RUN / UNKNOWN**.
- PR remains draft and unmerged.
