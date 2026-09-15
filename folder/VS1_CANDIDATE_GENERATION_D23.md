# VS1_CANDIDATE_GENERATION_D23 (VS-D23)

**Status:** VS-1 Deliverable VS-D23. Candidate generation for VS1-OBJ-001.
**Governance:** GENERATION ONLY. Competing possibilities, no selection,
implementation, deployment, observation, production change, commit, or push.

---

## 1. Purpose & objective

D22 admitted VS1-OBJ-001 (task priority LOW/MEDIUM/HIGH, view + filter,
existing behavior preserved). D23 answers what materially different
architectural strategies could satisfy it — possibilities for a future
selection gate to choose among. That separation is constitutional.

## 2. Authorization & ISR boundaries

D22 admission verified (status PASS, source digest byte-match
`4a9cde9a…`, objective hash match); canonical ISR recomputed
(`48e53dcef47aad84…`, unchanged — note: the D23 prompt §4 carries a
transcription slip `f961a626f`; the recomputed canonical value governs).
Historical D13/D14 synthetic lineage untouched; new candidates carry
`vs1-obj001-candidate-<digest>` identities on a separate chain.

## 3. Candidates (3, materially distinct)

- **domain-model-extension** (`f98815eb19e9`): priority as first-class
  Task attribute; service/API authoritative; filter as query capability.
  Low complexity, high reversibility, 8/13 direct coverage.
- **query-policy-separation** (`313b071dd7d4`): persistence in task
  domain, filtering semantics in a dedicated policy boundary (precedent:
  AuthorizationPolicy). Medium-low complexity, 7/13 direct.
- **capability-oriented-extension** (`a046c88a2460`): lifecycle
  authority untouched; Priority Capability owns validation,
  representation, filtering. Medium complexity, strongest isolation.

(IDs are content-addressed and reflect final candidate content.)

All: closed LOW/MEDIUM/HIGH + MEDIUM legacy default (structural fields,
not prose); deterministic MEDIUM-defaulting migration; NO_EVENT_CHANGE_REQUIRED;
10 failure modes each (fail-closed); membership-before-filter security;
priority never authorization.

## 4. Coverage honesty

API-owned criteria DIRECTLY_SUPPORTED; UI-realization needs downstream
work (no UI layer in slice); selection/deployment/observation-dependent
criteria REQUIRE_DOWNSTREAM_VERIFICATION; lineage established here. No
runtime claim is made at D23.

## 5. Comparison without selection

Neutral matrix (coverage/complexity/reversibility/coupling/risk) —
descriptive only. No winner, no ranking, no recommendation. T42 asserts
the comparison contains no selection language.

## 6. Determinism & integrity

Content-addressed ids, canonical evidence (`432ec0bf5a481d0a…`,
timestamp-independent), reordered-input stability. D01–D22 + ISR
unchanged; D12/D19/D20/D21 byte-stable; B3-v2 chain intact. Tests
`tests/vs1/test_candidate_generation_d23.py`: 62/62 (T01–T62).
Uncommitted per contract.

## 7. Handoff

`objective_id/hash`, source digest, ISR hash, policy hash, 3 ids/hashes,
lineage, coverage/security summaries; all downstream authorizations NONE/
FALSE. A D24 selection gate may now be authorized — nothing here selects.

---

*End of VS-D23 artifact. Report follows separately (uncommitted).*
