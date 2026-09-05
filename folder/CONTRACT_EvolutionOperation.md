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
