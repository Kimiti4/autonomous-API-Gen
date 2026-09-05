# CONTRACT_State_FailureSemantics (R1-B D14)

**Contract:** `State Machine & Failure Semantics`
**Status:** R1-B Deliverable D14. Authoritative common state/error model. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Authority:** R1-B D02–D12 (per-contract specifications) and D13 (cross-contract identity & provenance).

**Invariants this contract satisfies:** INV-B10 (Verification cannot fail open), INV-B11 (Certification cannot manufacture verification evidence), INV-B13 (Historical evidence is immutable), and the universal failure-semantics discipline (Validation failure ≠ warning; Verification exception ≠ success; Unsupported backend capability ≠ successful compilation).

---

## 1. Purpose

The state machine and failure-semantics model defines a **common discipline** for what failure, indeterminate, blocked, and invalid mean across all 11 canonical contracts. The discipline prevents the exact fail-open patterns the audit discovered: a verification exception becoming a successful verification result, an unsupported backend capability becoming a successful compilation, a validation failure becoming a warning.

## 2. The universal verification state model (D10)

The 5-state model is canonical for the **verification** contract (D10) and is the reference for cross-contract state mapping:

| State | Meaning |
|---|---|
| `PASS` | Verifier ran successfully; checks passed. |
| `FAIL` | Verifier ran successfully; checks failed. |
| `INDETERMINATE` | Verifier could not determine the result (e.g. internal exception, missing evidence, downstream `UNSUPPORTED_CAPABILITY`). |
| `NOT_RUN` | Verifier did not run (e.g. blocked by a precondition). |
| `BLOCKED` | A prerequisite (e.g. compilation, signature) was not met. |

**Mandatory invariant:** an internal verifier exception produces `INDETERMINATE`, not `PASS`. **A `PASS` outcome cannot be reached when the verifier's input is missing, broken, or unsupported.** This is INV-B10.

## 3. Per-contract state vocabularies

Different contracts have different state vocabularies. The contract surface is **heterogeneous by design**: each contract has its own state kinds that reflect its own failure modes. The universal verification state model (D10) is the **reference**; other contracts have their own states that are consistent with the universal discipline.

| Contract | State vocabulary | Notes |
|---|---|---|
| EvolutionOperation (D05) | `OPERATION_OK`, `OPERATION_FAILED`, `OPERATION_BLOCKED`, `OPERATION_INDETERMINATE` | Operation-level (not verification-level) |
| EvolutionRecord (D06) | `OPERATION_OK`, `OPERATION_FAILED`, `OPERATION_BLOCKED`, `OPERATION_INDETERMINATE` | Mirrors D05 (a record's status mirrors the operation's outcome) |
| CompilerIR lowering (D07) | `LOWERING_OK`, `LOWERING_FAILED`, `LOWERING_BLOCKED`, `LOWERING_INDETERMINATE` | Lowering-level |
| CompilerBackend (D08) | `COMPILATION_OK`, `UNSUPPORTED_CAPABILITY`, `COMPILATION_FAILED`, `COMPILATION_BLOCKED`, `COMPILATION_INDETERMINATE` | Backend-level; `UNSUPPORTED_CAPABILITY` is an explicit outcome, not a success |
| ArtifactSet (D09) | `ARTIFACT_SET_OK`, `ARTIFACT_SET_INCOMPLETE`, `ARTIFACT_SET_HASH_MISMATCH`, `ARTIFACT_SET_BROKEN_LINEAGE` | Artifact-set-level; construction-only |
| VerificationResult (D10) | `PASS`, `FAIL`, `INDETERMINATE`, `NOT_RUN`, `BLOCKED` | **The universal verification state model** |
| CertificationEvidence (D11) | `CERTIFIED`, `NOT_CERTIFIED`, `BLOCKED`, `INDETERMINATE` | Certification-level; derived from D10 |
| RuntimeObservation (D12) | `OBSERVATION_OK`, `OBSERVATION_BROKEN_LINEAGE`, `OBSERVATION_INDETERMINATE` | Observation-level |

## 4. Cross-contract state mapping

The D10 verification state is the **canonical** state for the certification gate. Other contracts' states map to D10 as follows:

| Upstream state | Maps to D10 state | Rationale |
|---|---|---|
| `EvolutionOperation.OPERATION_OK` | (no mapping; operation does not directly produce verification) | Operations are inputs to D07 lowering. |
| `EvolutionOperation.OPERATION_FAILED` | (no mapping) | A failed operation produces no candidate, so the chain is broken. |
| `CompilerIR.LOWERING_OK` | (prerequisite for verifier to run; does not by itself produce a verification result) | The verifier runs over the IR + artifact; lowering OK means the chain is intact. |
| `CompilerIR.LOWERING_FAILED` | `NOT_RUN` | The verifier did not run because lowering failed. |
| `CompilerIR.LOWERING_BLOCKED` | `BLOCKED` | A prerequisite was not met. |
| `CompilerBackend.COMPILATION_OK` | (prerequisite for verifier to run) | The backend produced an ArtifactSet. |
| `CompilerBackend.UNSUPPORTED_CAPABILITY` | `INDETERMINATE` | The backend was asked to lower a capability it does not support. The verifier cannot determine pass/fail. **Unsupported capability is not a successful compilation.** |
| `CompilerBackend.COMPILATION_FAILED` | `NOT_RUN` | The verifier did not run. |
| `CompilerBackend.COMPILATION_BLOCKED` | `BLOCKED` | A prerequisite was not met. |
| `CompilerBackend.COMPILATION_INDETERMINATE` | `INDETERMINATE` | |
| `ArtifactSet.ARTIFACT_SET_OK` | (prerequisite for verifier to run) | The artifact is complete and traceable. |
| `ArtifactSet.ARTIFACT_SET_INCOMPLETE` | `NOT_RUN` | The verifier did not run. |
| `ArtifactSet.ARTIFACT_SET_HASH_MISMATCH` | `INDETERMINATE` | Hash mismatch — cannot verify. |
| `ArtifactSet.ARTIFACT_SET_BROKEN_LINEAGE` | `INDETERMINATE` | Lineage broken — cannot verify. |
| `RuntimeObservation.OBSERVATION_OK` | (downstream; feeds back to evolution) | Observations feed back; they do not directly determine verification. |
| `RuntimeObservation.OBSERVATION_BROKEN_LINEAGE` | (the observation is rejected at construction; no downstream effect) | |
| `RuntimeObservation.OBSERVATION_INDETERMINATE` | (the observation is recorded; downstream may or may not use it) | |

