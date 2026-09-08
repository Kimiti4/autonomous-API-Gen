# VS1_EVIDENCE_ACQUISITION_RESULTS (VS-D10)

**Status:** VS-1 Deliverable VS-D10. Controlled evidence acquisition results.
**Spec:** VS-D10 authorization prompt (§§1–25).
**Governance:** EXECUTION ONLY. Ends at normalized evidence — see firewall below.

---

## 1. Governance status

VS-D10 executed under explicit authorization. Pre-flight recomputed all
frozen identities (D01–D09); all matched, D09 outcome
`EVIDENCE_PLAN_REQUIRED` with exactly 2 plans totaling 7 observations.
No tracked modifications exist. No commits or pushes performed.

## 2. Frozen inputs

D01 graph `28548494…5526`, D02 ISR `48e53dcef47aad8…8e9dfb`, D03
`vs1-candidate-a` (`vs1-selection-v1`), D04 `vs1-impl-v1`, D05
`vs1-deploy-v1`, D06 `vs1-observe-v1` (7 records), D07 `vs1-interpret-v1`
(8/6/3), D08 `NO_CHANGE` (`vs1-decision-v1`), D09
`vs1-evidence-acquisition-v1` (`EVIDENCE_PLAN_REQUIRED`).

## 3. Execution

Runner: `vertical_slice/evidence_runner.py` (contract
`vs1-evidence-run-v1`, run `vs1-d10-run-001`).

- Auth plan (4 observations, one fresh deployment): admin-allowed
  administration, member-denied administration, credential rejection ×3,
  outsider isolation.
- Deploy plan (3 independent cycles): fresh process, store, and port per
  cycle; readiness + CRUD probe + shutdown + port-release each.
- Termination honored: exactly 7 observations, no retries, no extras.

## 4. Results (mechanical, uninterrupted)

| Observation | Outcome |
|---|---|
| auth-admin-allowed (201) | PASS |
| auth-member-denied (403) | PASS |
| auth-credential-rejection (401×3 identical) | PASS |
| auth-outsider-isolated (403) | PASS |
| deploy-cycle-01 (ready/crud/released) | PASS |
| deploy-cycle-02 (ready/crud/released) | PASS |
| deploy-cycle-03 (ready/crud/released) | PASS |

Summary: authorized 7, executed 7; pass 7, fail 0, undetermined 0,
blocked 0; both plans completed, none incomplete.

## 5. What these results are not

No hypothesis conclusion is drawn here: "7/7 PASS" is not "the auth model
is adequate" and not "deployment is proven repeatable". Those
determinations belong to D11 interpretation on this evidence. No evolution
is authorized, recommended, or implied.

## 6. Provenance

Every record carries plan/hypothesis/observation/run/cycle IDs plus the
D01–D09 identity chain. Cycle stores recorded per cycle (distinct).
Evidence content hash recorded in the artifact; recomputable.

## 7. Secret safety

Tokens lived in memory only. Artifact scanned for secret-value shapes:
none. Plan prose may discuss redaction/credentials (explicitly allowed);
no values retained.

## 8. Tests

`tests/vs1/test_evidence_runner.py`: 26/26 (T01–T26: upstream identities,
plan integrity, exact count, no scope expansion, live auth/deploy
execution, independence, synthetic FAIL/UNDETERMINED/BLOCKED paths, secret
protection, security preservation, provenance, normalization, firewall ×2,
upstream immutability, artifact integrity).

## 9. Integrity

B3-v2 chain intact (443 records); `certification/`, `release/evidence/`,
all VS-D01–D09 artifacts byte-untouched; no architecture/implementation/
deployment/observation change of any kind; D06–D09 evidence read-only.

## 10. Firewall

```text
PERFORMED: evidence acquisition (7 authorized observations + records).
NOT PERFORMED: interpretation, evolution decision/authorization,
  architecture mutation, candidate generation/selection, implementation,
  optimization, deployment mutation, redeployment.
```

---

*End of VS-D10 artifact. Report follows separately per §24 (uncommitted).*
