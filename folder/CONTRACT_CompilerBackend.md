# CONTRACT_CompilerBackend (R1-B D08)

**Contract:** `CompilerBackend`
**Status:** R1-B Deliverable D08. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `compiler/core/protocol.py`

**Invariants this contract satisfies:** INV-B08 (Backend cannot redefine upstream semantics), INV-B14 (no category-specific compiler becomes a new architectural authority).

---

## 1. Purpose

The `CompilerBackend` is the canonical backend protocol. It consumes a `CompilerIR` (D07) and produces an `ArtifactSet` (D09). The backend is the **lowering boundary** between the canonical compiler and the technology-specific implementation.

## 2. Architecture

```text
CompilerIR
     ↓
CompilerBackend
     ↓
ArtifactSet
```

## 3. What a backend MUST NOT do

- Redefine ISR semantics.
- Modify the RequirementGraph.
- Own architecture evolution.
- Become a verification authority.
- Directly mutate certification state.
- Silently write arbitrary files outside `ArtifactSet` semantics.

The contract enforces these as failure conditions: a backend that performs any of the above is rejected at registration.

## 4. Required fields

| Field | Required? | Classification |
|---|---|---|
| Backend identity (backend_id + version) | yes | **semantic** |
| Supported target (technology + framework + version) | yes | **semantic** |
| Capabilities (what the backend can lower) | yes | **semantic** |
| Supported IR version (which CompilerIR version this backend accepts) | yes | **semantic** |
| Artifact format (what the backend produces) | yes | **semantic** |
| Determinism properties (deterministic, requires seed, etc.) | yes | **semantic** |
| Required tools (e.g. language compiler, build tool) | yes | **semantic** |
| Verification capabilities (does this backend support verification?) | yes | **semantic** |
| Deployment capabilities (does this backend produce deployment artifacts?) | yes | **semantic** |
| Security capabilities (does this backend produce security-policy artifacts?) | yes | **semantic** |
| Input contract (CompilerIR version + required fields) | yes | **semantic** |
| Output contract (ArtifactSet version + required fields) | yes | **semantic** |
| Lowering responsibility (what the backend lowers and how) | yes | **semantic** |
| Deterministic behavior (output is reproducible) | yes | **semantic** |
| Errors (typed error kinds) | yes | **semantic** |
| Unsupported capability behavior (e.g. `UNSUPPORTED_CAPABILITY` outcome) | yes | **semantic** |
| Versioning (backend version) | yes | **semantic** |

## 5. Lifecycle and mutability

- **Versioned.** Multiple versions may coexist temporarily (e.g. `python-fastapi@1.4.0` and `python-fastapi@1.5.0`).
- **Frozen protocol.** The protocol surface is frozen; backend implementations evolve; the protocol does not.

## 6. Identity

- **Backend identity:** `backend_id` + version (e.g. `python-fastapi@1.4.0`).
- **Manifest hash:** SHA-256 over the manifest (capabilities, supported target, supported IR version, etc.).

## 7. Hashing and serialization

- **Serialization:** manifest JSON (capabilities, supported target, supported IR version, etc.).
- **Hashing:** SHA-256 over the manifest. The manifest hash is the backend identity.

## 8. Provenance

- Backend implementer.
- Version.
- Commit hash.
- Tool versions (e.g. language compiler, build tool).

## 9. Failure semantics

The contract distinguishes:

- `COMPILATION_OK` — produced the expected `ArtifactSet`.
- `UNSUPPORTED_CAPABILITY` — the backend was asked to lower a capability it does not support. **This is an explicit outcome, not a successful compilation.**
- `COMPILATION_FAILED` — lowering failed; no `ArtifactSet` produced; reason recorded.
- `COMPILATION_BLOCKED` — a precondition (e.g. IR validation) was not met; no output produced.
- `COMPILATION_INDETERMINATE` — the backend could not determine the output deterministically; reason recorded.

## 10. Extension mechanism

- New backends are added by implementing the protocol.
- The protocol surface is frozen; extensions are versioned.

## 11. Current implementation

`compiler/core/protocol.py:CompilerBackend` (Protocol with `name, language, framework, version, backend_class, identity(), test_spec(), element_paths(plan), compile(plan), conformance(plan, repo)`). The current implementation is the canonical protocol; this contract freezes its API and adds the D08 requirements (capabilities, supported IR version, errors, unsupported-capability behavior, etc.).

## 12. Legacy implementations

- `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` (Gen-C). **LEGACY.** Retired as runtime per R1-D.5.
- `compiler/sdk/base.py:CompilerBackendBase` (Gen-A). **LEGACY.** Retired as runtime per R1-D.5.
- `constitutional_architecture/compilers/backend/base.py:BackendCompiler` (per-category, 9 sub-categories: backend, database, deployment, documentation, frontend, infrastructure, operational, runtime_policy, testing). **LEGACY.** Retired as runtime per R1-D.5. **INV-B14**: no category-specific compiler becomes a new architectural authority.

## 13. Migration destination

- Legacy Gen-C, Gen-A, and per-category backend protocols → LEGACY classification (R1-B.D17); canonical protocol retains the Gen-B shape with the D08 additions.
- The canonical `CompilerBackend` Protocol (`compiler/core/protocol.py`) is preserved.

---

*End of D08. Cross-references: D01 (registry), D07 (CompilerIR is the input), D09 (ArtifactSet is the output).*
