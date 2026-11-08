# ADR-R1-03: Semantic Equivalence and Bridge Evidence

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-03 |
| **decision_status** | `APPROVED` |
| **implementation_status** | `NOT_IMPLEMENTED` |
| **verification_status** | `NOT_VERIFIED` |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-002, CP067-ISR-004, CP067-ISR-008 |
| **Related work packages** | R1-W06 |
| **Prerequisite ADRs** | ADR-R1-01, ADR-R1-02 |

## Context

CP067 documented **≥22** bridges with mixed classifications (`LOSSY_EXPLICIT`, `NO_BRIDGE`, `UNSUPPORTED_FAIL_OPEN` risk on B-09). Matching digests cannot prove equivalence between representations.

## Decision (proposed)

Every bridge MUST publish a **TransformationContract** with: bridge id/version, source/dest family+revision, schema and canonicalization versions, lossiness class, obligation maps, verification method, failure behavior.

### Lossiness taxonomy (governed use)

| Class | Compile | Certify | Publish |
| --- | --- | --- | --- |
| `LOSSLESS_VERIFIED` | Yes, with evidence | Yes | Yes, with evidence |
| `LOSSY_EXPLICIT` | Only if loss budget accepted in plan binding | Case-by-case | Blocked unless waived by governance |
| `UNSUPPORTED_FAIL_CLOSED` | **No** trusted path | **No** | **No** |
| `UNKNOWN` | **No** trusted path | **No** | **No** |

Critical obligations (authZ, validation, effects, durability) cannot disappear silently.

## CP067 bridges (minimum remediation set)

B-04 (`isr_to_plan`), B-07 (constitutional↔core), B-08/B-09 (EngineeringISR path), B-03 synthesis — require explicit contracts before trusted promotion.

## Implementation boundaries

Contract registry + verification harness; **no** silent bridge behavior changes until authorized in R1-W06.

## Approval record

| Approver | Amos Kimiti Kariuki — 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| implementation_status | `NOT_IMPLEMENTED` |
| verification_status | `NOT_VERIFIED` |
