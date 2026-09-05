# CONTRACT_EvolutionOperation (R1-B D05)

**Contract:** `EvolutionOperation`
**Status:** R1-B Deliverable D05. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `evolution/core`

**Invariants this contract satisfies:** INV-B07 (Evolution does not depend on backend technology).

---

## 1. Purpose

An `EvolutionOperation` is a single operation that produces a new `ArchitectureCandidate` from one or more parent candidates. The contract defines the **operation surface** (mutation, crossover, recombination, selection, evaluation) without hardcoding unnecessary operators into the constitutional contract.

## 2. Distinction

```text
EvolutionOperation   (this contract; the operation itself)
        ↓ executes
EvolutionRecord/EIR  (D06; the record of what happened)
```

The contract separates **what was done** (D05) from **what happened as a result** (D06).

## 3. Operator types (frozen taxonomy)

The following operator types are part of the contract surface. New operator types require an ADR.

| Operator | Input | Output | Notes |
|---|---|---|---|
| `mutation` | 1 candidate | 1 candidate | Mutates the candidate per parameters. |
| `crossover` | 2+ candidates | 1 candidate | Combines architectural material from parents. The real crossover in `evolution/core/operations.py:74-104` (RNG-pick per gene with 50/50) is preserved. |
| `recombination` | 2+ candidates | 1+ candidates | Generalization of crossover; operator-specific. |
| `selection` | population | 1+ candidates (selected) | No new candidate is produced by selection alone. |
| `evaluation` | 1 candidate | 1 candidate (with evaluation metadata) | Does not change the candidate's architecture; adds evaluation metadata. |

## 4. Required fields

| Field | Required? | Classification |
|---|---|---|
| Operation ID | yes | **semantic** (identity) |
| Operator type | yes | **semantic** |
| Input candidate ID(s) | yes | **semantic** (lineage) |
| Output candidate ID(s) | yes (for mutation/crossover/recombination) | **semantic** |
| Parameters | yes (operator-specific) | **semantic** |
| Deterministic / randomness metadata (seed) | yes | **semantic** |
| Parentage (input candidate IDs) | yes | **semantic** |
| Provenance (operator, timestamp, run ID) | yes | **observational metadata** |
| Preconditions | yes | **semantic** |
| Postconditions | yes | **semantic** |
| Failure semantics | yes | **semantic** |

## 5. Identity

- **Operation ID:** UUIDv5 over operator type + parameters + timestamp.
- The operation is **stateless**; one execution = one identity.

## 6. Lifecycle and mutability

- **Frozen per execution.** Parameters are immutable.
- **Stateless.** A re-execution of the same operation with the same parameters and seed produces the same output (deterministic).

## 7. Real crossover is preserved

The existing genuine crossover in `evolution/core/operations.py:74-104` is the canonical crossover implementation. It is preserved by this contract. Substrate B's pseudo-crossover (which copied parent A) is **not** canonical and is retired per R1-D.5.

## 8. Field classification (summary)

| Field | Classification |
|---|---|
| Operation ID | **semantic** |
| Operator type | **semantic** |
| Input/output candidate IDs | **semantic** |
| Parameters | **semantic** |
| Deterministic / randomness (seed) | **semantic** |
| Provenance | **observational metadata** |
| Pre/postconditions | **semantic** |
| Failure semantics | **semantic** |

## 9. Hashing and serialization

- **Serialization:** deterministic JSON over operator type, input candidate IDs, parameters, seed.
- **Hashing:** SHA-256 over canonical serialization.

## 10. Provenance

- Operator type, parent candidate IDs, randomness seed, timestamp, evolution run ID.

## 11. Failure semantics

- Operation failure produces a failure record (D06 EvolutionRecord) and does not produce a candidate.
- The failure reason is recorded; the operation is not silently retried without explicit authorization.
- The contract distinguishes:
  - `OPERATION_OK` — produced the expected output(s).
  - `OPERATION_FAILED` — operation itself failed; no output produced.
  - `OPERATION_BLOCKED` — a precondition was not met; no output produced.
  - `OPERATION_INDETERMINATE` — the operator could not determine the output deterministically (e.g. RNG source failure).

## 12. Extension mechanism

- New operator types require an ADR; do not add them via the contract surface.
- New parameter schemas for an existing operator are versioned.
- The contract surface is frozen; extensions are versioned.

## 13. Current implementation

`evolution/core/operations.py:74-104` (real crossover verified in R0). Mutation, crossover, recombination, selection, evaluation all exist in `evolution/core/operations.py` and related modules. The current implementation is the canonical implementation; this contract freezes its API.

## 14. Legacy implementations

- `constitutional_architecture/engine/mutation_*.py` (6 mutation operator files). **LEGACY.** Retired as runtime per R1-D.5.
- `constitutional_architecture/engine/crossover_engine.py`. **LEGACY.** Retired as runtime per R1-D.5 (Substrate B's crossover is pseudo-crossover; the canonical crossover is in `evolution/core/operations.py`).

## 15. Migration destination

- Legacy Substrate B mutation/crossover operators → LEGACY classification (R1-B.D17); selectively migrated to `evolution/core/operations.py` only if they add genuinely new operator kinds.
- The canonical EvolutionOperation (`evolution/core/operations.py`) is preserved.

---

*End of D05. Cross-references: D01 (registry), D03 (ISR), D04 (ArchitectureCandidate), D06 (EvolutionRecord).*

---

# Part II: R1-D.3 D3-04 refinement

**Refinement authority:** R1-D.3 master prompt. The D3-03 semantic comparison identified MIGRATE actions for D05. This refinement extends D05 Part I with the missing fields. The original D05 is unchanged.

## 16. Refined fields (D3-04)

### 16.1 Verification relationship (added)

| Field | Required? | Classification |
|---|---|---|
| `verification_relationship: list[str]` (VerificationResult IDs) | yes (for operations that produce verifiable candidates) | **semantic** (cross-contract; D14) |

The EvolutionOperation references the VerificationResult(s) that establish the candidate's verification status. This is the cross-contract link (D14) between Evolution and Verification.

### 16.2 Environment (added)

| Field | Required? | Classification |
|---|---|---|
| `environment: dict[str, str]` (e.g., engine version, toolchain, OS) | yes | **observational metadata** |

### 16.3 Actor/origin (added)

| Field | Required? | Classification |
|---|---|---|
| `actor: str` (e.g., "evolution_engine", "agent:architect") | yes | **observational metadata** |

## 17. Constitutional `transformations=[]` defect (R1-D.3 finding)

**The constitutional EIR at `constitutional_architecture/engine/evolution_loop.py:107-114` constructs an EIR with `transformations=[]` despite the engine having performed mutations.** This violates the D06 contract INV-B04 (the audit-required fields must be populated for `OPERATION_OK`). The R1-D.3 fix is to populate `transformations` from the actual mutations performed. The canonical contract is **not** changed by this defect; the constitutional implementation is.

## 18. Cross-references

- D3-01: `folder/R1_D3_EVOLUTION_INVENTORY.md`
- D3-02: `folder/R1_D3_EVOLUTION_EXECUTION_GRAPH.md`
- D3-03: `folder/R1_D3_EVOLUTION_SEMANTIC_COMPARISON.md`
- D06 (R1-B Part I + D3-05 Part II): `folder/CONTRACT_EvolutionRecord_EIR.md`
- D3-05: `folder/R1_D3_EVOLUTION_MIGRATION_MAP.md` (next)

---

*End of Part II. The D05 contract is refined with `verification_relationship`, `environment`, and `actor` fields. The constitutional `transformations=[]` defect is documented. The canonical EvolutionOperation is preserved.*
