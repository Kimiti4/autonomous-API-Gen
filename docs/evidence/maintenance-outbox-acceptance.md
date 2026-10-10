# Maintenance outbox acceptance evidence

**Evidence baseline:** `main` at `cbe0a004055bb28fb6938a8b833075c035a45e5e`  
**Review date:** 2026-10-10  
**Rule:** `UNKNOWN` is not `PASS`. Unit/in-process tests do not certify a deployed staging environment.

## Acceptance matrix

| Requirement | Status | Evidence and boundary |
|---|---|---|
| SQLite state survives process restart/reopen | **PASS** | `autonomous-api/tests/test_governed_maintenance_outbox.py::test_outbox_sqlite_database_survives_reopen_with_pending_item` verifies a pending row and idempotent enqueue after reopening the same SQLite file. |
| SQLite state survives container replacement while host data is preserved | **PASS (Docker bind-mount proof)** | The dedicated [Maintenance Outbox Container Recovery workflow](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38056374753) passed. It writes a committed SQLite row in one disposable container, removes that container, then reads the row from a replacement container with the same host bind mount. Compose maps `./data:/app/data` and configures `MAINTENANCE_OUTBOX_DB_PATH=/app/data/maintenance-outbox.sqlite3`. This proves bind-mount persistence, not a live application deployment or staging rollout. |
| Expired delivery lease is reclaimed and delivered after worker interruption | **PASS (automated simulation)** | `test_expired_delivery_lease_is_recovered_after_reopen` claims an item, advances the test clock beyond the lease, reopens the DB, retries delivery, and asserts `delivered`, attempt count 2, event ID, and queue counts. This simulates interruption; it is not a live process-kill/staging test. |
| Lost acknowledgement retry returns original Observatory event ID without duplicate events | **PASS (in-process integration)** | `autonomous-api/tests/test_governed_maintenance_lost_ack_retry.py::test_lost_ack_retry_is_deduplicated_by_observatory` commits the event in the local TestClient, simulates losing the first ACK, retries, then asserts the original ID and event count 1. No external Observatory endpoint was contacted. |
| Worker batch is bounded; timeout/configuration validated | **PASS (unit tests)** | `autonomous-api/tests/test_maintenance_outbox_worker.py` checks one bounded batch, limit and timeout forwarding, missing required settings, out-of-range limits, and invalid timeout. Batch limit is constrained to 1–100; default 20. |
| Logs avoid secrets/evidence payloads; failures return non-zero | **PASS (unit tests)** | Worker tests assert the API token and evidence payload are absent from logs and that a failed/dead-letter batch returns exit code 1. Startup/configuration exceptions are logged by class only and return exit code 2. |
| Dashboard outbox endpoint requires authentication and exposes metadata only | **PASS (unit tests)** | `autonomous-api/tests/test_maintenance_outbox_routes.py` checks API-key-provider auth, signed operator-session fallback, anonymous rejection, bounded metadata without payload, and fail-closed behavior when storage is missing/uninitialized. |
| Live staging volume, auth, delivery, alerting, and failure recovery | **UNKNOWN** | No staging endpoint/container was exercised in this evidence run. Do not infer production or staging certification from CI. |

## Operational constraints

- Worker is one-shot: `python -m app.engine.maintenance_outbox_worker`; it is not auto-started by the API.
- Required configuration: `MAINTENANCE_OUTBOX_DB_PATH`, `OBSERVATORY_BASE_URL`, and `OBSERVATORY_API_TOKEN`.
- External scheduler cadence, alerting, and monitoring remain operator-managed.
- Preserve the host `autonomous-api/data` directory during container replacement. Deleting or replacing that directory invalidates the persistence assumption.
- Do not enable a production scheduler or perform production writes as part of this verification.

## CI snapshot

At the evidence baseline, GitHub Actions reported 37 checks for the main commit: 36 successful and 1 skipped; no failed or pending checks. The dedicated Docker replacement workflow subsequently passed: [run 38056374753](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38056374753). Other PR checks were still in progress at the last poll. This is not proof of staging behavior or a full application-container rollout.

## Status update rule

After the dedicated Docker workflow completes, update the container-replacement row with its run URL and result. Keep staging acceptance `UNKNOWN` until a controlled staging test records the target, retained volume identity/path, before/after database digest or row assertions, worker result, Observatory event ID, and no-duplicate count.
