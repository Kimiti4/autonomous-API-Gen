# VS1_OBSERVATION (VS-D06)

**Status:** VS-1 Deliverable VS-D06. Bounded runtime observation + evidence.
**Spec:** VS-D06 authorization prompt (§§1–23).
**Governance:** FACTS ONLY. Ends at validated evidence — see §19 firewall.

---

## 1. Contract identity

`vs1-observe-v1` (`vertical_slice/observation.py`): closed 7-probe catalogue
(P01 readiness, P02 authentication, P03 CRUD, P04 authorization, P05
persistence, P06 events, P07 lifecycle). Target deployment
`vs1-local-loopback`, implementation `vs1-impl-v1`.

## 2. Target deployment

The VS-D05 local loopback deployment, rebuilt per observation run (fresh
store, seeded users/memberships, OS-assigned loopback port). No production
infrastructure; no public exposure.

## 3. Frozen upstream identities

Recomputed, never trusted: graph
`28548494…5526`, ISR `48e53dcef47aad84…8e9dfb`, selection `vs1-candidate-a`
(`vs1-selection-v1`), implementation `vs1-impl-v1`, deployment
`vs1-deploy-v1`. Any drift fails closed (pinned T01–T05).

## 4. Probes executed

P01 readiness (200 + body); P02 authentication (wrong-password 401 recorded
as outcome class only); P03 CRUD (201 → 200 on a fresh task); P04
authorization (fresh outsider 403); P05 persistence (post-restart read 200
via injected restart hook); P06 events (`task-created` present, producer
`svc-task`); P07 lifecycle (steady-state recorded; harness owns shutdown).

## 5. Observations obtained

7 records per run (`vertical_slice/observation_evidence.json`): ready,
rejected, lifecycle-completed, outsider-rejected, survived-restart, emitted,
running. No interpretation fields exist anywhere in the schema.

## 6. Evidence schema

12 fields per record: observation_id, contract, deployment, implementation,
probe, sequence, operation, target, result, status, payload, provenance.
Provenance carries 6 fields (contract, deployment, implementation, D01 hash,
D02 hash, D03 selection). Schema violations raise `ObservationError`.

## 7. Provenance

Every record traces contract → deployment → implementation → upstream
hashes. Reverse lineage to artifact/candidate/ISR/requirements is preserved
through the recorded hashes and the D12 field set.

## 8. Security/redaction

Passwords, tokens, salts, and hashes are scrubbed at collection
(`_scrub`, recursive, key-based); a marker scan (`_assert_no_secrets`)
rejects any record containing secret material. Evidence contains zero
secret markers (verified on the committed artifact). Tokens live in memory
only for the duration of a run.

## 9. Determinism

Records carry sequence numbers, not timestamps. Normalization sorts by
(sequence, observation_id). Two independent runs produce byte-equal
normalized evidence (pinned T18). Nondeterministic fields (ports, pids,
tokens) never enter records.

## 10. Failures/boundaries

Dead target → exception, no partial evidence. Incomplete provenance →
rejection. Unknown probe → rejection. Malformed upstream → fail-closed.
Full tie/boundary semantics in §13 of the module.

## 11. Explicit non-goals

No interpretation, optimization, benchmarking, load/chaos testing,
profiling, tuning, anomaly analysis, architecture proposals, remediation,
regeneration, or redeployment. Runtime→evaluation→evolution consumers remain
deferred; this artifact is their future input, not their implementation.

## 12. Verification results

`tests/vs1/test_observation.py`: 24/24 pass (T01–T22). Combined targeted
regression reported in the STOP REPORT. Full default `pytest -q` exceeds
the execution window (as previously observed); reported honestly.

---

## OBSERVED / NOT PERFORMED (§19 firewall)

```text
OBSERVED:
    Readiness, authentication outcome, CRUD lifecycle, authorization
    enforcement, persistence across restart, event emission, steady state.

NOT INFERRED:
    No statement about why anything behaved as it did.

NOT DECIDED:
    No statement about what should change.

NOT EVOLVED:
    No architecture, candidate, ISR, or requirement was modified.

NOT REGENERATED:
    No implementation was regenerated.

NOT REDEPLOYED:
    No evolved artifact was deployed. The observation server instances
    were terminated after each run.
```

---

*End of VS-D06 artifact. Report follows separately per §20 (uncommitted).*
