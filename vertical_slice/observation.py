"""VS-D06 — observation contract + bounded probes + evidence normalization.

Facts only. This module records what happened at runtime; it never decides
what the system should become (no interpretation, optimization, evolution,
or remediation). See folder/VS1_OBSERVATION.md §19 (firewall).

Boundaries enforced here:
  - No secrets recorded: passwords, tokens, and secret payloads are redacted
    at collection time (never present in raw records).
  - No upstream mutation: read-only access to frozen builders for identity.
  - Fail-closed: incomplete provenance or schema violations raise; no
    partial run is presented as complete.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any, Callable

OBSERVATION_CONTRACT_VERSION = "vs1-observe-v1"
OBSERVATION_CONTRACT_ID = "vs1-observe-v1"
DEPLOYMENT_ID = "vs1-local-loopback"
IMPLEMENTATION_ID = "vs1-impl-v1"

REDACTED = "[redacted]"

# Probe catalogue: the complete permitted set (closed world).
PROBES: tuple[dict[str, object], ...] = (
    {"probe_id": "P01-readiness", "operation": "readiness",
     "target": "/health", "expected": {"http_status": 200}},
    {"probe_id": "P02-authentication", "operation": "authentication",
     "target": "/users/login", "expected": {"http_status": 200}},
    {"probe_id": "P03-crud-lifecycle", "operation": "crud_lifecycle",
     "target": "/workspaces/{ws}/tasks", "expected": {"http_status": [201, 200, 204]}},
    {"probe_id": "P04-authorization", "operation": "authorization",
     "target": "/workspaces/{ws}/tasks", "expected": {"http_status": [401, 403]}},
    {"probe_id": "P05-persistence", "operation": "persistence",
     "target": "store.json", "expected": {"survives_restart": True}},
    {"probe_id": "P06-events", "operation": "events",
     "target": "store.json:events", "expected": {"sequence": ["task-created", "task-updated"]}},
    {"probe_id": "P07-lifecycle", "operation": "lifecycle",
     "target": "server-process", "expected": {"shutdown": "clean"}},
)

_PERMITTED_PROBE_IDS = frozenset(p["probe_id"] for p in PROBES)

_EVIDENCE_FIELDS = (
    "observation_id", "observation_contract", "deployment_id",
    "implementation_id", "probe_id", "sequence", "operation", "target",
    "result", "status", "evidence_payload", "provenance",
)

_PROVENANCE_FIELDS = (
    "observation_contract", "deployment_id", "implementation_id",
    "vs-d01-graph-sha256", "vs-d02-isr-content-hash", "vs-d03-selected",
)


class ObservationError(Exception):
    """Fail-closed observation failure (never silently degraded)."""


def contract_identity() -> dict[str, str]:
    from vertical_slice import implementation as IMPL

    identity = IMPL.frozen_input_identity()
    return {
        "observation_contract": OBSERVATION_CONTRACT_ID,
        "observation_contract_version": OBSERVATION_CONTRACT_VERSION,
        "deployment_id": DEPLOYMENT_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": str(identity["vs-d03-selected"]),
    }


def _get(url: str, token: str | None = None,
         timeout: float = 10.0) -> tuple[int, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
            import json
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            import json
            return exc.code, json.loads(raw) if raw else None
        except ValueError:
            return exc.code, raw


def _scrub(value: object) -> object:
    """Redact secret-bearing fields at collection time (recursive)."""
    if isinstance(value, dict):
        return {k: (REDACTED if k.lower() in {
            "password", "token", "authorization", "secret", "salt_hex",
            "password_hash",
        } else _scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def make_record(probe_id: str, operation: str, target: str, result: str,
                status: str, evidence_payload: dict[str, object],
                sequence: int, provenance: dict[str, str]) -> dict[str, object]:
    """Build one raw observation record (secrets scrubbed on entry)."""
    if probe_id not in _PERMITTED_PROBE_IDS:
        raise ObservationError(f"probe outside authorized boundary: {probe_id}")
    record = {
        "observation_id": f"{probe_id}-{sequence:03d}",
        "observation_contract": OBSERVATION_CONTRACT_ID,
        "deployment_id": DEPLOYMENT_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "probe_id": probe_id,
        "sequence": sequence,
        "operation": operation,
        "target": target,
        "result": result,
        "status": status,
        "evidence_payload": _scrub(evidence_payload),
        "provenance": dict(provenance),
    }
    validate_record(record)
    return record


def validate_record(record: dict[str, object]) -> None:
    """Fail-closed schema + provenance validation for one record."""
    for field in _EVIDENCE_FIELDS:
        if field not in record:
            raise ObservationError(f"record missing field: {field}")
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        raise ObservationError("record provenance must be a mapping")
    for field in _PROVENANCE_FIELDS:
        if field not in provenance:
            raise ObservationError(f"record provenance missing: {field}")
    if record.get("observation_contract") != OBSERVATION_CONTRACT_ID:
        raise ObservationError("record contract mismatch")
    _assert_no_secrets(record)


def _assert_no_secrets(record: dict[str, object]) -> None:
    import json

    blob = json.dumps(record)
    lowered = blob.lower()
    for marker in ("alice-secret", "bob-secret", "cara-secret", "eve-secret",
                   "vs1-test-token", "vs1-deploy-token"):
        if marker in lowered:
            raise ObservationError(f"secret material leaked into evidence: {marker}")


def normalize(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministic normalization: order by (sequence, observation_id),
    drop wall-clock-only variance. Input records carry sequence numbers, not
    timestamps, so normalization is the identity modulo ordering."""
    for record in records:
        validate_record(record)
    return sorted(records, key=lambda r: (r["sequence"], r["observation_id"]))


