# CONTRACT_CertificationEvidence (R1-B D11)

**Contract:** `CertificationEvidence`
**Status:** R1-B Deliverable D11. Authoritative contract specification. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** `certification/evidence/`

**Invariants this contract satisfies:** INV-B11 (certification cannot manufacture verification evidence), INV-B13 (historical evidence is immutable).

---

## 1. Purpose

`CertificationEvidence` is the downstream-of-verification certification record. Certification **must remain downstream of verification**: a CertificationEvidence record is only created when a `VerificationResult` exists, and the certification status is determined by the verification result — never by the certifier's local opinion.

## 2. Architecture

```text
Artifact (D09)
   ↓
Verification (D10)
   ↓
Evidence
   ↓
Certification
```

The contract enforces this chain. A CertificationEvidence record without a corresponding VerificationResult is rejected at construction.

## 3. The immutability invariant

> **Historical evidence is immutable.**

The B3-v2 evidence chain is preserved unchanged. R1-B does **not** alter historical certification evidence. The chain hash, the record contents, the timestamps, the verdict — all are immutable.

A new campaign identity (R2, the post-migration certification baseline) produces a new evidence chain. The old chain is not modified; it is preserved as historical evidence.

## 4. Required fields

| Field | Required? | Classification |
|---|---|---|
| `evidence_id` (identity) | yes | **semantic** |
| `subject_identity` (link to D09 ArtifactSet + D07 CompilerIR) | yes | **semantic** |
| `evidence_type` (e.g. `tiannara.verification.evidence`, `tiannara.certification.record`) | yes | **semantic** |
| `source` (which verifier / certifier produced this evidence) | yes | **semantic** |
| `verifier` (link to D10 VerificationResult) | yes | **semantic** (non-derivable) |
| `verification_result` (PASS / FAIL / INDETERMINATE / NOT_RUN / BLOCKED) | yes | **semantic** |
| `hash` (content hash, SHA-256) | yes | **semantic** |
| `timestamp` | yes | **observational metadata** |
| `campaign_id` (which campaign produced this evidence) | yes | **semantic** |
| `run_id` (which run within the campaign) | yes | **semantic** |
| `ledger_reference` (where in the evidence ledger this record lives) | yes | **semantic** |
| `certification_status` (CERTIFIED / NOT_CERTIFIED / BLOCKED / INDETERMINATE) | yes | **semantic** |
| `historical_immutability` (true; evidence is immutable) | yes | **semantic** |

## 5. Identity

- **Evidence ID:** UUIDv5 over subject + verifier + verification result + timestamp + campaign ID.
- **Content hash:** SHA-256 over canonical serialization. The chain is hash-linked: each record's hash includes the previous record's hash.

## 6. Lifecycle and mutability

- **Append-only.** Evidence is never modified or deleted.
- **Frozen.** Each record is immutable once written.
- **Historical immutability.** The B3-v2 evidence chain is preserved unchanged. R1-B does not alter it.

## 7. Hashing and serialization

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization. The chain is hash-linked.
- **Hash chain integrity:** each record's `hash` includes the previous record's `hash`, so tampering with one record invalidates the entire chain after it.

## 8. Provenance

- Subject identity (ArtifactSet, CompilerIR).
- Verifier (link to D10 VerificationResult).
- Source (which verifier / certifier produced this evidence).
- Campaign ID, run ID.
- Timestamp.
- Ledger reference.

## 9. Failure semantics

- A CertificationEvidence record without a corresponding VerificationResult is rejected at construction.
- The certification status is determined by the verification result:
  - `VerificationResult.PASS` → `CertificationStatus.CERTIFIED` (subject to campaign-level rules).
  - `VerificationResult.FAIL` → `CertificationStatus.NOT_CERTIFIED`.
  - `VerificationResult.INDETERMINATE` → `CertificationStatus.INDETERMINATE`.
  - `VerificationResult.NOT_RUN` → `CertificationStatus.BLOCKED`.
  - `VerificationResult.BLOCKED` → `CertificationStatus.BLOCKED`.
- **The certifier cannot manufacture verification evidence.** A certification status that contradicts the verification result (e.g. `CERTIFIED` with `VerificationResult.FAIL`) is rejected at construction. **INV-B11**.

## 10. Extension mechanism

- New evidence types are added by extending the schema; the contract surface is frozen.
- New campaign IDs are versioned.
- The contract surface is frozen; extensions are versioned.

## 11. Current implementation

`certification/evidence/ledger.py:EvidenceLedger` (JSONL, hash-chained, SHA-256). The B3-v2 ledger (443 records, chain intact) is preserved unchanged. The contract freezes the API.

## 12. Legacy implementations

None observed at this layer. The certification evidence ledger is canonical from inception.

## 13. Migration destination

n/a (canonical from inception). No migration required.

---

*End of D11. Cross-references: D01 (registry), D07 (CompilerIR), D09 (ArtifactSet), D10 (VerificationResult), D19 (no rewriting of historical evidence).*
