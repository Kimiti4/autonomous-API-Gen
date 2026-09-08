# VS1_RUNTIME_OBSERVATION (VS-D17)

**Status:** VS-1 Deliverable VS-D17. Controlled runtime observation of the
D16 deployment; mechanical evidence only.
**Spec:** VS-D17 gate prompt (§§1–14).
**Governance:** OBSERVATION ONLY. Detects and records; never interprets,
authorizes, mutates, regenerates, redeploys, or optimizes. Meaning belongs
to D18.

---

## 1. Purpose

Establish the runtime-feedback acquisition boundary: running `vs1-impl-v2`
software → mechanical observation → evidence, with nothing else in between.
D17 proves the deployed system can be exercised under a deterministic
workload and that every attempted operation resolves to exactly one of
PASS / FAIL / UNDETERMINED / BLOCKED — with no silent failures and no
inference disguised as observation.

## 2. Deployment observed

`vs1-deploy-v2` / `vs1-impl-v2` (`d2090df69127e992`) /
`vs1-evolved-96fe2d29fd76` (`d0f8d7579a08de83…`) / ISR `48e53dcef47aad84…`,
target `local-uvicorn-loopback`. The identity gate
(`verify_deployment_identity()`) recomputes D01–D15 before any observation;
any drift fails closed, and the harness asserts the live process is the v2
module — v1 is never silently substituted.

## 3. Workload (bounded, deterministic)

Authentication (register / login / invalid-credential 401 /
authenticated request), authorization (admin grant 201 / permitted op /
outsider 403 / member-role 403), full CRUD lifecycle (create → read →
update → read-after-update → delete → read-after-delete 422), event
emission, restart persistence, clean shutdown. One Outcomes note: the
lifecycle task is deleted mid-workload by design, so post-restart
persistence is proven two ways — "Observed task" present, "Lifecycle task"
still absent (the deletion itself persisted).

## 4. Measurements

Request counts, per-operation HTTP status, mechanical latency
(`perf_counter`, recorded — never judged), persistence/event/restart/
shutdown outcomes. `system is fast` style conclusions do not exist in D17;
the module has no vocabulary for them.

## 5. Failure handling

No retries, no remediation, no adaptive workload. The transport seam raises
into UNDETERMINED rather than inferring success; missing prerequisites
would be BLOCKED. This run: 18/18 PASS, 0 FAIL / 0 UNDETERMINED / 0 BLOCKED
— reported as counts, not as a quality claim.

## 6. Evidence schema & normalization

Each record carries observation/execution/deployment/implementation/
architecture IDs, operation, expected/observed class, status, measurement,
timestamp, and full provenance to ISR/requirements. Normalized form drops
timestamps and variable measurements (keeping `_measured` presence flags),
so repeated identical workloads produce equivalent normalized evidence —
proven by T24 (two independent launches, byte-equal normalized output).
Content hash `5f5056bc965fae73…` covers everything except `generated_at`.

## 7. Invariants (mechanical)

Constitutional (all five identities recomputed), security (auth/authz/
isolation enforced + secret-shape scan over every record), behavioral
(lifecycle, restart persistence, `svc-task` lifecycle events, clean
shutdown). A failed invariant raises instead of repairing — none failed.

## 8. Security

Passwords/tokens exist only as generator- and test-local call arguments;
no record, measurement, or evidence field carries them (fail-closed
`assert_secret_safe` scan at record, normalize, and assemble time; evidence
blob verified free of secret shapes and raw credential strings).

## 9. Firewall

`runtime_observation.py` imports only stdlib + the D16 contract (read-only
identity path). AST-enforced: no evolution/candidate/interpret/optimize/
retire/redeploy machinery, no calls to selection/decision/builders, no
writes to upstream, ledger, or evidence paths. Production authorization
remains false; no verdict language exists in the evidence.

## 10. Integrity & git

Upstream recomputed green (D15 hash, D16 contract hash `279fd4da7a47672…`,
D14 selection hash). B3-v2 chain, `certification/`, `release/evidence/`,
all VS1 docs, and the D16 implementation/deployment untouched. Work left
uncommitted per §13.

## 11. Tests

`tests/vs1/test_runtime_observation.py`: 30/30 (T01–T30). Three failures
during execution were fixed honestly: PASS-without-observation hardened in
the module (not the test), normalization test corrected to same-semantic
inputs, firewall import expectation corrected to the real parse result.

## 12. Handoff

D18 may interpret `vertical_slice/runtime_observation_evidence.json`
(18 observations, normalized form + `5f5056bc965fae73…`). No evolution
decision is authorized by anything in D17.

---

*End of VS-D17 artifact. Report follows separately per §14 (uncommitted).*
