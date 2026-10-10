# Maintenance Recovery Evidence Review

**Review date:** 2026-10-10  
**Reviewed main commit:** `de7547a6ce60934a869253d5a641456f3c38ccc8`  
**Scope:** maintenance outbox persistence/recovery, Observatory retry idempotency, one-shot worker safety.  
**Certification rule:** a test proves only the behavior and environment it actually exercises. Unit/in-process tests do not certify a deployed staging environment.

## Results

| Requirement | Result | Evidence and boundary |
|---|---|---|
| Persistent volume: SQLite survives container replacement while host data directory is preserved | **UNKNOWN** | `autonomous-api/docker-compose.yml` configures `MAINTENANCE_OUTBOX_DB_PATH=/app/data/maintenance-outbox.sqlite3` and bind-mounts `./data:/app/data`. `test_outbox_sqlite_database_survives_reopen_with_pending_item` verifies SQLite data survives reopening the same file. This does **not** execute a Docker container replacement or verify the actual host directory/mount on a running host. Do not certify staging/production persistence until a replacement test records the same host path, database digest/row identity before and after, and successful read/retry after replacement. |
| Process interruption: expired delivery lease is reclaimed and delivered | **PASS (automated test scope)** | `test_expired_delivery_lease_is_recovered_after_reopen` claims an item, leaves it in `delivering`, advances the test clock past the lease, reopens the outbox, and verifies delivery, attempt count, persisted event ID, and final queue counts. This simulates interruption; it is not a real process-kill/container-kill test. |
| Lost ACK: retry returns original Observatory event ID without duplicate event | **PASS (in-process integration scope)** | `tests/test_governed_maintenance_lost_ack_retry.py::test_lost_ack_retry_is_deduplicated_by_observatory` sends an event to an in-process Observatory TestClient, deliberately drops the first ACK after receiver commit, retries after backoff, verifies the original deterministic event ID, and asserts event count remains one. No external/live Observatory endpoint is exercised. |
| Worker bounded execution | **PASS (unit-test scope)** | `tests/test_maintenance_outbox_worker.py::test_worker_delivers_only_one_bounded_batch` verifies one call with configured batch limit and timeout; parameterized tests reject batch limits outside 1–100 and invalid timeout values. The worker is one-shot and does not start a daemon/scheduler. |
| Worker logs are sanitized | **PASS (unit-test scope)** | `test_worker_logs_metadata_without_logging_token_or_evidence` verifies the configured token and evidence payload are absent from captured logs. The worker logs only delivery metadata and a safe error classification; CLI startup failures log exception class rather than raw exception text. |
| Authentication and read-only status endpoint | **PASS (unit-test scope)** | `tests/test_maintenance_outbox_routes.py` verifies API-key-provider auth, signed operator-session fallback, anonymous rejection, disabled/uninitialized storage behavior, bounded status metadata, and no storage initialization on GET. This is not an external deployment penetration test. |
| Failure handling / explicit exit status | **PASS (unit-test scope)** | Worker CLI returns 1 when a batch contains delivery failures, 0 when there are no due events, and 2 on startup/configuration exceptions. Outbox tests cover backoff, dead-letter/requeue, invalid configuration, and expired-lease recovery. |
| Staging/production operational behavior | **UNKNOWN** | No live staging host, real mounted volume replacement, external Observatory endpoint, production credentials, or externally managed scheduler was exercised as part of this review. |

## Overall disposition

**Not fully certified.** Automated recovery/idempotency/safety tests pass within their stated scopes, but persistent-volume behavior under actual container replacement remains **UNKNOWN**, as does staging/production behavior. The one-shot worker intentionally does not enable its own schedule. Keep scheduling external and explicitly operated; do not treat this report as authorization for production repair/deployment.

## Required closure evidence for the UNKNOWN volume result

1. Identify the staging host and the exact host directory bound to `/app/data`.
2. With a non-sensitive test event, record the database path, row/event digest, status, and a database-file checksum or equivalent integrity evidence.
3. Replace/recreate only the app container while preserving that host directory; do not delete the data directory or volume.
4. Verify the same event row and digest remain, the database opens cleanly, and a controlled retry can finish without a duplicate Observatory event.
5. Attach command output and timestamps to the run evidence. Redact credentials and payloads.
6. Record the result as PASS only if all checks succeed; otherwise FAIL or UNKNOWN, with the failure reason. Repeat for each materially different deployment configuration.
