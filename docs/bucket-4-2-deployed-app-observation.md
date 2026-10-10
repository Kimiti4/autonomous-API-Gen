# Bucket 4.2 — Deployed-app observation and governed maintenance

Bucket 4.2 extends existing-codebase maintenance to applications that already
have a deployment/runtime surface. It closes the boundary between “the code
exists” and “the deployed system is behaving as expected” without granting
autonomous production authority.

## Contract

The deployed-app path must:

1. identify the deployed revision and environment fingerprint;
2. collect runtime health and verification evidence;
3. compare the observation with the declared deployment baseline;
4. record drift as evidence, separating advisory findings from authoritative
   obligations;
5. admit maintenance/enhancement work only when the work is explicitly
   authorized and within the existing obligation set;
6. require deployment access in addition to explicit authorization for any
   production write;
7. retain an observation digest so later repair/verification work can reference
   exactly what was observed.

## Anti-hallucination rule

A runtime observation, scanner finding, metric regression, or drift finding does
**not** create a new requirement.

An unbound finding is advisory. A finding may drive executable work only when it
is mapped to an already-authorized obligation. This prevents the deployed-app
loop from turning telemetry into endless autonomous feature creation.

## Evidence boundary

deployed system -> runtime observation -> drift classification

- advisory drift -> report only;
- authorized obligation -> governed repair and verification;
- production write -> requires deployment access and human authorization.

A changed source revision or environment fingerprint is a baseline mismatch,
not proof of a defect. It blocks autonomous maintenance admission until the
baseline is re-established or the change is explicitly handled by the governed
workflow.

## Surface compatibility

The Bucket 4.1 surface modes remain authoritative:

- frontend-only;
- backend-only;
- API-contract-only;
- whole application.

Bucket 4.2 adds runtime evidence; it does not create a new surface authority.

## Stop condition

The system stops when the authorized obligation set is complete and the
required verification/deployment-readiness evidence exists. Additional
observations remain advisory unless separately authorized.

Production deployment remains a human-authorized action.


## Maintenance-record input hardening

The maintenance evidence validator rejects whitespace-only observation, obligation,
patch, and authorization identifiers. Verification evidence entries must be non-empty
strings; malformed entries fail closed rather than raising an incidental attribute
error. Focused regression tests cover these invalid inputs.


## Verified repair hand-off

The governed maintenance adapter accepts only a repair report whose digest is valid,
whose source revision matches the runtime observation, whose verification gates all
pass with explicit evidence references, and whose residual list is empty. It binds
the resulting maintenance record to the admitted observation, authorized obligation,
patch digest, and authorization reference, then creates a digest-linked lifecycle
event for Observatory consumption. This adapter records evidence only; it does not
execute repository mutations or deploy. Production-write requests remain blocked
unless the admission independently carries production authorization.

The maintenance hand-off also requires explicit regression evidence with a boolean
outcome and non-empty evidence references; absent, malformed, or detected regressions
block record creation.


## Observatory delivery bridge

`governed_maintenance_observatory.py` provides an explicit, authenticated HTTP
delivery path to the existing `POST /observatory/events` ingestion endpoint. The
bridge validates that the event's observation, obligation, patch, evidence, and
canonical digest still match the maintenance record before sending. It requires an
explicit Observatory base URL and token, uses a bounded request timeout, and accepts
delivery only when Observatory returns an `accepted` response with an event ID.
The combined orchestration helper returns the record, event, and Observatory event ID
only after that acknowledgement.

Configure the caller with the deployed Observatory URL and its API token through the
runtime's secret/configuration mechanism; do not hardcode either value. The bridge
does not start deployments or grant production-write authority. Delivery currently has
no durable local outbox: callers must retain the generated evidence and surface a
delivery failure for controlled retry. The focused tests use a fake HTTP transport and
do not claim that a live Observatory deployment was contacted.


### Observatory transport hardening

The delivery bridge requires HTTPS for non-loopback endpoints; plain HTTP is accepted
only for `localhost`, `127.0.0.1`, or `::1` development targets. Endpoint URLs containing
credentials, query parameters, or fragments are rejected so secrets are not embedded
in URLs. The timeout must be a finite positive number. Requests carry a deterministic
`Idempotency-Key` derived from the verified event digest so a receiver that supports
idempotency can safely deduplicate retries. Acknowledgements must be JSON objects with
the expected accepted status and a non-empty event ID; malformed JSON shapes fail
closed. This remains transport-contract testing, not proof of live Observatory support
for the idempotency header.


## Durable Observatory delivery outbox

