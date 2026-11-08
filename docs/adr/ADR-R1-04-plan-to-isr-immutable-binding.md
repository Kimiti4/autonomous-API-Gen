# ADR-R1-04: Compilation Plan and Exact ISR Revision Binding

| Field | Value |
| --- | --- |
| **Identifier** | ADR-R1-04 |
| **decision_status** | `APPROVED` |
| **implementation_status** | `NOT_IMPLEMENTED` |
| **verification_status** | `NOT_VERIFIED` |
| **governance_status** | `APPROVED` |
| **Date proposed** | 2026-11-08 |
| **Related findings** | CP067-ISR-002 |
| **Related work packages** | R1-W04, R1-W08 |
| **Prerequisite ADRs** | ADR-R1-01, ADR-R1-02 |

## Context

`compiler.core.lowering.isr_to_plan` is lossy. Current `CompilationPlan.plan_id` uses `plan:{revision.content_hash[:16]}` — insufficient for immutable exact revision binding. Orchestration calls `isr_to_plan(revision)` without execution-time re-verification gate (CP067 §K).

## Decision (proposed)

Introduce **PlanBindingRecord** (immutable at approval time):

| Field | Required |
| --- | --- |
| `isr_family_id` | Yes |
| `isr_revision_id` | Yes |
| `isr_content_digest` | Full 64-char hex |
| `isr_schema_version` | Yes |
| `canonicalization_id` + `canonicalization_version` | Yes |
| `plan_digest` | Hash of canonical plan serialization |
| `plan_revision` / `plan_id` | Surrogate |
| `compiler_id` + `compiler_version` | At execution |
| `backend_id` + capability manifest ref | At execution |
| `transformation_lineage_refs` | When bridges used |

**Execution gate (mandatory at `FullStackOrchestrationAuthority` / compile ingress):** Recompute ISR digest; verify plan digest; reject stale/superseded/wrong-family/tampered bindings.

**Historical plans:** Previously authorized immutable plans may execute under their recorded contract versions until superseded by governance; contract upgrades require explicit re-authorization policy (default: fail closed for certification paths).

## Failure behavior

Fail closed on all cases listed in CP067-R2 §14.3.

## Implementation boundaries (R1-W04 — not Wave 0)

Types, gate in orchestration authority, evidence fields — after ADR approval.

## Approval record

| Approver | Amos Kimiti Kariuki — 2026-11-08T15:39+03:00 |
| Evidence | `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json` |
| implementation_status | `NOT_IMPLEMENTED` (R1-W04 not authorized to start) |
| verification_status | `NOT_VERIFIED` |
