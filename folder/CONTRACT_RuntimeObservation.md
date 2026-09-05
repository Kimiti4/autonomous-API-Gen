# CONTRACT_RuntimeObservation (R1-B D12)

**Contract:** `RuntimeObservation`
**Status:** R1-B Deliverable D12. Authoritative contract specification. **C-17 deferred** — the contract is defined in R1-B, but the implementation is out of R1 scope. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** (D12 defines; C-17 deferred)

**Invariants this contract satisfies:** INV-B12 (Runtime observations retain reverse lineage), INV-B14 (no category-specific compiler becomes a new architectural authority).

---

## 1. Purpose

`RuntimeObservation` is the **reverse path** of the canonical chain. A deployed artifact produces runtime observations; observations produce evidence; evidence feeds back into the learning and evolution systems. The contract specifies the observation surface; the implementation is **deferred to R2/R3 platform integration** per the C-17 deferral.

## 2. Architecture

```text
Deployed Artifact
       ↓
Runtime Observation
       ↓
Evidence
       ↓
Learning
       ↓
Evolution
```

## 3. The reverse lineage invariant

Runtime observations must include enough lineage to identify:

```text
deployment
→ ArtifactSet
→ CompilerIR
→ Architecture
→ ISR
→ RequirementGraph
```

The contract enforces this by including the full reverse lineage as part of the observation's provenance. An observation with missing reverse lineage cannot be attached to the evidence chain; it is rejected at construction.

## 4. What this contract does NOT do

- **This contract does not make `autonomous-api` canonical.** `autonomous-api/app/main.py:111-115` `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` is the audit-flagged observation-ISR binding gap. The contract specifies the **interface**; the implementation is out of R1 scope.
- **C-17 is deferred to R2/R3 platform integration.** The implementation of this contract, including the binding to a runtime instrumentation system, is deferred.

## 5. Required fields

| Field | Required? | Classification |
|---|---|---|
| `observation_id` (identity) | yes | **semantic** |
| `deployment_id` (which deployment produced this observation) | yes | **semantic** |
| `artifact_set_id` (link to D09) | yes | **semantic** |
| `compiler_ir_id` (link to D07) | yes | **semantic** |
| `architecture_candidate_id` (link to D04) | yes | **semantic** |
| `isr_revision_hash` (link to D03) | yes | **semantic** |
| `requirement_graph_id` (link to D02) | yes | **semantic** |
| `runtime_identity` (which runtime produced this observation) | yes | **semantic** |
| `observation_kind` (e.g. metric, log, error, trace) | yes | **semantic** |
| `observation_payload` (the observation data) | yes | **semantic** |
| `provenance` (full reverse lineage) | yes | **semantic** (non-derivable) |
| `timestamp` | yes | **observational metadata** |
| `serialization` (deterministic JSON) | yes | **derived** |
| `content_hash` (SHA-256) | yes | **derived** |

## 6. Identity

- **Observation ID:** UUIDv5 over deployment + artifact + timestamp.
- **Content hash:** SHA-256 over canonical serialization.

## 7. Lifecycle and mutability

- **Append-only.** Observations are never modified or deleted.
- **Frozen.** Each observation is immutable once written.

## 8. Hashing and serialization

- **Serialization:** deterministic JSON with reverse-lineage fields.
- **Hashing:** SHA-256 over canonical serialization. The hash is the observation's identity.

## 9. Provenance

The full reverse lineage:

```text
deployment
→ ArtifactSet
→ CompilerIR
→ Architecture
→ ISR
→ RequirementGraph
```

Each step is referenced by content hash. The contract verifies the lineage at construction; an observation with a broken lineage (e.g. a hash that does not match the referenced artifact) is rejected.

## 10. Failure semantics

- An observation with missing reverse lineage is rejected (`RuntimeObservationBrokenLineage`).
- An observation that cannot be attached to the evidence chain is rejected.
- The contract distinguishes:
  - `OBSERVATION_OK` — produced and verified.
  - `OBSERVATION_BROKEN_LINEAGE` — provenance hash mismatch; rejected.
  - `OBSERVATION_INDETERMINATE` — runtime could not produce a deterministic observation; reason recorded.

## 11. Extension mechanism

- New observation kinds (e.g. custom metric types) are added by extending the schema.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation

**None in the canonical runtime.** `autonomous-api/app/observation/{gateway,sequences,projectors}.py` exists but is **LEGACY** (C-17 deferred). The campaign runtime does not depend on `autonomous-api/`.

## 13. Legacy implementations

- `autonomous-api/app/observation/{gateway,sequences,projectors}.py` — LEGACY. Retired as runtime per R1-D.5; C-17 deferred to R2/R3.
- `autonomous-api/app/main.py:111-115` `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` — the audit-flagged observation-ISR binding gap. **C-17 deferred.**

## 14. Migration destination

- Legacy `autonomous-api/app/observation/` → LEGACY classification (R1-B.D17); implementation deferred to R2/R3 platform integration.
- The canonical `RuntimeObservation` is defined in D12 (this document); the implementation is out of R1 scope.

---

*End of D12. Cross-references: D01 (registry), D02 (RequirementGraph), D03 (ISR), D04 (ArchitectureCandidate), D07 (CompilerIR), D09 (ArtifactSet), C-17 (deferred to R2/R3).*