**Key cross-contract decision (D14):** `UNSUPPORTED_CAPABILITY` at the backend level maps to `INDETERMINATE` at the verification level, not `PASS` and not `FAIL`. The verifier cannot determine pass/fail when the backend did not produce an ArtifactSet for a requested capability. **This is the explicit answer to the audit's "unsupported backend capability ≠ successful compilation" requirement.**

## 5. Certification state derivation

The D11 CertificationEvidence state is derived from the D10 verification state:

| D10 state | D11 state | Rationale |
|---|---|---|
| `PASS` | `CERTIFIED` (subject to campaign-level rules) | Verification passed; certifier can certify. |
| `FAIL` | `NOT_CERTIFIED` | Verification failed. |
| `INDETERMINATE` | `INDETERMINATE` | Verification indeterminate; certifier cannot certify. **The certifier cannot manufacture evidence.** INV-B11. |
| `NOT_RUN` | `BLOCKED` | Verifier did not run. |
| `BLOCKED` | `BLOCKED` | A prerequisite was not met. |

**Key cross-contract decision (D14):** a D10 state of `INDETERMINATE` produces a D11 state of `INDETERMINATE`, not `CERTIFIED`. The certifier cannot manufacture evidence. This is INV-B11.

## 6. Universal failure-semantics discipline

The following are **universal** across all 11 contracts and are enforced as failure conditions:

| Discipline | Enforcement |
|---|---|
| Validation failure ≠ warning | A validator that catches an exception and returns success is rejected at registration. |
| Verification exception ≠ success | A verifier that catches an internal exception and returns `PASS` is rejected at registration. The correct outcome is `INDETERMINATE`. |
| Unsupported backend capability ≠ successful compilation | A backend that returns `COMPILATION_OK` for an unsupported capability is rejected at registration. The correct outcome is `UNSUPPORTED_CAPABILITY`. |
| Missing evidence ≠ certified | A certifier that produces `CERTIFIED` without a corresponding `PASS` `VerificationResult` is rejected at construction. |
| Broken lineage ≠ valid | A contract with a broken parent reference is rejected at construction. |
| Historical evidence is immutable | The B3-v2 evidence chain is preserved unchanged. R1-B does not alter it. |
| No bidirectional adapters | Adapters are always `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY` (INV-B15). |
| No silent retry | An operation that fails is not silently retried without explicit authorization. |

## 7. State machine diagrams

### 7.1 Verification (D10)

```text
[INIT]
  ↓
verifier runs
  ↓
  ├─→ all checks pass        → PASS
  ├─→ any check fails        → FAIL
  ├─→ internal exception     → INDETERMINATE  (mandatory)
  ├─→ missing evidence       → INDETERMINATE
  ├─→ downstream UNSUPPORTED → INDETERMINATE
  ├─→ verifier did not run   → NOT_RUN
  └─→ prerequisite not met   → BLOCKED
```

### 7.2 Certification (D11)

```text
[INIT]
  ↓
consume VerificationResult
  ↓
  ├─→ PASS        → CERTIFIED
  ├─→ FAIL        → NOT_CERTIFIED
  ├─→ INDETERMINATE → INDETERMINATE
  ├─→ NOT_RUN     → BLOCKED
  └─→ BLOCKED     → BLOCKED
```

### 7.3 Backend compilation (D08)

```text
[INIT]
  ↓
backend lowers CompilerIR
  ↓
  ├─→ produces valid ArtifactSet → COMPILATION_OK
  ├─→ capability not supported  → UNSUPPORTED_CAPABILITY
  ├─→ lowering error            → COMPILATION_FAILED
  ├─→ prerequisite not met      → COMPILATION_BLOCKED
  └─→ cannot determine          → COMPILATION_INDETERMINATE
```

### 7.4 Evolution operation (D05)

```text
[INIT]
  ↓
operator executes
  ↓
  ├─→ produces expected output(s) → OPERATION_OK
  ├─→ operator itself failed     → OPERATION_FAILED
  ├─→ precondition not met       → OPERATION_BLOCKED
  └─→ cannot determine           → OPERATION_INDETERMINATE
```

## 8. Field classification

| Field | Classification |
|---|---|
| State values, state transitions, mapping rules | **semantic** (define the contract's correctness) |
| Failure reasons, indeterminate reasons | **semantic** |
| Timestamps | **observational metadata** |

## 9. Extension mechanism

- New states for a contract require an ADR.
- New cross-contract state mappings require an ADR.
- The state machine is frozen; extensions are versioned.

## 10. Cross-references

- D10: VerificationResult (the universal verification state model).
- D05, D06, D07, D08, D09, D11, D12: per-contract state vocabularies.
- D13: cross-contract identity and provenance.
- D20: R1-B gate report (the gate evaluates whether the state machine is consistent).

---

*End of D14. The state machine and failure-semantics model is the common discipline that prevents the audit's fail-open patterns. The 5-state verification model is the reference; other contracts have their own state vocabularies that map consistently to it.*
