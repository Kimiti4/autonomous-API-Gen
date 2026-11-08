# ADR-R1-01: ISR Revision Identity and Hash Authority

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-01 |
| **Status (document)** | Proposed |
| **decision_status** | `APPROVED` |
| **implementation_status** | `IMPLEMENTED` (R1-W01 slice — see CP067-R3) |
| **verification_status** | `INDEPENDENTLY_VERIFIED` (F-01 Payroll slice — `cp067_r3_independent_verification_report.json`) |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-001 |
| **Related work packages** | R1-W01, R1-W02, R1-W09 |
| **Supersedes / relates** | ADR-008 (partial overlap — does not revoke ADR-008 until ratified) |

## Context

CP067 established parallel SHA-256 canonicalization paths for governed certification (`isr.core.identity.compute_content_hash` on `ISRGraph`) and constitutional artifacts (`constitutional_architecture.isr.versioning.ContentHasher` + `ISRSerializer` on `ISR`). No interchange proof exists. Digest equality is used in some slices (F-01 Payroll) but must not imply cross-family semantic equivalence.

## Current implementation

| Path | Input | Canonicalization | Algorithm |
| --- | --- | --- | --- |
| `compute_content_hash` | `schema_version` + sorted `ISRGraph` nodes/edges JSON | `json.dumps(sort_keys=True, separators=(",", ":"))` | SHA-256 hex |
| `ContentHasher.hash_isr` | Constitutional `ISR` model via `ISRSerializer.to_canonical_json` | Sorted keys, compact JSON | SHA-256 hex |

`ISRRevision.create()` recomputes via `compute_content_hash` only. Direct `ISRRevision(...)` construction bypasses `create()` (P1 CP067-ISR-005).

Consumers include: certification orchestration, evidence graph (`isr_authority_audit`), genesis validators, campaign plan builder, conformance harnesses.

## Confirmed problem

- Cross-domain digest comparison is **undocumented** and **unsafe**.
- Revision identity dimensions (family, schema, canonicalization version, revision surrogate, content digest) are **not** uniformly represented in a versioned envelope.
- Historical constitutional revisions may not reproduce under F-01 contract.

## Architectural requirements

1. Separate **authority domains** with explicit scopes.
2. Versioned **digest envelope** (see below) without circular self-hash.
3. Fail-closed on unknown canonicalization or schema contract.
4. Digest equality **never** constitutes semantic-equivalence evidence.

## Decision (proposed — not adopted until approved)

1. **`compute_content_hash`** remains **certification-path authority** for family **F-01/F-02** (`isr.core.revision`).
2. **`ContentHasher.hash_isr`** remains **constitutional authority** for family **F-06**.
3. **Forbidden:** comparing or substituting digests across domains without an approved bridge contract (B-07).
4. Introduce a **DigestEnvelope** specification (types + metadata only in Wave 1 — implementation in R1-W01 after approval):
   - `hash_algorithm` (e.g. `sha256`)
   - `authority_domain` (`isr.core.certification` | `constitutional.isr` | …)
   - `isr_family_id`
   - `schema_version`
   - `canonicalization_id` + `canonicalization_version`
   - `content_digest` (hex)
   - `revision_id` (surrogate, not hashed)
   - `provenance_ref` (optional bound metadata, not inside hashed payload unless contract says so)
5. Verification authority is selected by `authority_domain` + `canonicalization_version`.

## Identity dimensions (explicit, not collapsed)

Family, schema identity/version, canonicalization id/version, hash algorithm, content digest, revision id, source identity, provenance, signer, authorization, and semantic-equivalence evidence remain **distinct fields**. Semantic equivalence requires bridge/oracle evidence (ADR-R1-03).

## Alternatives considered

| Alternative | Rejection reason |
| --- | --- |
| Merge all hashing into `compute_content_hash` | Loses constitutional model semantics; migration risk unbounded |
| Merge all into `ContentHasher` | Certification path already bound to graph model and CP063 evidence |
| Treat matching SHA-256 as equivalence | Violates CP067 and ESAP invariants |
| Single universal digest string | Hides family and canonicalization version — unsafe at trust boundaries |

## Security / semantic / compatibility / migration

- **Security:** Wrong-family digest substitution must fail closed at ingress.
- **Semantic:** Content integrity ≠ semantic preservation.
- **Compatibility:** Existing F-01 records remain verifiable under `isr.core.identity/v1` contract after envelope adoption.
- **Migration:** Constitutional stores re-verify under F-06 contract; no automatic rewrite of historical evidence.
- **Historical evidence:** CP062–066 ledgers remain valid as slice evidence; labels must not claim universal ISR.

## Implementation boundaries (R1-W01 when authorized)

**Permitted:** envelope types, policy docs, verification helpers, fail-closed gates at documented trust boundaries, tests.

**Prohibited without separate ADR:** changing constitutional serializer semantics; retiring either hash path; silently redirecting callers.

**Modules in scope:** `isr/core/identity.py`, `isr/core/revision.py`, consumers in `certification/orchestration`, `certification/evidence_graph`, constitutional `versioning/hash.py` (read-only contract alignment only).

## Required tests (implementation phase)

Deterministic digest, domain binding, wrong-family rejection, tamper detection, stale digest, historical revision, no cross-domain equivalence without bridge, post-create mutation detection, consumer boundary tests.

## Independent verification

Non-generator verifier recomputes digests from published canonical bytes; adversarial matrix CP067 §M class A/F.

## Governance requirements

Constitutional architecture governance + ESAP architecture review. CP052 trusted evidence unchanged.

## Consequences

Adds explicit metadata at trust boundaries; short-term verbosity; long-term auditable identity.

## Open questions

- Whether B-07 bridge is Wave 1 or deferred.
- Authenticity signing scope (CP052 vs content hash only).

## Approval record

| Field | Value |
| --- | --- |
| Approver | Amos Kimiti Kariuki |
| Role | Human Project Owner / Architecture Decision Authority |
| Timestamp | 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| Scope | Dual-domain hash authority, digest envelope, no cross-domain interchange; **not** merge implementations; digest ≠ semantic equivalence |
| implementation_status | `NOT_IMPLEMENTED` |
| verification_status | `NOT_VERIFIED` |
| Limitations | Per ratification record — does not certify implementation or bypass IV/governance |
