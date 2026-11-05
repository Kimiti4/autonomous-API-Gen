# CONTRACT_CrossContractIdentity_Provenance (R1-B D13)

**Contract:** `Cross-Contract Identity & Provenance Model`
**Status:** R1-B Deliverable D13. Authoritative cross-contract identity and provenance model. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Authority:** R1-B D02–D12 (per-contract specifications).

**Invariants this contract satisfies:** INV-B12 (Runtime observations retain reverse lineage), INV-B13 (Historical evidence is immutable), and the cross-contract traceability invariant (every contract references upstream contracts by content hash).

---

## 1. Purpose

The cross-contract identity and provenance model defines **one explicit identity chain** across all 11 canonical contracts. Contract identities are deterministic and contract-specific: most use canonical content hashes, while some use UUIDv5 identities. ISR now separates semantic graph identity (`content_hash`) from exact revision-envelope identity (`revision_hash`). Exact references to an ISR revision must bind the envelope hash; the graph hash remains available for semantic-equivalence comparisons.

## 2. The identity chain

```text
RequirementGraph ID (D02)
    ↓
ISR Revision envelope hash (D03)
    ↓
ArchitectureCandidate ID (D04)
    ↓
EvolutionRecord ID (D06; produced by EvolutionOperation D05)
    ↓
CompilerIR ID (D07)
    ↓
ArtifactSet ID (D09; produced by CompilerBackend D08)
    ↓
VerificationResult ID (D10)
    ↓
CertificationEvidence ID (D11)
    ↓
RuntimeObservation ID (D12)
    ↓
[feedback into Evolution D04–D06]
```

The chain is a **downward sequence of deterministic identities**. Each contract at level N references its predecessor at level N-1 by the identity required by that predecessor's contract. For ISR, exact revision lineage uses `revision_hash`; semantic graph comparison uses `content_hash`. The chain is intended to be end-to-end, but the downstream adoption of the new ISR envelope hash remains a migration item.

## 3. Identity rules

### 3.1 Per-contract identity

Every contract has a stable identity computed from its canonical serialization:

| Contract | Identity |
|---|---|
| RequirementGraph | SHA-256 of canonical JSON of requirements + edges |
| ISR | `content_hash`: SHA-256 of canonical graph JSON + schema version; `revision_hash`: SHA-256 of system ID + schema version + graph hash + provenance |
| ArchitectureCandidate | SHA-256 of canonical JSON of the candidate |
| EvolutionOperation | UUIDv5 over operator type + parameters + timestamp |
| EvolutionRecord | SHA-256 of canonical JSON of the record |
| CompilerIR | SHA-256 of canonical JSON of the IR |
| CompilerBackend | Backend ID + version + SHA-256 of the manifest |
| ArtifactSet | SHA-256 of the manifest (file paths + content hashes + metadata) |
| VerificationResult | UUIDv5 over subject + verifier + timestamp |
| CertificationEvidence | UUIDv5 over subject + verifier + verification result + timestamp + campaign ID |
| RuntimeObservation | UUIDv5 over deployment + artifact + timestamp |

### 3.2 Content hash determinism

A contract's content hash is **deterministic**: the same content produces the same hash. The canonical serialization is sorted-key JSON (or another canonical form defined in the per-contract spec). Hash function: SHA-256.

### 3.3 Parent references

Every contract at level N references its predecessor at level N-1 by the identity required by that predecessor's contract. The reference is **non-derivable** (semantic) — it cannot be computed from the referencing contract's own content; it must be set explicitly. For exact ISR revision lineage, use the revision-envelope hash.

## 4. Lineage rules

### 4.1 Forward lineage (Requirement → Artifact)

The forward lineage traces a generated artifact back to its requirement:

```text
Requirement
→ RequirementGraph (D02)
→ ISR (D03)
→ ArchitectureCandidate (D04)
→ CompilerIR (D07)
→ ArtifactSet (D09)
```

