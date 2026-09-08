# VS1_DEPLOYMENT_V2 (VS-D16)

**Status:** VS-1 Deliverable VS-D16. Controlled deployment & runtime
bring-up of the regenerated implementation.
**Spec:** VS-D16 gate prompt (§§1–37).
**Governance:** DEPLOYMENT ONLY. Proves implementation → running system.
Performs no observation, interpretation, authorization, or evolution.

---

## 1. Purpose

Prove that `vs1-impl-v2` — the compiled artifact of the D14-selected
evolved architecture `vs1-evolved-96fe2d29fd76` — can be instantiated as a
running system under an exact deployment contract, without mutating any
upstream constitutional or evolutionary artifact and without upgrading
synthetic test authority into production authority.

D16 proves only: *the regenerated implementation can be brought to a
controlled running state with lineage, determinism, and security intact.*

## 2. Deployment boundary

```text
vs1-evolved-96fe2d29fd76 (D14 selection, central-policy)
        ↓
vs1-impl-v2 (D15 compilation, implementation_hash d2090df69127e992)
        ↓
vs1-deploy-v2 (D16 contract, local-uvicorn-loopback)
        ↓
controlled running deployment (bring-up verified, then shut down)
```

PERFORMED: contract definition, loopback bring-up, readiness/smoke/
security verification, clean shutdown, deterministic restart.
NOT PERFORMED: observation campaign, evidence interpretation, hypothesis
update, evolution decision/generation/selection, implementation
regeneration, production promotion (§§22–23 firewall).

## 3. Upstream inputs (frozen, consumed read-only)

D01 graph `28548494…5526`, D02 ISR `48e53dcef47aad8…8e9dfb`, D03
`vs1-candidate-a`, D04 `vs1-impl-v1`, D05 `vs1-deploy-v1` (untouched; v2
uses a separate contract and default port), D06 `vs1-observe-v1`, D07
`vs1-interpret-v1`, D08/D12 `NO_CHANGE` (`ae6df7c889ff9cab`), D09–D11 as
recorded, D13 `vs1-evolution-synthetic-001` (3 candidates), D14
`vs1-evolved-96fe2d29fd76` (`f39c508e3a6ed52d`), D15 `vs1-impl-v2`
(`d2090df69127e992`). Verified by recomputation in
`deployment_v2.verify_upstream()`; any mismatch fails closed.

## 4. Implementation identity

`vs1-impl-v2`, parent `vs1-impl-v1` (preserved, untouched). Entrypoint
`vertical_slice/app_v2/api.py:create_app`, launch module
`vertical_slice/serve_v2.py`, namespace `vertical_slice.app_v2`.
`verify_implementation()` proves the component set exists and the
central-policy delta is represented (service delegates to
`AuthorizationPolicy.check_session/check_member/check_admin`). The test
harness asserts the live process command line contains
`vertical_slice.serve_v2` and never the v1 module — a deployment that
accidentally runs v1 fails.

## 5. Architecture identity

`vs1-evolved-96fe2d29fd76` / central-policy, architecture hash
`d0f8d7579a08de83…`, selection `vs1-selection-44cf7da052a5`
(`f39c508e3a6ed52d`), objective
`vs1-objective-synthetic-auth-boundary`, authorization
`vs1-authorization-synthetic-001`, ISR `48e53dcef47aad84…`.

## 6. Deployment target

`local-uvicorn-loopback` on `127.0.0.1` (default port 8472; tests use
OS-assigned ports). Rationale: D16 must demonstrate the
implementation-to-runtime transition with the least machinery capable of
proving it. The D05 loopback pattern is the repository's authoritative
deployment shape; Docker/Kubernetes/cloud would add infrastructure without
adding architectural evidence, and would blur the D16/D17 boundary by
inviting operational observability. Technology stays a backend: FastAPI /
Uvicorn / Python 3.14.0 are pinned runtime facts, never the identity.

## 7. Configuration model

`runtime_configuration()`: host, default port, application entrypoint,
launch module, startup command, database (`json-file-store` rooted at a
per-deployment isolated `VS1_STORE_DIR`), runtime environment, pinned
dependency versions, security configuration (central policy active, no
bypass flags), logging (stdio, audit-only). Canonical and secret-free by
construction; T10 enforces both.

## 8. Startup procedure

