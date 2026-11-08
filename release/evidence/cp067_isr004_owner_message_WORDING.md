# CP067-ISR-004 supplement ratification — owner wording (copy/paste)

**Approver:** Amos Kimiti Kariuki  
**Supplements:** `release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json` (004 was left `PARTIAL_REMEDIATION_OPEN`)  
**New evidence:** CP067-R7 F-06 contract + `F-01..F-17` inventory + `canonicalization_oracle.v1`

---

## Recommended verbatim message

```
I, Amos Kimiti Kariuki, as Human Project Owner / Architecture Decision Authority,
ratify the supplemental independent proof for finding CP067-ISR-004 (CP067-R7),
supplementing release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json.

I accept the canonicalization independent oracle
certification.isr_independent_verification.canonicalization_oracle.v1 and the
refreshed evidence in release/evidence/cp067_p0_closure_independent_proof_report.json,
including CP067 checkpoint CP067-R7 (F-06 constitutional contract and complete
F-01..F-17 family inventory).

I update governed register status for CP067-ISR-004 from
PARTIAL_REMEDIATION_OPEN to CLOSED_SCOPED with this scope only:

- Seventeen-family inventory aligned to CP067 §E (no missing IDs);
- Five registered canonicalization contracts: F-01, F-02, F-04, F-05, F-06;
- Twelve families explicitly classified UNSUPPORTED_FAIL_CLOSED (no false PASS);
- Unknown-family lookup remains fail-closed in the registry.

I acknowledge this supplement does NOT certify universal canonicality across all
ISR families, does NOT register contracts for F-03 or F-07..F-17 beyond inventory
classification, and does NOT promote CP068 beyond
CP068_CONDITIONAL_ISOLATED_TESTING_ONLY or authorize production promotion or
governed runtime conformance.

I supersede the prior blocker "families-without-contract:approx-13" for this
scoped acceptance criterion: cp067-f01-f17-inventory-v1.

Timestamp: 2026-11-08T21:00:00+03:00
```

---

## After the owner message (engineering)

1. Copy template → `release/evidence/cp067_isr004_supplement_ratification_2026-11-08.json`; set `RATIFIED`, timestamp, event id e.g. `CP067-ISR-004-SUPP-RAT-2026-11-08-2100`.
2. Update `certification/atlas/esap/cp067_r1_p0_remediation_register.json`:
   - `p0_findings[CP067-ISR-004].status` → `CLOSED_SCOPED`
   - `acceptance_criterion` → `cp067-f01-f17-inventory-v1`
   - `supplement_ratification_ref` + append `supplement_ratifications` entry
   - `governed_status_after_ratification.CP067-ISR-004` → `CLOSED_SCOPED` (IV stage may remain `PARTIAL_INDEPENDENTLY_VERIFIED` per scope)
3. Update `folder/fs00_checkpoint_067_r7_w02_canonicalization_expansion.md` with ratification note.
4. Add conformance test mirroring `test_cp067_isr002_supplement_ratified_on_disk` for 004 JSON when ratified.