Each step is referenced by content hash. The forward lineage is enforced at construction in each contract (e.g. D09 ArtifactSet requires the source Requirement reference; D07 CompilerIR requires the source ISR reference).

### 4.2 Reverse lineage (Runtime → Requirement)

The reverse lineage traces a runtime observation back to the requirement that produced the deployed artifact:

```text
RuntimeObservation (D12)
→ Deployment
→ ArtifactSet (D09)
→ CompilerIR (D07)
→ ArchitectureCandidate (D04)
→ ISR (D03)
→ RequirementGraph (D02)
```

The reverse lineage is enforced at construction in D12.

### 4.3 Evolution lineage

The evolution lineage traces a candidate back to its parents and the operation that produced it:

```text
ArchitectureCandidate (D04)
← parent_architecture (parent candidate ID)
← EvolutionOperation (D05) identity
← EvolutionRecord (D06) — the record of what happened
← ISR (D03) — the ISR the parent was for
```

The evolution lineage is enforced at construction in D04 and D06.

## 5. Cross-reference matrix

| Referencing contract | Referenced contract | Field | Reference kind |
|---|---|---|---|
| ArchitectureCandidate (D04) | ISR (D03) | `isr_revision_reference` (currently graph content hash; add revision-envelope hash for exact lineage) | semantic; non-derivable; downstream migration open |
| CompilerIR (D07) | ISR (D03) | `source_isr_content_hash` + `source_isr_revision_hash` | semantic; non-derivable; both carried by canonical CompilerIR |
| CompilerIR (D07) | ArchitectureCandidate (D04) | `source_architecture_candidate_reference` | semantic; non-derivable |
| CompilerBackend (D08) | CompilerIR (D07) | input contract: `supported_ir_version` | semantic |
| CompilerIR (D07) | CompilerBackend (D08) | `backend_constraints` (which backends can lower this IR) | semantic |
| ArtifactSet (D09) | CompilerBackend (D08) | `backend_id` + `backend_version` | semantic |
| ArtifactSet (D09) | CompilerIR (D07) | `compiler_ir_id` | semantic; non-derivable |
| ArtifactSet (D09) | ArchitectureCandidate (D04) | `architecture_candidate_id` | semantic; non-derivable |
| ArtifactSet (D09) | ISR (D03) | `isr_revision_hash` (must resolve to revision-envelope hash; implementation adoption open) | semantic; non-derivable |
| ArtifactSet (D09) | RequirementGraph (D02) | `requirement_graph_id` | semantic; non-derivable |
| VerificationResult (D10) | ArtifactSet (D09) | `subject_artifact_id` | semantic; non-derivable |
| VerificationResult (D10) | CompilerIR (D07) | `subject_ir_id` | semantic; non-derivable |
| CertificationEvidence (D11) | VerificationResult (D10) | `verifier` (link to D10) | semantic; non-derivable |
| CertificationEvidence (D11) | ArtifactSet (D09) | `subject_identity` | semantic; non-derivable |
| CertificationEvidence (D11) | CompilerIR (D07) | `subject_identity` | semantic; non-derivable |
| RuntimeObservation (D12) | ArtifactSet (D09) | `artifact_set_id` | semantic; non-derivable |
| RuntimeObservation (D12) | CompilerIR (D07) | `compiler_ir_id` | semantic; non-derivable |
| RuntimeObservation (D12) | ArchitectureCandidate (D04) | `architecture_candidate_id` | semantic; non-derivable |
| RuntimeObservation (D12) | ISR (D03) | `isr_revision_hash` (must resolve to revision-envelope hash; implementation adoption open) | semantic; non-derivable |
| RuntimeObservation (D12) | RequirementGraph (D02) | `requirement_graph_id` | semantic; non-derivable |
| EvolutionRecord (D06) | EvolutionOperation (D05) | `operation_id` | semantic; non-derivable |
| EvolutionRecord (D06) | ArchitectureCandidate (D04) | `parent_candidate_ids` + `resulting_candidate_ids` | semantic; non-derivable |
| EvolutionRecord (D06) | ISR (D03) | `source_isr` + `target_isr` (currently content hashes; exact revision-envelope migration open) | semantic; non-derivable |

