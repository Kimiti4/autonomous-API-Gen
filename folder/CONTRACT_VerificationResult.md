# CONTRACT_VerificationResult (R1-B D10)

**Contract:** `VerificationResult`
**Status:** R1-B Deliverable D10. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** (D10 defines; stabilization is `certification/stages/`)

**Invariants this contract satisfies:** INV-B10 (Verification cannot fail open), INV-B19 (negative cases fail correctly).

---

## 1. Purpose

The `VerificationResult` defines verification as an **evidence-producing subsystem**, not merely a boolean. The contract establishes the mandatory state model and the failure semantics. **An internal verifier exception must never silently become a successful verification result.**

## 2. Architecture

```text
ArtifactSet (D09)
   ↓
Verification
   ↓
VerificationResult
   ↓
CertificationEvidence (D11)
```

## 3. Mandatory state model

The contract defines exactly five states. **All five are required; none is optional.**

| State | Meaning | Result equivalent |
|---|---|---|
| `PASS` | Verifier ran successfully; checks passed | `True` |
| `FAIL` | Verifier ran successfully; checks failed | `False` |
| `INDETERMINATE` | Verifier could not determine the result (e.g. internal exception, missing evidence) | **NOT** `True`, **NOT** `False` |
| `NOT_RUN` | Verifier did not run (e.g. blocked by a precondition) | `None` |
| `BLOCKED` | A prerequisite (e.g. compilation, signature) was not met | `None` |

### The mandatory invariant

> **An internal verifier exception must never silently become a successful verification result.**

A verifier that catches an internal exception and returns `PASS` (or any state that the certifier interprets as success) is rejected at registration. The correct outcome is `INDETERMINATE` with `indeterminate_reason` populated.

## 4. Required fields

| Field | Required? | Classification |
|---|---|---|
| `verification_id` (identity) | yes | **semantic** |
| `subject_artifact_id` (link to D09 ArtifactSet) | yes | **semantic** |
| `subject_ir_id` (link to D07 CompilerIR) | yes | **semantic** |
| `verifier_id` (which verifier ran) | yes | **semantic** |
| `verifier_version` | yes | **semantic** |
| `checks_performed` (list of checks) | yes | **semantic** |
| `evidence_refs` (references to evidence records) | yes | **semantic** |
| `result` (PASS / FAIL / INDETERMINATE / NOT_RUN / BLOCKED) | yes | **semantic** |
| `failure_reason` (when result is FAIL) | when applicable | **semantic** |
| `indeterminate_reason` (when result is INDETERMINATE) | when applicable | **semantic** |
| `provenance` (subject identity, verifier identity/version, evidence references) | yes | **semantic** |
| `timestamps` (start, end) | yes | **observational metadata** |
| `deterministic_identity` (where applicable) | optional | **semantic** |

## 5. Identity

- **Verification ID:** UUIDv5 over subject + verifier + timestamp.
- **Content hash:** SHA-256 over canonical serialization.

## 6. Lifecycle and mutability

- **Append-only.** VerificationResults are never modified or deleted.
- **Frozen.** Each VerificationResult is immutable once written.

## 7. Hashing and serialization

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization.

## 8. Provenance

- Subject identity (ArtifactSet ID, CompilerIR ID).
- Verifier identity/version.
- Evidence references (links to evidence records in the certifier's ledger).
- Timestamps (start, end).

## 9. Failure semantics

The contract's mandatory state model is the failure semantics. Specifically:

- **An internal verifier exception produces `INDETERMINATE`, not `PASS`.**
- A missing prerequisite produces `BLOCKED`.
- A non-existent verifier produces `NOT_RUN`.
- A successfully-run verifier that found a violation produces `FAIL`.
- A successfully-run verifier that found no violation produces `PASS`.

The contract distinguishes between:

- A successful verification (result is `PASS`).
- An unsuccessful verification (result is `FAIL`).
- An indeterminate verification (result is `INDETERMINATE`).
- A non-run verification (result is `NOT_RUN`).
- A blocked verification (result is `BLOCKED`).

The certifier (D11) decides certification status based on the result. A non-`PASS` result must not become a `CERTIFIED` outcome.

## 10. Extension mechanism

- New verifier kinds are added by implementing the verifier protocol.
- New result states require an ADR (the five states are the contract surface; new states are not added via the contract).
- The contract surface is frozen; extensions are versioned.

## 11. Current implementation (stabilization)

`certification/stages/{stub_stages,docker_stages,independent_verify}.py` (fail-closed in the campaign runtime; R0 verified this). The canonical Verifier interface is defined in D10 and implemented under R1-E.1.

## 12. Legacy implementations

- `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (fail-open: returns `success=True` on engine exception). **LEGACY.** Retired as runtime per R1-D.5; adapted to the canonical contract in R1-E.1 with LEGACY classification per R1-B.D17. **INV-B10**: verification cannot fail open.

## 13. Migration destination

- Legacy Gen-C verification pass → LEGACY classification (R1-B.D17); adapted to the canonical contract in R1-E.1 (fail-closed).
- The canonical `Verifier` interface and `VerificationResult` schema are defined in D10 and implemented under R1-E.1.

---

*End of D10. Cross-references: D01 (registry), D07 (CompilerIR), D09 (ArtifactSet), D11 (CertificationEvidence consumes VerificationResult), D19 (negative cases).*