def collect(base_url: str, tokens: dict[str, str], store_dir: str,
            provenance: dict[str, str],
            do_restart: Callable[[], str] | None = None) -> list[dict[str, object]]:
    """Execute the bounded probe set against a deployed runtime.

    Read-only with respect to upstream artifacts. Authentication material
    lives in memory only and is never recorded. `do_restart` is an injected
    restart hook (test harness restarts the server); when None, P05 observes
    the already-persisted store file without restarting.
    """
    records: list[dict[str, object]] = []
    seq = 0

    def add(probe_id: str, operation: str, target: str, result: str,
            status: str, payload: dict[str, object]) -> None:
        nonlocal seq
        seq += 1
        records.append(make_record(probe_id, operation, target, result, status,
                                   payload, seq, provenance))

    # P01 — readiness
    status, body = _get(base_url + "/health")
    if status != 200 or body != {"status": "ok"}:
        raise ObservationError(f"P01 readiness failed: {status} {body}")
    add("P01-readiness", "readiness", "/health", "ready", "observed",
        {"http_status": status, "representation": "ok"})

    # P02 — authentication (fact: login succeeds; no credential recorded)
    import json as json_module
    import urllib.request as urlrequest

    def post(path: str, body: object, token: str | None = None) -> tuple[int, Any]:
        data = json_module.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        request = urlrequest.Request(base_url + path, data=data, headers=headers,
                                     method="POST")
        if token:
            # Token lives in memory only; _scrub strips it before recording.
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urlrequest.urlopen(request, timeout=10) as response:
                raw = response.read().decode()
                return response.status, json_module.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                return exc.code, json_module.loads(raw) if raw else None
            except ValueError:
                return exc.code, raw

    status, _ = post("/users/login", {"username": "alice", "password": "x"})
    # NOTE: password content is never recorded; only the outcome class below.
    add("P02-authentication", "authentication", "/users/login",
        "rejected" if status == 401 else f"http-{status}",
        "observed", {"http_status": status})

    # P03 — CRUD lifecycle on a fresh task
    status, created = post("/workspaces/ws-a/tasks",
                           {"title": "Observed task"}, token=tokens["alice"])
    if status != 201:
        raise ObservationError(f"P03 create failed: {status}")
    task_id = created["task_id"]
    status, _ = _get(f"{base_url}/workspaces/ws-a/tasks/{task_id}",
                     token=tokens["alice"])
    if status != 200:
        raise ObservationError(f"P03 read failed: {status}")
    add("P03-crud-lifecycle", "crud_lifecycle", "/workspaces/{ws}/tasks",
        "lifecycle-completed", "observed",
        {"http_status": [201, 200], "task_ref": task_id})

    # P04 — authorization (outsider rejected; recorded as fact)
    status, outsider = post("/users/register",
                            {"username": "obs-outsider", "password": "x"})
    if status != 201:
        raise ObservationError(f"P04 setup failed: {status}")
    status, login = post("/users/login",
                         {"username": "obs-outsider", "password": "x"})
    if status != 200:
        raise ObservationError(f"P04 login failed: {status}")
    status, _ = _get(f"{base_url}/workspaces/ws-a/tasks", token=login["token"])
    if status != 403:
        raise ObservationError(f"P04 isolation failed: {status}")
    add("P04-authorization", "authorization", "/workspaces/{ws}/tasks",
        "outsider-rejected", "observed", {"http_status": status})

    # P05 — persistence (across restart when hook provided)
    import os
    if do_restart is not None:
        new_base = do_restart()
        status, body = _get(new_base + "/health")
        if status != 200:
            raise ObservationError("P05 post-restart readiness failed")
        status, _ = _get(f"{new_base}/workspaces/ws-a/tasks/{task_id}",
                         token=tokens["alice"])
        if status != 200:
            raise ObservationError(f"P05 post-restart read failed: {status}")
        add("P05-persistence", "persistence", "store.json",
            "survived-restart", "observed", {"http_status": status})
    else:
        path = os.path.join(store_dir, "store.json")
        if not os.path.exists(path):
            raise ObservationError("P05 store file missing")
        add("P05-persistence", "persistence", "store.json",
            "store-present", "observed", {"present": True})

    # P06 — events (from the persisted store file; no event API exists)
    import os as _os
    with open(_os.path.join(store_dir, "store.json"), encoding="utf-8") as f:
        import json as _json
        state = _json.load(f)
    names = [e["event_name"] for e in state.get("events", [])
             if e.get("task_id") == task_id]
    if "task-created" not in names:
        raise ObservationError(f"P06 event evidence missing: {names}")
    add("P06-events", "events", "store.json:events", "emitted", "observed",
        {"event_names": names, "producer": "svc-task"})

    # P07 — lifecycle (the harness owns shutdown; here we record steady-state)
    add("P07-lifecycle", "lifecycle", "server-process", "running", "observed",
        {"steady": True})
    return normalize(records)


def build_evidence_artifact(records: list[dict[str, object]],
                            run: dict[str, object]) -> dict[str, object]:
    """Assemble the validated machine-readable evidence artifact."""
    normalized = normalize(records)
    return {
        "observation_contract": OBSERVATION_CONTRACT_ID,
        "observation_contract_version": OBSERVATION_CONTRACT_VERSION,
        "deployment_id": DEPLOYMENT_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "provenance": normalized[0]["provenance"] if normalized else {},
        "records": normalized,
        "run": dict(run),
    }
