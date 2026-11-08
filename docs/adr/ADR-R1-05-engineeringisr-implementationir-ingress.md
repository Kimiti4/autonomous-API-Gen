# ADR-R1-05: EngineeringISR and ImplementationIR Authority and Ingress

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-05 |
| **decision_status** | `APPROVED` |
| **implementation_status** | `IMPLEMENTED` (R1-W05 — CP067-R4) |
| **verification_status** | `INDEPENDENTLY_VERIFIED` (Model C policy matrix + Payroll orch path) |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-003, CP067-ISR-008 |
| **Related work packages** | R1-W05, R1-W08 |
| **Prerequisite ADRs** | ADR-R1-01, ADR-R1-02, ADR-R1-03 |

## Context

Path: `RequirementGraph → project_to_isr → EngineeringISR → ImplementationIR → compilers/tests`. Parallel to governed `ISRRevision` path (CP067 dashed lifecycle). F-10/F-11 have **no** content hash on dataclass models.

## Interim decision (proposed): Model C

| Aspect | Policy |
| --- | --- |
| Implementation | **Retained** — no deletion |
| Registration | **Retained** in family inventory |
| Trusted orchestration certification | **Blocked** when input is F-11 without governed lineage |
| Product acceptance / CP052 trusted registration | **Blocked** for ImplIR-only artifacts |
| Publication / promotion / deploy | **Blocked** unless re-enters via verified F-01 or future Model A/B |
| Isolated experiments | **Permitted** if marked `non_authoritative` provenance |
| Equivalence to `ISRRevision` | **Forbidden claim** without independent bridge evidence |

### Trusted ingress (governed)

CP056/057 orchestration and publication gateways must reject F-11 as certification authority input until Model A or B is **approved and independently verified**.

### Bypass inventory (investigated)

| Surface | Risk |
| --- | --- |
| `source_bound_full_stack.lower_source_bound_candidate` | Uses ImplementationIR |
| Contract tests `test_checkpoint_050_*` | In-process — not publication authority |
| `certification/proving/plan_full_stack_bridge` | Proving lane — scope limited |
| Dashboard orchestration | Uses governed path when configured — verify binding in R1-W08 |

### Future models (not selected)

- **Model A:** Derived from verified `ISRRevision` + transformation record.
- **Model B:** F-11 as independent authoritative family with full envelope.

## Trust laundering prevention

Non-authoritative artifacts must carry `provenance.non_authoritative=true` (or equivalent) and **must not** enter CP052 trusted registry or promotion lifecycle without re-verification.

## Approval record

| Approver | Amos Kimiti Kariuki — 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| Scope | **Model C** interim; Model A/B requires separate decision |
| implementation_status | `IMPLEMENTED` (CP067-R4; IV recorded) |
| verification_status | `NOT_VERIFIED` |
