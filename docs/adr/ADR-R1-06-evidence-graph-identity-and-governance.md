# ADR-R1-06: Evidence Graph Identity and Governance Binding

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-06 |
| **decision_status** | `APPROVED` |
| **implementation_status** | `NOT_IMPLEMENTED` |
| **verification_status** | `NOT_VERIFIED` |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-001..004 (reporting gaps), CP067-ISR-009 (P2) |
| **Related work packages** | R1-W07 |
| **Prerequisite ADRs** | ADR-R1-01 through ADR-R1-05 |

## Context

CP063 evidence graph binds ISR `content_hash` on a **slice** (Payroll). Graph **reports** lineage; it does **not** enforce compiler ingress. CP052 separates trusted evidence registration from generator self-certification.

## Decision (proposed)

1. **Minimum identity bindings** for governed evidence nodes: requirement refs, ISR family/schema/canonicalization version, revision id, content digest, plan binding ref, bridge ref (if any), compiler/backend ids, artifact digest, runtime env, oracle id, verification result, governance approval id, publication decision id.
2. **Invalidation rules:** Any change to ISR content, canonicalization contract, bridge, compiler, backend capability, plan, or oracle invalidates dependent evidence unless explicitly superseded with lineage.
3. **Historical failures preserved** — repairs supersede, never erase (CP063).
4. Evidence graph remains **L5 reporting** — enforcement stays at ingress/governance (ADR-R1-04, R1-W08).
5. **Non-authoritative experiments** may appear as nodes but **cannot** carry `trusted=true` without CP052 path.

## Governance boundaries

Preserve CP044 role separation, CP052 human gates, separate certification vs promotion approval. Graph is **not** constitutional authority.

## Approval record

| Approver | Amos Kimiti Kariuki — 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| Conditions | CP044/CP052 preserved; graph ≠ constitutional authority |
| implementation_status | `NOT_IMPLEMENTED` (R1-W07 not authorized to start) |
| verification_status | `NOT_VERIFIED` |
