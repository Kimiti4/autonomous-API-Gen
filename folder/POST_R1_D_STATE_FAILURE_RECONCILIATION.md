# POST_R1_D_STATE_FAILURE_RECONCILIATION (R1-RG-06)

**Status:** R1-RG-06. Lifecycle and failure semantics across the stack. Spec: `folder/postr1d.md` §§13–14.

---

## 1. Lifecycle map (conceptual §13 states → actual contract states)

| Conceptual | ISR | Compiler | Verification | Certification | Evolution |
|---|---|---|---|---|---|
| PROPOSED | `ISRRevision.create` (validated) | `isr_to_plan` input | — | — | candidate constructed |
| VALIDATED | `validate_invariants` pass | plan built | — | — | constraints hold |
| COMPILED | — | `backend.compile` → repo | — | — | — |
| VERIFIED | — | — | PASS/FAIL/INDETERMINATE/NOT_RUN/BLOCKED | — | evaluation evidence |
| OBSERVED | — | — | — | — | runtime edge (contract) |
| EVALUATED | — | — | — | — | fitness objectives |
| SELECTED/REJECTED | — | — | — | CERTIFIED/NOT_CERTIFIED (+QUALIFIED_PARTIAL campaign) | Pareto decision |
| EVOLVED | new revision (`parent_revision_id`) | new plan | — | new ledger records | new candidate + record |

## 2. Contradiction checks (§13)

- Compiler SUCCESS + verification FAILED + evolution ACCEPTED: **impossible by construction** — evolution consumes fitness/selection, and governance zeros exclude via the 0.2 gate (tested); verification failure yields non-PASS evidence which cannot certify (D14).
- `INDETERMINATE` vs `CERTIFIED`: **distinct by construction** — trial default is `NOT_CERTIFIED` (`trial.py:75`); campaign honesty rule (`verdict.py:1-3`); rg test pins ledger-failure → NOT_CERTIFIED. No path from INDETERMINATE to CERTIFIED exists.

No contradictions. No blocker.

## 3. Failure semantics (§14)

| Failure | Meaning across layers |
|---|---|
| Invalid ISR | `ISRInvariantViolation` at construction (fail-closed) |
| Invalid Architecture | constructor/validator rejection; candidate never enters selection |
| Invalid CompilerIR | Pydantic validation; lowering raises on bad input |
| Unsupported backend capability | explicit `UNSUPPORTED_CAPABILITY` → Verification INDETERMINATE → not certified (D14; R1-B gate decision A) |
| Compilation failure | empty/invalid repo → conformance failure → NOT_CERTIFIED |
| Artifact failure | missing/hash-mismatch → rejected (D09) |
| Verification failure | FAIL → NOT_CERTIFIED; exception → INDETERMINATE → NOT_CERTIFIED |
| Runtime evidence failure | fail-closed 0.0 vector (governance model for evidence-shaped failures) |
| Evaluation failure | exception propagates; no silent score |
| Evolution failure | operation raises; record with failure status; no silent retry |
| Provenance failure | construction rejection (missing refs) |

FAIL / REJECT / UNSUPPORTED / INDETERMINATE / NOT_CERTIFIED have consistent, layer-appropriate meanings; the fail-closed direction is preserved at every transition. `UNSUPPORTED_CAPABILITY → INDETERMINATE → ≠CERTIFIED` verified preserved (rg failure tests).

---

*End of R1-RG-06.*