`governed_maintenance_outbox.py` adds an explicit SQLite-backed outbox for the
verified maintenance record/event pair. Call `MaintenanceOutbox.enqueue(record, event)`
before attempting network delivery; enqueue is durable and idempotent for the same
event digest and rejects a digest collision with different serialized evidence.
The database uses WAL mode, full synchronous writes, a busy timeout, and short
transactions. Choose a persistent local volume for the database path; an ephemeral
container filesystem is not durable across container replacement.

`deliver_pending(base_url=..., token=...)` claims due events using an expiring lease,
delivers with the authenticated Observatory bridge, and persists acknowledgement or
failure state. Transient failures are retried with bounded exponential backoff. After
the configured attempt limit, an event enters `dead_letter` and remains available for
operator review; `retry_dead_letter(event_digest)` is an explicit recovery action.
The `get(event_digest)` and `summary()` methods expose delivery metadata/counts for
a dashboard or health endpoint without returning the stored evidence payload. Failure
records intentionally retain only the exception class, not raw transport error text,
to avoid persisting URLs or other sensitive details.

The outbox remains a library component for delivery execution; a separate authenticated,
read-only dashboard endpoint exposes only bounded status metadata. It is not yet wired
to an automatically running scheduler. It does not prove that the live Observatory
honors the `Idempotency-Key`; delivery can be retried after an ambiguous network outcome,
so the receiver must implement and verify deduplication for true end-to-end exactly-once
effects. No live endpoint was contacted by offline tests, and no production writes or
deployments are performed.


## Dashboard visibility for maintenance delivery

The authenticated read-only endpoint `GET /api/v1/observation/maintenance-outbox`
returns aggregate queue counts and a bounded list of recent delivery metadata. It
does not return the persisted evidence payload, authorization material, or tokens.
The dashboard's `Governed maintenance delivery` panel reads this endpoint through
the existing same-origin `/observation/` reverse proxy and shows pending, delivering,
delivered, and dead-letter counts plus the recent event digest, attempt count, safe
failure class, and acknowledgement ID.

Configure `MAINTENANCE_OUTBOX_DB_PATH` to a path on persistent storage to enable
the endpoint. If the setting is empty or the store cannot be read, the API returns
an explicit 503 and the dashboard renders an unavailable state; it does not substitute
zero counts or claim the queue is empty. The endpoint accepts the existing platform
API-key auth provider or the signed operator session cookie used by the dashboard.
It is read-only: retries and dead-letter requeue remain controlled operations outside
this dashboard panel.

This is implementation and CI evidence only. The outbox scheduler is not automatically
started by this status endpoint; an operator-controlled worker still needs to call
`deliver_pending()`. Live endpoint credentials, deployed storage durability, receiver
idempotency, and production dashboard behavior remain unverified until configured and
tested in the target environment.

## Controlled one-shot delivery worker

`app.engine.maintenance_outbox_worker` is an explicit one-shot entry point. It
processes at most one bounded batch and exits; it does not run a background daemon,
start automatically with FastAPI, create repair obligations, mutate application
repositories, or deploy applications. An external scheduler or operator may invoke it
at a deliberate cadence, after the target environment and its storage have been
configured.

Run from the `autonomous-api` directory:

```sh
python -m app.engine.maintenance_outbox_worker
```

Required environment variables:

- `MAINTENANCE_OUTBOX_DB_PATH`: SQLite path on a persistent mounted volume.
- `OBSERVATORY_BASE_URL`: Observatory base URL; HTTPS is required except for loopback development.
- `OBSERVATORY_API_TOKEN`: secret token supplied by the deployment's secret manager.

Optional bounded settings:

- `MAINTENANCE_OUTBOX_BATCH_LIMIT`: integer from 1 to 100; defaults to 20.
- `MAINTENANCE_OUTBOX_HTTP_TIMEOUT_SECONDS`: finite positive timeout in seconds; defaults to 5.

The worker reports event digests, delivery status, attempts, and safe failure classes,
but never logs the token, stored evidence payload, raw exception text, or full HTTP
response. Exit code 0 means the batch completed without a reported delivery failure
(including an empty batch); exit code 1 means at least one claimed event failed or was
dead-lettered; exit code 2 means configuration or worker startup failed. Schedule
cadence and alerting are intentionally owned by the deployment operator. Avoid
immediate restart loops: outbox retry timestamps govern delivery eligibility, and
scheduler cadence should respect that backoff.

Offline tests use a fake transport and do not verify live Observatory idempotency.
A timeout after receiver acceptance can still result in a retry, so exactly-once
effects require receiver-side deduplication by the event digest/idempotency key. Do
not enable production scheduling until persistent-volume behavior, credentials,
receiver deduplication, and monitoring are verified in the target environment.
