# CONTRACT_ArtifactSet (R1-B D09)

**Contract:** `ArtifactSet`
**Status:** R1-B Deliverable D09. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** (D09 defines; stabilization is `compiler/core/repository.py:GeneratedRepository`)

**Invariants this contract satisfies:** INV-B06 (Compiler IR is distinct from generated artifacts), INV-B09 (ArtifactSet is the generated-software boundary).

---

## 1. Purpose

The `ArtifactSet` is the canonical generated-software boundary. Every generated artifact is in an `ArtifactSet`. Backends **emit**; the packager **writes**. The contract prevents backend filesystem emission from becoming an implicit architectural API.

## 2. Architecture

```text
ArtifactSet
├── files
├── directories
├── metadata
├── manifests
├── provenance
└── content hashes
```

## 3. The traceability invariant

Every generated artifact must be traceable to:

```text
Requirement
→ RequirementGraph
→ ISR
→ ArchitectureCandidate
→ CompilerIR
→ Backend
→ ArtifactSet
```

The contract enforces this by including the full lineage as part of the ArtifactSet's provenance. An ArtifactSet with missing lineage (no source Requirement reference) is rejected at construction.

## 4. Distinguishing artifact kinds

The contract explicitly distinguishes four artifact kinds. Conflating them is a frequent architectural mistake.

| Kind | Definition | Example |
|---|---|---|
| `generated artifact` | A file produced by a backend from a CompilerIR | Source code, configuration files, generated docs |
| `compiler workspace` | The compiler's internal working directory | Temporary build output, intermediate IR forms |
| `temporary build output` | A file produced during the build/test cycle | Object files, build artifacts, test reports |
| `runtime deployment artifact` | A file deployed to a runtime | Container images, deployment manifests, SBOMs |

A backend emits `generated artifact` and (optionally) `runtime deployment artifact`. The packager writes them. The compiler workspace and temporary build output are not part of the ArtifactSet; they are internal to the compiler.

## 5. Required fields

| Field | Required? | Classification |
|---|---|---|
| `artifact_set_id` (identity) | yes | **semantic** |
| `files` (file paths + content hashes) | yes | **semantic** |
| `directories` (directory structure) | yes | **semantic** |
| `metadata` (artifact kind per file, language, framework) | yes | **semantic** |
| `manifest` (full manifest: paths + hashes + metadata) | yes | **semantic** |
| `provenance` (source Requirement → ... → ArtifactSet) | yes | **semantic** (non-derivable) |
| `content_hashes` (per file + manifest hash) | yes | **derived** |
| `backend_id` + `backend_version` | yes | **semantic** |
| `compiler_ir_id` (link to D07) | yes | **semantic** |
| `architecture_candidate_id` (link to D04) | yes | **semantic** |
| `isr_revision_hash` (link to D03) | yes | **semantic** |
| `requirement_graph_id` (link to D02) | yes | **semantic** |
| Serialization (deterministic JSON) | yes | **derived** |

## 6. Identity

- **ArtifactSet ID:** content hash (SHA-256) over the manifest (file paths + content hashes + metadata).
- **Per-file content hash:** SHA-256 over the file content.
- **Manifest hash:** SHA-256 over the manifest.

## 7. Lifecycle and mutability

- **Append-only per compilation.**
- **Frozen.** An ArtifactSet is immutable once written.
- **No filesystem emission inside `compile()`.** A backend that calls `self.write_files()` (or equivalent) inside `compile()` is rejected at registration. The backend emits an `ArtifactSet`; the packager writes.

## 8. Hashing and serialization

- **Serialization:** manifest JSON (paths, hashes, metadata, provenance).
- **Hashing:** SHA-256 per file; SHA-256 over the manifest.
- **Traceability hashes:** the source hashes (Requirement → ... → ArtifactSet) are part of the provenance and are verified at construction.

## 9. Provenance

The full lineage:

```text
Requirement
→ RequirementGraph
→ ISR
→ ArchitectureCandidate
→ CompilerIR
→ Backend
→ ArtifactSet
```

Each step is referenced by content hash. The contract verifies the lineage at construction; an ArtifactSet with a broken lineage (e.g. a hash that does not match the referenced artifact) is rejected.

## 10. Failure semantics

- Incomplete manifest (missing files, hash mismatches) is rejected at construction.
- Backend-emitted filesystem writes that bypass the ArtifactSet are forbidden at registration.
- The contract distinguishes:
  - `ARTIFACT_SET_OK` — produced and verified.
  - `ARTIFACT_SET_INCOMPLETE` — missing files; rejected.
  - `ARTIFACT_SET_HASH_MISMATCH` — hash mismatch in manifest; rejected.
  - `ARTIFACT_SET_BROKEN_LINEAGE` — provenance hash mismatch; rejected.

## 11. Extension mechanism

- New artifact kinds are added by extending the manifest schema.
- New metadata fields require an ADR.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation (stabilization)

`compiler/core/repository.py:GeneratedRepository` (used by `certification/`). Gen-B backends emit via `build_repository(files_dict)` (pure emission). The canonical ArtifactSet module is created in R1-D.5 to formalize the contract.

## 13. Legacy implementations

- `constitutional_architecture/compiler/backends/fastapi_backend.py:72-86` calls `self.write_files()` inside `compile()` — **forbidden**; this is the Gen-C artifact-purity defect. Per R1-B.D17 it is LEGACY and will be **corrected or retired** in R1-E.7.
- `CompilationOutput` (Gen-A `compiler/models.py`). **LEGACY.** Retired as runtime per R1-D.5.

## 14. Migration destination

- Legacy Gen-C backend (`fastapi_backend.py`) → LEGACY classification (R1-B.D17); the `self.write_files()` inside `compile()` defect is corrected in R1-E.7 or the backend is retired.
- Legacy Gen-A `CompilationOutput` → LEGACY; retired as runtime.
- The canonical `ArtifactSet` (`compiler/core/artifactset.py` or similar) is created in R1-D.5.

---

*End of D09. Cross-references: D01 (registry), D02 (RequirementGraph), D03 (ISR), D04 (ArchitectureCandidate), D07 (CompilerIR), D08 (CompilerBackend emits), D10 (VerificationResult consumes).*
