# CONTRACT_EvolutionRecord_EIR (R1-B D06)

**Contract:** `EvolutionRecord` / `EIR`
**Status:** R1-B Deliverable D06. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `evolution/core`

**Invariants this contract satisfies:** INV-B04 (Architecture Model is distinct from ISR), INV-B07 (Evolution does not depend on backend technology).

---

## 1. Purpose

The `EvolutionRecord` (also called EIR — Evolution Intermediate Representation) is the **record of what happened** when an `EvolutionOperation` executed. It is the lineage record of the evolution engine. The record separates **what was done** (D05 EvolutionOperation) from **what happened as a result** (D06 EvolutionRecord).

## 2. Distinction

```text
EvolutionOperation   (D05; the operation itself)
        ↓ executes
EvolutionRecord/EIR  (this contract; the record of what happened)
```

## 3. Required fields (the audit's required fields, made canonical)

The audit required the following fields for EIR. All are now part of the canonical contract.

| Field | Required? | Classification |
|---|---|---|
| `record_id` (record identity) | yes | **semantic** |
| `transformation_id` (per transformation, if multiple) | yes (for compound operations) | **semantic** |
| `operation_id` (link to D05) | yes | **semantic** (lineage) |
| `source_isr` (content hash of the source ISR revision) | yes | **semantic** |
| `target_isr` (content hash of the target ISR revision, if changed) | yes (when ISR changes) | **semantic** |
| `operator` (operator type from D05) | yes | **semantic** |
| `target_semantic_path` (which semantic path was changed) | yes (for mutations) | **semantic** |
| `old_value`, `new_value` (per transformation) | yes (for mutations) | **semantic** |
| `reason` (why this transformation was chosen) | yes | **semantic** |
| `strategy` (mutation strategy) | yes | **semantic** |
| `parent_architecture` (parent candidate ID) | yes | **semantic** (lineage) |
| `child_architecture` (child candidate ID) | yes (when produced) | **semantic** (lineage) |
| `timestamp` | yes | **observational metadata** |
| `evolution_run_id` | yes | **observational metadata** |
| `evidence_refs` (references to evidence records) | optional | **observational metadata** |
| `status` (OPERATION_OK / FAILED / BLOCKED / INDETERMINATE) | yes | **semantic** |
| `failure_information` | when status is not OPERATION_OK | **semantic** |
| `parent_candidate_ids` (input candidate IDs from D05) | yes | **semantic** |
| `resulting_candidate_ids` (output candidate IDs) | yes (when produced) | **semantic** |
| `parameters` (operator-specific parameters) | yes | **semantic** |
| `seed` (randomness seed) | yes (when stochastic) | **semantic** |
| `evaluation_results` (if evaluation was part of the operation) | optional | **semantic** |

## 4. Identity

- **Record ID:** content hash (SHA-256) over the canonical serialization of the record.
- **transformation_id:** for compound operations, each transformation has its own ID (UUIDv5 over the transformation's fields).

## 5. Lifecycle and mutability

- **Append-only.** Records are never modified or deleted.
- **Frozen.** Each record is immutable once written.

## 6. The `transformations=[]` defect is repaired

`constitutional_architecture/engine/evolution_loop.py:107-114` constructs an EIR with `transformations=[]` despite the engine having performed mutations. This is a critical defect. Per the contract:

- A record with `status=OPERATION_OK` and an empty `transformations` list is **forbidden** unless the operation was genuinely a no-op.
- The contract enforces this: the evolution engine must populate `transformations` with the actual semantic transformations performed.
- The defect is repaired in R1-D.3 (or the Substrate B path is retired per R1-D.5).

## 7. Field classification (summary)

| Field | Classification |
|---|---|
| All lineage, semantic, identity, status fields | **semantic** |
| Serialization, hashing | **derived** |
| Timestamp, evolution_run_id, evidence_refs | **observational metadata** |

## 8. Hashing and serialization

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization. The hash is the record's identity.

## 9. Provenance

- The record carries the operation's provenance (operator type, parent IDs, seed, timestamp, run ID).
- Evidence references link to verification/certification records (D10, D11).

## 10. Failure semantics

- A failed operation produces a record with `status=OPERATION_FAILED` and `failure_information` populated; the record is **not silently dropped**.
- The contract distinguishes:
  - `OPERATION_OK` — operation completed; transformations and result IDs are populated.
  - `OPERATION_FAILED` — operation failed; no output produced; `failure_information` populated.
  - `OPERATION_BLOCKED` — a precondition was not met; no output produced; reason recorded.
  - `OPERATION_INDETERMINATE` — operator could not determine output deterministically; reason recorded.

## 11. Extension mechanism

- New record fields require an ADR; do not add them via the contract surface.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation

`evolution/core/lineage` (in-memory lineage). The canonical `EvolutionRecord` will be formalized in R1-D.3 as a new `evolution/core/record.py` with the required fields above.

## 13. Legacy implementations

- `constitutional_architecture/eir/transformation.py:EIR` (TransformationClass, Transformation, EIR dataclasses at lines 37-77). **LEGACY.** The missing fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`) are added in the canonical EvolutionRecord (R1-D.3) per the audit's requirement. Retired as runtime per R1-D.5 with LEGACY classification per R1-B.D17.
- The defect at `constitutional_architecture/engine/evolution_loop.py:107-114` (`transformations=[]`) is repaired in R1-D.3 or the path is retired.

## 14. Migration destination

- Legacy `constitutional_architecture/eir/transformation.py:EIR` → LEGACY classification (R1-B.D17); useful schema fields selectively absorbed into `evolution/core/record.py` in R1-D.3.
- The canonical EvolutionRecord (`evolution/core/record.py`) is created in R1-D.3.

---

*End of D06. Cross-references: D01 (registry), D03 (ISR), D04 (ArchitectureCandidate), D05 (EvolutionOperation).*