## 6. Provenance fields

Each contract carries a `provenance` field that includes:

- **Author/owner** (who or what produced the contract).
- **Tool versions** (which tools were used).
- **Timestamp** (when the contract was produced).
- **Source prompt hash** (if applicable).
- **Parent reference hashes** (the content hashes of upstream contracts referenced by this contract).

The `provenance` field is **observational metadata** (per the field-classification discipline) — it describes the contract but does not define its semantics.

## 7. Immutability

- Every contract is **immutable** once written.
- A new revision is a new identity; the previous is preserved.
- The B3-v2 evidence chain is **historically immutable** (INV-B13). R1-B does not alter it.

## 8. Reconstruction rule

Given any contract at level N, the **full lineage** can be reconstructed by following the parent references upward. The reconstruction is:

- Deterministic: the same set of contracts reconstructs to the same lineage.
- Verifiable: each parent reference is verified at construction.
- Tamper-evident: any modification to a contract invalidates its content hash and breaks the lineage.

The reconstruction rule is what makes Tiannara's engineering lineage **reconstructable** rather than merely **generated**. Generated files are not enough; the lineage is the source of truth.

## 9. Failure semantics

- A contract that references a non-existent or non-traceable parent is rejected at construction (`BrokenLineage`).
- A contract with a content hash that does not match its canonical serialization is rejected (`HashMismatch`).
- The contract distinguishes:
  - `LINEAGE_OK` — full lineage verified.
  - `LINEAGE_BROKEN` — parent reference invalid; rejected.
  - `LINEAGE_HASH_MISMATCH` — content hash mismatch; rejected.

## 10. Extension mechanism

- New contract surfaces (i.e., new contracts in the chain) require an ADR.
- New cross-reference fields require an ADR.
- The chain is frozen; extensions are versioned.

## 11. Cross-references

- D02–D12: per-contract identity, lineage, and provenance fields.
- D14: state machine & failure semantics.
- D17: legacy boundary specification (legacy components are mapped to their canonical destinations via this model).
- D20: R1-B gate report (the gate evaluates whether the cross-contract model is consistent).

---

*End of D13. The cross-contract identity and provenance model is the foundation of Tiannara's reconstructable engineering lineage. Contract identities are deterministic and contract-specific; exact ISR revision references use the provenance-bound revision-envelope hash. The chain is intended to be end-to-end and tamper-evident; downstream adoption of the ISR dual identity remains open.*


## 12. ISR dual-identity extension (FS-00 A2)

The approved ISR schema reconciliation defines two distinct identities:

- `content_hash`: semantic graph hash over canonical graph serialization plus ISR schema version. Provenance is intentionally excluded so semantically identical graphs can be compared.
- `revision_hash`: revision-envelope hash over system ID, schema version, graph content hash, and canonical Provenance. It binds the exact immutable revision and its lineage.

Canonical CompilerIR now carries both `source_isr_content_hash` and `source_isr_revision_hash`. TOR SourceTraceability schema 1.1 and authorization/payroll certification evidence also bind the exact revision-envelope hash. The ISR migration helper records the source revision ID, source graph hash, source envelope hash, and migration ID in the new revision's provenance.

**Downstream migration still required:** Campaign A source-bound snapshot schema 2 and mapping provenance now carry the exact ISR revision-envelope hash and CompilerIR ID/hash. The canonical D04 ArchitectureCandidate runtime model still needs a separately validated revision-envelope field. D06 EvolutionRecord, D09 ArtifactSet and D12 RuntimeObservation fields also require implementation-level verification/migration. Full cross-contract exact-revision lineage is NOT ESTABLISHED.
