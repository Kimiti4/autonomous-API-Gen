# VS1_DEPLOYMENT (VS-D05)

**Status:** VS-1 Deliverable VS-D05. Controlled deployment + bring-up.
**Spec:** VS-D05 authorization prompt (§§1–28).
**Governance:** DEPLOYMENT ONLY. Ends at bring-up + bounded smoke verification.

---

## 1. Governance status

VS-D05 executed under explicit authorization. Pre-flight verified: VS-D01 at
`7340e93`, VS-D02 at `0c06f48`, `folder/VS1_CANDIDATES.md` present with PASS
selection of `vs1-candidate-a`, VS-D04 files present with PASS implementation.
uvicorn 0.45.0 available in the root environment. The pre-existing
`evidence/factory.jsonl` append was left untouched and unattributed.

## 2. Frozen input identities

| Artifact | Identity |
|---|---|
| VS-D01 graph | sha256 `28548494e754e9b8…5526` (recomputed at validation) |
| VS-D02 ISR | content hash `48e53dcef47aad8…8e9dfb` (recomputed) |
| VS-D03 selection | `vs1-selection-v1` → `vs1-candidate-a` (re-executed, same winner) |
| VS-D04 implementation | `vs1-impl-v1` |

`vertical_slice/implementation.py:frozen_input_identity()` recomputes all
three; any drift fails closed.

## 3. Selected candidate

`vs1-candidate-a` / `consolidated-monolith`. No re-selection performed.

## 4. Implementation identity

`vs1-impl-v1` (`vertical_slice/app/*` + `vertical_slice/implementation.py`),
evidence `vertical_slice/evidence.json`. No implementation semantics changed
for deployment (zero tracked modifications to existing files).

## 5. Deployment target

**local-uvicorn-loopback**: uvicorn serving the frozen D04 FastAPI app on
`127.0.0.1` with an OS-assigned port (recorded as a runtime-instance
identifier). Non-public by construction. Reason: smallest viable environment
exercising real HTTP wiring; no cloud, DNS, certificates, or production
infrastructure.

## 6. Runtime/dependency versions

Python 3.14.0; fastapi 0.136.0; uvicorn 0.45.0; starlette installed;
pydantic 2.13.0 (httpx 0.28.1 test-only). Pinned in
`vertical_slice/deployment.py:DEPENDENCY_VERSIONS` and asserted by test.

## 7. Deployment contract

`vertical_slice/deployment.py` (`vs1-deploy-v1`): target, host, default
port, startup command `python -m vertical_slice.serve`, readiness
`GET /health → 200`, shutdown via terminate+wait, 10 named smoke tests.
Deterministic except recorded instance identifiers (bound port, exit code).

## 8. Configuration identity

`VS1_STORE_DIR` (store directory), `VS1_PORT` (default 8471, `0` for
OS-assigned in tests). No secrets in evidence or logs; test credentials are
synthetic (`alice-secret-pw` etc.) and never leave the local run.

## 9. Build/package evidence

N/A — no build step exists. The implementation runs directly from source
(`python -m vertical_slice.serve`); no application semantics altered.

## 10. Startup evidence

Server process starts; uvicorn reports the bound port; recorded per run
(e.g. port 13134 in the evidence-generating run).

## 11. Readiness evidence

`GET /health` → `200 {"status": "ok"}` within the bounded poll window,
before any smoke test proceeds.

## 12. API smoke-test evidence

Register → login → create → list → get → patch → delete → get-gone, plus
assign/member administration — all status codes as contracted
(201/200/204/401/403/422). Recorded in `deployment_evidence.json`.

## 13. Persistence smoke-test evidence

Task created via API, server terminated, server restarted on the same store
directory, task retrievable with identical content. Recorded.

## 14. Event smoke-test evidence

API create+update produced persisted `["task-created", "task-updated"]`
with `producer=svc-task` for the task. Verified by reading the store file
(white-box seam, documented: no event API surface exists by design).

## 15. Security smoke-test evidence

No credentials → 401; bad token → 401; outsider → 403 on member-only reads;
non-admin member administration → 403; identical login errors for unknown
users and wrong passwords. Recorded.

## 16. Shutdown evidence

Terminate + wait; process exits (Windows TerminateProcess yields exit code
1 — recorded honestly with annotation); port released (connection refused
afterwards). No hang.

## 17. Known limitations

- Single-file JSON durability (slice scope, not a scale claim).
- Interface single but unversioned (carried from VS-D04).
- Evidence-generating run is one instance; per-test hermetic runs repeat the
  same smoke matrix independently (15 deployment tests).
- No Docker/CI execution in this phase; local loopback only.

## 18. Integrity verification

B3-v2 chain intact (443 records); `certification/` and `release/evidence/`
show zero tracked modifications; requirements/ISR/selection/implementation
semantics unchanged (frozen identities recomputed); compiler and evolution
untouched; no observation/evolution work (AST-pinned).

## 19. Explicit observation/evolution STOP boundary

```
DEPLOYMENT + BRING-UP (this artifact)
        X ← STOP HERE
OBSERVATION / EVOLUTION (not authorized, not performed)
```

Logged lines were used only to detect readiness (`Uvicorn running on…`);
no telemetry was collected, interpreted, or fed back. No redeploy based on
observations occurred.

---

*End of VS-D05 artifact. Report follows separately per §28 (uncommitted).*
