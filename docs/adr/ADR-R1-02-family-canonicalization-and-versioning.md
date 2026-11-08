# ADR-R1-02: Family-Specific Canonicalization and Versioning

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-02 |
| **decision_status** | `APPROVED` |
| **implementation_status** | `IMPLEMENTED` (Tier A F-01/F-02 — see CP067-R3) |
| **verification_status** | `INDEPENDENTLY_VERIFIED` (Tier A + Tier B on Payroll slice — not universal) |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-001, CP067-ISR-004 |
| **Related work packages** | R1-W02, R1-W06 |
| **Prerequisite ADRs** | ADR-R1-01 (approved) |

## Context

CP067 inventoried **17** confirmed ISR/intermediate families and **5** ambiguous candidates. **≥12** lack explicit canonical contracts. ESAP requires deterministic, versioned representation without flattening family semantics.

## Decision (proposed)

1. Each trusted family publishes a **CanonicalizationContract**:
   - `canonicalization_id` (stable string, e.g. `isr.core.revision/canonical/v1`)
   - `canonicalization_version` (semver or integer)
   - `schema_version` rules
   - Serializer entrypoint(s)
   - Determinism rules (key order, null/absent, unicode, numeric, datetime)
   - Unknown-field and extension policy (**fail-closed** or explicit preserve)
2. **No universal schema** — shared machinery allowed; semantic contracts per family.
3. Schema version changes and canonicalization version changes are **orthogonal**.
4. Historical revisions verified under the contract version recorded at creation time.

## Family inventory (CP067 baseline — unchanged)

Confirmed F-01…F-17 and candidates C-01…C-05 remain in inventory. Ambiguous candidates stay **`UNRESOLVED`** until classified; no silent removal.

### W02 initial implementation scope (when authorized)

| Tier | Families | Rationale |
| --- | --- | --- |
| **Tier A (first)** | F-01, F-02 | Certification path; existing tests |
| **Tier B (second)** | F-04, F-05 | Plan/contract binding (ADR-R1-04 dependency) |
| **Tier C (declared only)** | F-06 | Constitutional — contract declaration without F-01 merge |
| **Deferred** | F-10–F-13 until ADR-R1-05 resolved | Model C blocks trusted ingress |

## Ambiguous candidates (classification)

| ID | Proposed classification | Action |
| --- | --- | --- |
| C-01 | Adapter/projection of reqgraph | Contract ties to F-03, not new family until proven |
| C-02 | Intent synthesis output | **UNKNOWN** — no equivalence claim |
| C-03 | Genesis pre-revision | Bridge B-11 only |
| C-04 | Runtime ledger | Not ISR family — consumption only |
| C-05 | Frontend projection | Derived artifact contract |

## Alternatives rejected

Universal canonical JSON for all families; implicit schema_version as canonicalization_version; omitting ambiguous candidates from inventory.

## Implementation boundaries (R1-W02)

Framework for registering contracts; golden byte vectors per Tier A family; **no** change to unrelated family serializers until contract approved.

## Required tests

Per-family determinism matrix (key reorder, null/absent, extensions, version mismatch fail-closed).

## Approval record

| Approver | Amos Kimiti Kariuki — Human Project Owner / Architecture Decision Authority |
| Timestamp | 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| Scope | Per-family versioned canonicalization; no universal schema collapse |
| implementation_status | `NOT_IMPLEMENTED` |
| verification_status | `NOT_VERIFIED` |
