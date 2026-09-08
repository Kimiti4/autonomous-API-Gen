"""VS-D17 — runtime observation & production-feedback capture (mechanical only).

Observes the D16-deployed vs1-impl-v2 system under a deterministic bounded
workload and records mechanical runtime evidence. Performs NO interpretation,
authorization, mutation, optimization, regeneration, or redeployment. Anomalies
are detected and recorded; their meaning belongs to D18.

Raw records retain audit-only runtime values (timestamps, latency). The
committed normalized representation excludes PID, ephemeral ports,
wall-clock timestamps, and random identifiers so repeated identical workloads
produce equivalent normalized evidence. Secrets are never persisted: any
secret shape in a record fails closed before write.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from vertical_slice import deployment_v2 as DEP

OBSERVATION_CONTRACT_VERSION = "vs1-runtime-observe-v1"
OBSERVATION_POLICY = "vs1-runtime-observe-v1"
EXECUTION_TARGET = "local-uvicorn-loopback"

STATUS_VALUES: tuple[str, ...] = ("PASS", "FAIL", "UNDETERMINED", "BLOCKED")

RECORD_FIELDS: tuple[str, ...] = (
    "observation_id",
    "execution_id",
    "deployment_id",
    "implementation_id",
    "architecture_id",
    "operation",
    "expected_class",
    "observed_class",
    "status",
    "measurement",
    "timestamp",
    "provenance",
)

# Fields with no semantic content for equivalence (dropped in normalization).
EPHEMERAL_FIELDS: tuple[str, ...] = ("timestamp",)

# Measurement keys that are inherently runtime-variable (kept raw, dropped
# from normalized; presence is recorded instead as "<key>_measured").
VARIABLE_MEASUREMENTS: tuple[str, ...] = ("latency_ms", "bound_port", "pid")

_SECRET_SHAPE = re.compile(
    r"(password|passwd|secret|api_key|salt|credential|session_cookie"
    r"|private_key|bearer [a-z0-9\-_]+|\"token\"\s*:\s*\"[^\"]+\")",
    re.IGNORECASE,
)


class ObservationError(Exception):
    """Fail-closed observation failure (including secret-safety trips)."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def verify_deployment_identity() -> dict[str, str]:
    """Fail-closed gate: the observed deployment must be D16's v2 deployment."""
    identities = DEP.verify_upstream()
    contract = DEP.build_contract()
    if contract["deployment_id"] != "vs1-deploy-v2":
        raise ObservationError("deployment identity drift")
    if contract["deployment_target"] != EXECUTION_TARGET:
        raise ObservationError("execution target drift")
    if contract.get("production_authorization") is not False:
        raise ObservationError("production authorization drift")
    return {
        "deployment_id": contract["deployment_id"],  # type: ignore[dict-item]
        "implementation_id": identities["d15_implementation"],
        "implementation_hash": identities["d15_implementation_hash"],
        "architecture_id": identities["d14_architecture"],
        "architecture_hash": DEP.ARCHITECTURE_HASH,
        "isr_hash": identities["d02_isr"],
        "deployment_target": EXECUTION_TARGET,
    }


def provenance_block(execution_id: str) -> dict[str, str]:
    identity = verify_deployment_identity()
    return {
        "execution_id": execution_id,
        "deployment_id": identity["deployment_id"],
        "implementation_id": identity["implementation_id"],
        "implementation_hash": identity["implementation_hash"],
        "architecture_id": identity["architecture_id"],
        "architecture_hash": identity["architecture_hash"],
        "isr_hash": identity["isr_hash"],
        "graph_hash": DEP.GRAPH_HASH,
        "requirements_ref": "folder/VS1_REQUIREMENTS.md",
    }