`python -m vertical_slice.serve_v2` with `VS1_STORE_DIR` set to an
isolated directory and `VS1_PORT=0`. The harness parses the bound port
from uvicorn stdio, then polls `GET /health` to readiness. A process that
exits immediately fails (§13).

## 9. Readiness contract

`GET /health` → `200 {"status":"ok"}` — the exact contract established by
the implementation. Readiness is bring-up verification, not behavioral
observation.

## 10. Security boundary

Deployment adds no credentials, no bypass flags, no network exposure
beyond loopback. Bring-up re-proves: identical-error login (401/401),
member/admin role path (403/201), tenant isolation for a true outsider
(403), and absence of secret shapes in all recorded bodies. The central
`AuthorizationPolicy` remains the sole authorization mechanism; any
configuration bypassing it fails (§17).

## 11. Restart behavior

The exact same contract relaunches against the same store: startup,
readiness, v2 identity (command line), and shutdown all re-verified.
State written before shutdown (task + memberships) reads back after
restart through fresh login tokens.

## 12. Shutdown behavior

`SIGTERM/terminate + wait` (15s, then kill as a safety net that the tests
treat as failure-adjacent, never silent). Post-shutdown the loopback
address refuses connections; the orphan audit (T29) fails on any surviving
launched process.

## 13. Evidence model

`vertical_slice/deployment_v2_evidence.json`: identity, integrity,
configuration, startup, readiness, API reachability, controlled smoke,
security bring-up, shutdown, restart, determinism, authorization status,
boundary status, provenance. Recomputable: `build_contract()` and
`verify_upstream()` are pure recomputation; the live sections are
reproducible by rerunning the documented bring-up (the generator procedure
below) — statuses, never instance values, are recorded, so two runs
produce the same normalized content.

Regeneration procedure (no repo artifact required): seed an isolated store
via `TaskTrackerServiceV2` (two workspaces, three users, three
memberships), launch `python -m vertical_slice.serve_v2` with
`VS1_PORT=0`, record health / valid-create / 401 / 403 / persistence-read
/ role-path / isolation / shutdown / restart-identity, then
`deployment_v2.assemble_evidence(live, <utc-timestamp>)` and write
canonical JSON (sorted keys, compact separators, LF).

## 14. Determinism model

The contract contains no PIDs, timestamps, bound ports, or secrets, so
normalization is the explicit identity function (`normalize_contract`).
`contract_hash` (`279fd4da7a47672…`) is stable across preparations.
`normalized_hash` in evidence covers everything except `generated_at`;
verified timestamp-independent.

## 15. Synthetic authorization limitation

Real authority is `NO_CHANGE` with `real_authorization=0`. D13/D14/D15/D16
run under `SYNTHETIC_TEST_ONLY`; `production_authorization=false` is
pinned in the module, the contract, the selection record, and the
evidence. T31 proves no assignment path in D16 code can upgrade synthetic
to production, and the real D12 record still reads `NO_CHANGE`. This
deployment is a controlled test bring-up, never a production promotion.

## 16. Downstream handoff (D17)

`deployment_id=vs1-deploy-v2`, `implementation_id=vs1-impl-v2`
(`d2090df69127e992`), `architecture_id=vs1-evolved-96fe2d29fd76`
(`d0f8d7579a08de83…`), `isr_hash=48e53dcef47aad84…`,
`deployment_target=local-uvicorn-loopback`,
`deployment_evidence_hash=e9b469ee5f26d025…`,
`production_authorization=false`. D17 may observe the running v2 system;
it must remain a separate stage.

## 17. Limitations

- Loopback only: no TLS, no multi-node, no production hardening claims.
- Minimal smoke by design (§16): full behavioral equivalence was proven
  at D15; D16 re-proves reachability, not behavior.
- Full default `pytest -q` exceeds the execution window; D16 reports the
  complete targeted regression (below) honestly instead.

## 18. Tests

`tests/vs1/test_deployment_v2.py`: 31/31 (T01–T31; T31 is the §32
synthetic-firewall test, required rather than inflationary). Two genuine
defects were caught during execution and fixed in behavior, not
assertions: response-key ordering comparison, and isolation tested with a
user that had just been granted membership (now uses a true outsider).

---

*End of VS-D16 artifact. Report follows separately per §36 (uncommitted).*
