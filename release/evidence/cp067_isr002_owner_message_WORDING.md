# CP067-ISR-002 supplement ratification — owner wording (copy/paste)

**Approver:** Amos Kimiti Kariuki  
**Supplements:** `release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json` (002 was left `PARTIAL_REMEDIATION_OPEN`)  
**New evidence:** CP067-R6 B-04 obligation verifier + refreshed `cp067_p0_closure_independent_proof_report.json`

---

## Recommended verbatim message

```
I, Amos Kimiti Kariuki, as Human Project Owner / Architecture Decision Authority,
ratify the supplemental independent proof for finding CP067-ISR-002 (CP067-R6),
supplementing release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json.

I accept the updated independent verification recorded in
release/evidence/cp067_p0_closure_independent_proof_report.json and the B-04
obligation oracle certification.isr_independent_verification.b04_lowering_oracle.v1,
including enforcement on payroll, orders, and appointments workloads.

I update governed register status for CP067-ISR-002 from
PARTIAL_REMEDIATION_OPEN to CLOSED_SCOPED with this scope only:

- B-04 bridge registered as LOSSY_EXPLICIT;
- plan-to-ISR binding gate at compile;
- ISR→plan obligation diff verifier (preserved behavioral IDs, CAUSES_EFFECT
  bindings, plan_id/isr_id binding, deterministic re-lowering digest, explicit
  loss inventory for topology/requirement nodes).

I acknowledge this supplement does NOT accept a full inverse plan→ISR compiler,
does NOT claim universal lowering across all ISR families, and does NOT promote
CP068 beyond CP068_CONDITIONAL_ISOLATED_TESTING_ONLY or authorize production
promotion or governed runtime conformance.

I supersede the prior blocker "no-plan-isr-round-trip-verifier" for this scoped
acceptance criterion: b04-obligation-diff-verifier-v1.

Timestamp: 2026-11-08T20:45:00+03:00
```

---

## After the owner message (engineering)

1. Copy template → `release/evidence/cp067_isr002_supplement_ratification_2026-11-08.json`; set `RATIFIED`, timestamp, `repository_head_reviewed`, event id e.g. `CP067-ISR-002-SUPP-RAT-2026-11-08-2045`.
2. Update `certification/atlas/esap/cp067_r1_p0_remediation_register.json`:
   - `p0_findings[CP067-ISR-002].status` → `CLOSED_SCOPED`
   - `p0_independent_closure_proof.governed_status_after_ratification.CP067-ISR-002` → `CLOSED_SCOPED`
   - `p0_independent_closure_proof.independent_stages.CP067-ISR-002` → `CLOSED_INDEPENDENTLY_VERIFIED`
   - Add `supplement_ratification_ref` on the finding row.
3. Append supplement event id to checkpoint `folder/fs00_checkpoint_067_r6_w06_b04_obligation_verifier.md`.
4. Do not alter CLOSED_SCOPED statuses for 001/003/008 or PARTIAL for 004 without separate ratification.