def observe(*, observation_id: str, execution_id: str, operation: str,
            expected_class: str, observed_class: str | None,
            status: str, measurement: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mechanical record factory. No inference: unestablished results must be
    passed as observed_class=None with status UNDETERMINED/BLOCKED."""
    if status not in STATUS_VALUES:
        raise ObservationError(f"unknown status: {status}")
    if observed_class is None and status in ("PASS", "FAIL"):
        raise ObservationError("PASS/FAIL requires an observed class")
    record = {
        "observation_id": observation_id,
        "execution_id": execution_id,
        "deployment_id": DEP.DEPLOYMENT_ID,
        "implementation_id": DEP.IMPLEMENTATION_ID,
        "architecture_id": DEP.ARCHITECTURE_ID,
        "operation": operation,
        "expected_class": expected_class,
        "observed_class": observed_class,
        "status": status,
        "measurement": dict(measurement or {}),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": provenance_block(execution_id),
    }
    return validate_record(record)


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Schema + provenance validation, fail-closed. Returns the record."""
    if not isinstance(record, dict):
        raise ObservationError("observation malformed")
    for field in RECORD_FIELDS:
        if field not in record:
            raise ObservationError(f"observation missing field: {field}")
    if record["status"] not in STATUS_VALUES:
        raise ObservationError("observation status invalid")
    if record["observed_class"] is None and record["status"] in ("PASS", "FAIL"):
        raise ObservationError("PASS/FAIL requires an observed class")
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        raise ObservationError("provenance missing")
    for field in ("execution_id", "deployment_id", "implementation_id",
                  "architecture_id", "isr_hash"):
        if not provenance.get(field):
            raise ObservationError(f"provenance missing: {field}")
    assert_secret_safe(record)
    return record


def assert_secret_safe(payload: object) -> None:
    """Fail closed if any secret shape or raw credential material is present."""
    blob = _canon(payload)
    if _SECRET_SHAPE.search(blob):
        raise ObservationError("secret material in observation payload")


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Deterministic normalized form: drop ephemeral fields and variable
    measurements (recording their presence), keep everything semantic."""
    validate_record(record)
    measurement = {
        key: value for key, value in record["measurement"].items()
        if key not in VARIABLE_MEASUREMENTS
    }
    for key in VARIABLE_MEASUREMENTS:
        if key in record["measurement"]:
            measurement[key + "_measured"] = True
    normalized = {key: record[key] for key in RECORD_FIELDS
                  if key not in EPHEMERAL_FIELDS}
    normalized["measurement"] = measurement
    return normalized


def normalize_evidence(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(records, key=lambda r: r["observation_id"])
    return [normalize_record(record) for record in ordered]


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in STATUS_VALUES}
    for record in records:
        counts[record["status"]] += 1
    return {
        "observation_count": len(records),
        "status_counts": counts,
        "request_count": sum(1 for r in records
                             if r["operation"].startswith("http.")),
        "successful_request_count": sum(
            1 for r in records
            if r["operation"].startswith("http.") and r["status"] == "PASS"),
        "rejected_request_count": sum(
            1 for r in records
            if r["operation"].startswith("http.") and r["observed_class"] in
            ("http-401", "http-403", "http-422")),
    }


def check_constitutional_invariants() -> dict[str, str]:
    """Mechanical recomputation: ISR/requirements/implementation/architecture/
    deployment identity unchanged. No repair attempted."""
    identities = DEP.verify_upstream()
    contract = DEP.build_contract()
    results = {
        "isr_unchanged": "PASS" if identities["d02_isr"] == DEP.ISR_HASH else "FAIL",
        "requirements_unchanged": "PASS" if identities["d01_graph"] == DEP.GRAPH_HASH else "FAIL",
        "implementation_unchanged": "PASS" if identities["d15_implementation_hash"] == DEP.IMPLEMENTATION_HASH else "FAIL",
        "architecture_unchanged": "PASS" if identities["d14_selection_hash"] == DEP.SELECTION_HASH else "FAIL",
        "deployment_unchanged": "PASS" if DEP.contract_hash(contract) == DEP.contract_hash() else "FAIL",
    }
    if set(results.values()) != {"PASS"}:
        raise ObservationError(f"constitutional invariant failure: {results}")
    return results


def check_security_invariants(records: list[dict[str, Any]]) -> dict[str, str]:
    """Mechanical: auth enforced, authz enforced, isolation preserved, no
    secret leakage. Reads recorded classes only; decides nothing further."""
    by_id = {r["observation_id"]: r for r in records}
    required = ("auth.invalid-rejected", "auth.authenticated-request",
                "authz.outsider-rejected", "authz.role-rejected",
                "authz.permitted-operation")
    results = {}
    for obs_id in required:
        record = by_id.get(obs_id)
        results[obs_id] = ("PASS" if record is not None and record["status"] == "PASS"
                           else "FAIL")
    try:
        for record in records:
            assert_secret_safe(record)
        results["no-secret-leakage"] = "PASS"
    except ObservationError:
        results["no-secret-leakage"] = "FAIL"
    if set(results.values()) != {"PASS"}:
        raise ObservationError(f"security invariant failure: {results}")
    return results


def check_behavioral_invariants(records: list[dict[str, Any]]) -> dict[str, str]:
    """Mechanical: CRUD lifecycle, restart persistence, events, clean shutdown."""
    by_id = {r["observation_id"]: r for r in records}
    required = ("crud.read-after-update", "crud.read-after-delete",
                "persist.restart-state", "events.lifecycle-emitted",
                "lifecycle.shutdown-clean")
    results = {obs_id: ("PASS" if by_id.get(obs_id) is not None
                        and by_id[obs_id]["status"] == "PASS" else "FAIL")
               for obs_id in required}
    if set(results.values()) != {"PASS"}:
        raise ObservationError(f"behavioral invariant failure: {results}")
    return results


def run_online_workload(base: str, execution_id: str,
                        transport: Callable[..., tuple[int, object]],
                        admin_token: str) -> list[dict[str, Any]]:
    """Deterministic bounded online workload (no restart/shutdown: the caller
    owns process lifecycle and appends those records via observe()).

    The caller seeds workspace ``ws-obs`` plus a bootstrap admin BEFORE
    startup and injects the admin token; all other users register through
    the observed API. This module never persists credential material."""
    records: list[dict[str, Any]] = []

    def step(observation_id: str, operation: str, expected: str,
             action: Callable[[], tuple[str | None, str, dict[str, Any]]]) -> None:
        try:
            observed, status, measurement = action()
        except Exception:
            observed, status, measurement = None, "UNDETERMINED", {}
        records.append(observe(
            observation_id=observation_id, execution_id=execution_id,
            operation=operation, expected_class=expected,
            observed_class=observed, status=status, measurement=measurement))

    def timed(method: str, url: str, body: object = None,
              token: str | None = None) -> tuple[int, float]:
        started = time.perf_counter()
        status, _ = transport(method, url, body, token) if token is not None \
            else transport(method, url, body)
        return status, (time.perf_counter() - started) * 1000.0

    session: dict[str, str] = {}

    def do_readiness() -> tuple[str | None, str, dict[str, Any]]:
        started = time.perf_counter()
        status, body = transport("GET", base + "/health", None)
        latency = (time.perf_counter() - started) * 1000.0
        observed = f"http-{status}" if body == {"status": "ok"} else f"http-{status}-bad-body"
        return observed, ("PASS" if observed == "http-200" else "FAIL"), \
            {"http_status": status, "latency_ms": round(latency, 3)}

    step("lifecycle.readiness", "http.readiness", "http-200", do_readiness)

    def do_register() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/users/register",
                                 {"username": "obs-alice", "password": "x" * 16})
        assert isinstance(body, dict)
        session["alice_id"] = str(body.get("user_id", ""))
        return f"http-{status}", ("PASS" if status == 201 else "FAIL"), {"http_status": status}

    step("auth.register", "http.register", "http-201", do_register)

    def do_login() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/users/login",
                                 {"username": "obs-alice", "password": "x" * 16})
        assert isinstance(body, dict)
        session["alice"] = str(body.get("token", ""))
        return f"http-{status}", ("PASS" if status == 200 and session["alice"] else "FAIL"), \
            {"http_status": status, "token_received": bool(session.get("alice"))}

    step("auth.login", "http.login", "http-200", do_login)

    def do_invalid() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/users/login",
                              {"username": "obs-alice", "password": "wrong"})
        return f"http-{status}", ("PASS" if status == 401 else "FAIL"), {"http_status": status}

    step("auth.invalid-rejected", "http.login-invalid", "http-401", do_invalid)

    def do_grant() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/workspaces/ws-obs/members",
                              {"user_id": session["alice_id"], "role": "member"},
                              admin_token)
        return f"http-{status}", ("PASS" if status == 201 else "FAIL"), {"http_status": status}

    step("authz.admin-grant", "http.admin-grant", "http-201", do_grant)

    def do_authenticated() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = timed("GET", base + "/workspaces/ws-obs/tasks", token=session["alice"])
        return f"http-{status}", ("PASS" if status == 200 else "FAIL"), {"http_status": status}

    step("auth.authenticated-request", "http.authenticated-list", "http-200", do_authenticated)

    def do_permitted() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/workspaces/ws-obs/tasks",
                                 {"title": "Observed task"}, token=session["alice"])
        assert isinstance(body, dict)
        session["task_id"] = str(body.get("task_id", ""))
        return f"http-{status}", ("PASS" if status == 201 and session["task_id"] else "FAIL"), \
            {"http_status": status, "task_recorded": bool(session.get("task_id"))}

    step("authz.permitted-operation", "http.task-create", "http-201", do_permitted)

    def do_outsider() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/users/register",
                                 {"username": "obs-outsider", "password": "y" * 16})
        assert isinstance(body, dict)
        status, body = transport("POST", base + "/users/login",
                                 {"username": "obs-outsider", "password": "y" * 16})
        assert isinstance(body, dict)
        outsider = str(body.get("token", ""))
        status, _ = transport("GET", base + "/workspaces/ws-obs/tasks", token=outsider)
        return f"http-{status}", ("PASS" if status == 403 else "FAIL"), {"http_status": status}

    step("authz.outsider-rejected", "http.outsider-list", "http-403", do_outsider)

    def do_role() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/workspaces/ws-obs/members",
                              {"user_id": session["alice_id"]}, token=session["alice"])
        return f"http-{status}", ("PASS" if status == 403 else "FAIL"), {"http_status": status}

    step("authz.role-rejected", "http.member-add-forbidden", "http-403", do_role)

    def crud_read(path: str, obs: str, op: str, expect: str,
                  check: Callable[[object], bool] | None = None) -> None:
        def action() -> tuple[str | None, str, dict[str, Any]]:
            started = time.perf_counter()
            status, body = transport("GET", base + path, None, session["alice"])
            latency = (time.perf_counter() - started) * 1000.0
            observed = f"http-{status}"
            ok = status == int(expect.split("-")[1]) and (check(body) if check else True)
            return observed, ("PASS" if ok else "FAIL"), \
                {"http_status": status, "latency_ms": round(latency, 3)}
        step(obs, op, expect, action)

    def do_crud_create() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/workspaces/ws-obs/tasks",
                                 {"title": "Lifecycle task"}, token=session["alice"])
        assert isinstance(body, dict)
        session["lc_task"] = str(body.get("task_id", ""))
        return f"http-{status}", ("PASS" if status == 201 else "FAIL"), {"http_status": status}

    step("crud.create", "http.crud-create", "http-201", do_crud_create)
    crud_read(f"/workspaces/ws-obs/tasks/{session.get('lc_task', 'missing')}",
              "crud.read", "http.crud-read", "http-200")

    def do_update() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("PATCH",
                                 base + f"/workspaces/ws-obs/tasks/{session['lc_task']}",
                                 {"status": "done"}, session["alice"])
        assert isinstance(body, dict)
        ok = status == 200 and body.get("status") == "done"
        return f"http-{status}", ("PASS" if ok else "FAIL"), {"http_status": status}

    step("crud.update", "http.crud-update", "http-200", do_update)
    crud_read(f"/workspaces/ws-obs/tasks/{session.get('lc_task', 'missing')}",
              "crud.read-after-update", "http.crud-read-after-update", "http-200",
              check=lambda body: isinstance(body, dict) and body.get("status") == "done")

    def do_delete() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("DELETE",
                              base + f"/workspaces/ws-obs/tasks/{session['lc_task']}",
                              None, session["alice"])
        return f"http-{status}", ("PASS" if status == 204 else "FAIL"), {"http_status": status}

    step("crud.delete", "http.crud-delete", "http-204", do_delete)
    crud_read(f"/workspaces/ws-obs/tasks/{session.get('lc_task', 'missing')}",
              "crud.read-after-delete", "http.crud-read-after-delete", "http-422")

    return records


def assemble_evidence(records: list[dict[str, Any]], execution_id: str,
                      generated_at: str) -> dict[str, Any]:
    """Canonical evidence: raw observations (secret-safe) + normalized form +
    timestamp-independent content hash. Interpretation-free."""
    identity = verify_deployment_identity()
    for record in records:
        validate_record(record)
    normalized = normalize_evidence(records)
    evidence: dict[str, Any] = {
        "contract": OBSERVATION_CONTRACT_VERSION,
        "policy": OBSERVATION_POLICY,
        "execution_id": execution_id,
        "deployment_id": identity["deployment_id"],
        "implementation_id": identity["implementation_id"],
        "implementation_hash": identity["implementation_hash"],
        "architecture_id": identity["architecture_id"],
        "architecture_hash": identity["architecture_hash"],
        "isr_hash": identity["isr_hash"],
        "deployment_target": identity["deployment_target"],
        "summary": summarize(records),
        "constitutional_invariants": check_constitutional_invariants(),
        "security_invariants": check_security_invariants(records),
        "behavioral_invariants": check_behavioral_invariants(records),
        "observations": sorted(records, key=lambda r: r["observation_id"]),
        "normalized": normalized,
        "production_authorization": False,
        "authorization_mode": DEP.AUTHORIZATION_MODE,
        "provenance": provenance_block(execution_id) | {"generated_at": generated_at},
    }
    _normalized = {k: v for k, v in evidence.items() if k != "provenance"}
    _provenance = dict(evidence["provenance"])
    _provenance.pop("generated_at", None)
    _normalized["provenance"] = _provenance
    evidence["normalized_hash"] = _sha(_canon(_normalized))
    return evidence
