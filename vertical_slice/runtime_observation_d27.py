"""VS-D27 — runtime observation of the D26 deployment artifact (mechanical only).

Observes vs1-impl-obj001-v1 (D26 deployment vs1-deploy-obj001-4ca3d24c…)
under a bounded priority workload on a loopback fixture. Records raw
facts (statuses, counts, mechanical measurements) with full provenance.
No interpretation, authorization, mutation, or evolution. Observation IDs
reuse the D17 vocabulary where semantics match so the proven invariant
checks apply unchanged.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from vertical_slice import runtime_observation as OBS

OBSERVATION_CONTRACT = "vs1-runtime-observe-d27"
EXECUTION_ID = "vs1-d27-run-001"
DEPLOYMENT_ID = "vs1-deploy-obj001-4ca3d24c13561599"
IMPLEMENTATION_ID = "vs1-impl-obj001-v1"
IMPLEMENTATION_HASH = (
    "7dbbf34fe75660f1aa7355e7fc68d7d427467f0d8e2278e29357e666d30207f4"
)
ARCHITECTURE_ID = "vs1-obj001-candidate-313b071dd7d4"
OBJECTIVE_ID = "VS1-OBJ-001"
ISR_HASH = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
D26_DEPLOYMENT_HASH = (
    "4ca3d24c1356159944a411da5a4c1901777d8725b51a1bb0b1d6c16dff9f8679"
)
D26_MANIFEST_HASH = (
    "31a7d9fc0aefe7d095c60593f12480313b4474165130f237d1c03e1af33de382"
)


class ObservationError(Exception):
    """Fail-closed observation failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def verify_deployment_identity() -> dict[str, str]:
    """The observed process must be the D26 artifact (fail-closed)."""
    from vertical_slice import implementation_d25 as IMPLD25
    from vertical_slice import deployment_d26 as DEP26

    upstream = IMPLD25.verify_upstream()
    if upstream["d24"]["selected_candidate"] != ARCHITECTURE_ID:
        raise ObservationError("architecture drift")
    record = IMPLD25._load_json(
        "vertical_slice/implementation_d25_evidence.json")
    if record.get("implementation_hash") != IMPLEMENTATION_HASH:
        raise ObservationError("implementation drift")
    manifest = DEP26.load_json(
        Path("vertical_slice/deployment_d26_manifest.json"), "D26 manifest")
    if manifest.get("deployment_id") != DEPLOYMENT_ID:
        raise ObservationError("deployment drift")
    if manifest.get("deployment_hash") != D26_DEPLOYMENT_HASH:
        raise ObservationError("deployment hash drift")
    return {
        "deployment_id": DEPLOYMENT_ID,
        "deployment_hash": D26_DEPLOYMENT_HASH,
        "manifest_hash": D26_MANIFEST_HASH,
        "implementation_id": IMPLEMENTATION_ID,
        "implementation_hash": IMPLEMENTATION_HASH,
        "architecture_id": ARCHITECTURE_ID,
        "objective_id": OBJECTIVE_ID,
        "isr_hash": ISR_HASH,
    }


def provenance_block(execution_id: str = EXECUTION_ID) -> dict[str, str]:
    identity = verify_deployment_identity()
    return {
        "execution_id": execution_id,
        "deployment_id": identity["deployment_id"],
        "deployment_hash": identity["deployment_hash"],
        "implementation_id": identity["implementation_id"],
        "implementation_hash": identity["implementation_hash"],
        "architecture_id": identity["architecture_id"],
        "objective_id": identity["objective_id"],
        "isr_hash": identity["isr_hash"],
        "graph_hash": "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526",
        "requirements_ref": "folder/VS1_REQUIREMENTS.md",
    }


def observe(*, observation_id: str, execution_id: str = EXECUTION_ID,
            operation: str, expected_class: str,
            observed_class: str | None, status: str,
            measurement: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mechanical record with D27 provenance (same schema/firewall as D17)."""
    if status not in OBS.STATUS_VALUES:
        raise ObservationError(f"unknown status: {status}")
    if observed_class is None and status in ("PASS", "FAIL"):
        raise ObservationError("PASS/FAIL requires an observed class")
    record = {
        "observation_id": observation_id,
        "execution_id": execution_id,
        "deployment_id": DEPLOYMENT_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "architecture_id": ARCHITECTURE_ID,
        "operation": operation,
        "expected_class": expected_class,
        "observed_class": observed_class,
        "status": status,
        "measurement": dict(measurement or {}),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": provenance_block(execution_id),
    }
    return OBS.validate_record(record)


def run_priority_workload(base: str, execution_id: str,
                          transport: Callable[..., tuple[int, object]],
                          admin_token: str) -> list[dict[str, Any]]:
    """Bounded priority workload. Raw facts only; no conclusions."""
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
                                 {"username": "obs27-alice", "password": "x" * 16})
        assert isinstance(body, dict)
        session["alice_id"] = str(body.get("user_id", ""))
        return f"http-{status}", ("PASS" if status == 201 else "FAIL"), {"http_status": status}

    step("auth.register", "http.register", "http-201", do_register)

    def do_login() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/users/login",
                                 {"username": "obs27-alice", "password": "x" * 16})
        assert isinstance(body, dict)
        session["alice"] = str(body.get("token", ""))
        return f"http-{status}", ("PASS" if status == 200 and session["alice"] else "FAIL"), \
            {"http_status": status, "token_received": bool(session.get("alice"))}

    step("auth.login", "http.login", "http-200", do_login)

    def do_invalid() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/users/login",
                              {"username": "obs27-alice", "password": "wrong"})
        return f"http-{status}", ("PASS" if status == 401 else "FAIL"), {"http_status": status}

    step("auth.invalid-rejected", "http.login-invalid", "http-401", do_invalid)

    def do_grant() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/workspaces/ws-obs/members",
                              {"user_id": session["alice_id"], "role": "member"},
                              admin_token)
        return f"http-{status}", ("PASS" if status == 201 else "FAIL"), {"http_status": status}

    step("authz.admin-grant", "http.admin-grant", "http-201", do_grant)

    def do_authenticated() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("GET", base + "/workspaces/ws-obs/tasks",
                              None, session["alice"])
        return f"http-{status}", ("PASS" if status == 200 else "FAIL"), {"http_status": status}

    step("auth.authenticated-request", "http.authenticated-list", "http-200", do_authenticated)

    # The HIGH-priority creation doubles as the observed permitted
    # operation (same real response recorded under both IDs; no stubbed
    # statuses anywhere in this workload).
    permitted: dict[str, Any] = {}

    for prio in ("LOW", "MEDIUM", "HIGH"):
        def make_create(priority: str):
            def action() -> tuple[str | None, str, dict[str, Any]]:
                status, body = transport(
                    "POST", base + "/workspaces/ws-obs/tasks",
                    {"title": f"Prio {priority}", "priority": priority},
                    session["alice"])
                assert isinstance(body, dict)
                ok = status == 201 and body.get("priority") == priority
                session[f"task_{priority.lower()}"] = str(body.get("task_id", ""))
                if priority == "HIGH":
                    permitted.update(
                        observed=f"http-{status}",
                        status="PASS" if ok else "FAIL",
                        measurement={"http_status": status,
                                     "derived_from": "priority.create-high"})
                return f"http-{status}", ("PASS" if ok else "FAIL"), {"http_status": status}
            return action
        step(f"priority.create-{prio.lower()}", "http.priority-create", "http-201",
             make_create(prio))

    records.append(observe(
        observation_id="authz.permitted-operation", execution_id=execution_id,
        operation="http.task-create-observed", expected_class="http-201",
        observed_class=permitted.get("observed"),
        status=permitted.get("status", "UNDETERMINED"),
        measurement=permitted.get("measurement", {})))

    def do_filter(priority: str, expect_count: int | None = None):
        def action() -> tuple[str | None, str, dict[str, Any]]:
            status, body = transport(
                "GET", base + f"/workspaces/ws-obs/tasks?priority={priority}",
                None, session["alice"])
            ok = status == 200 and isinstance(body, list) and all(
                t.get("priority") == priority for t in body)
            if expect_count is not None:
                ok = ok and len(body) == expect_count
            return f"http-{status}", ("PASS" if ok else "FAIL"), \
                {"http_status": status,
                 "returned": len(body) if isinstance(body, list) else -1}
        return action

    step("priority.filter-high", "http.priority-filter", "http-200", do_filter("HIGH"))
    step("priority.filter-low", "http.priority-filter", "http-200", do_filter("LOW"))

    def do_invalid_create() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/workspaces/ws-obs/tasks",
                              {"title": "Bad", "priority": "URGENT"},
                              session["alice"])
        return f"http-{status}", ("PASS" if status == 422 else "FAIL"), {"http_status": status}

    step("priority.invalid-rejected", "http.priority-invalid", "http-422", do_invalid_create)

    def do_invalid_filter() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("GET", base + "/workspaces/ws-obs/tasks?priority=URGENT",
                              None, session["alice"])
        return f"http-{status}", ("PASS" if status == 422 else "FAIL"), {"http_status": status}

    step("priority.filter-invalid-rejected", "http.priority-filter-invalid",
         "http-422", do_invalid_filter)

    def do_update() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport(
            "PATCH", base + f"/workspaces/ws-obs/tasks/{session['task_low']}",
            {"priority": "HIGH"}, session["alice"])
        assert isinstance(body, dict)
        ok = status == 200 and body.get("priority") == "HIGH"
        return f"http-{status}", ("PASS" if ok else "FAIL"), {"http_status": status}

    step("priority.update", "http.priority-update", "http-200", do_update)

    def do_read_updated() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport(
            "GET", base + f"/workspaces/ws-obs/tasks/{session['task_low']}",
            None, session["alice"])
        assert isinstance(body, dict)
        ok = status == 200 and body.get("priority") == "HIGH"
        return f"http-{status}", ("PASS" if ok else "FAIL"), {"http_status": status}

    step("crud.read-after-update", "http.priority-read-after-update", "http-200",
         do_read_updated)

    def do_outsider() -> tuple[str | None, str, dict[str, Any]]:
        status, body = transport("POST", base + "/users/register",
                                 {"username": "obs27-out", "password": "y" * 16})
        assert isinstance(body, dict)
        status, body = transport("POST", base + "/users/login",
                                 {"username": "obs27-out", "password": "y" * 16})
        assert isinstance(body, dict)
        outsider = str(body.get("token", ""))
        status, _ = transport("GET", base + "/workspaces/ws-obs/tasks?priority=HIGH",
                              None, outsider)
        return f"http-{status}", ("PASS" if status == 403 else "FAIL"), {"http_status": status}

    step("authz.outsider-rejected", "http.outsider-filter", "http-403", do_outsider)

    def do_role() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport("POST", base + "/workspaces/ws-obs/members",
                              {"user_id": session["alice_id"]}, session["alice"])
        return f"http-{status}", ("PASS" if status == 403 else "FAIL"), {"http_status": status}

    step("authz.role-rejected", "http.member-add-forbidden", "http-403", do_role)

    def do_delete() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport(
            "DELETE", base + f"/workspaces/ws-obs/tasks/{session['task_medium']}",
            None, session["alice"])
        return f"http-{status}", ("PASS" if status == 204 else "FAIL"), {"http_status": status}

    step("crud.delete", "http.priority-delete", "http-204", do_delete)

    def do_read_deleted() -> tuple[str | None, str, dict[str, Any]]:
        status, _ = transport(
            "GET", base + f"/workspaces/ws-obs/tasks/{session['task_medium']}",
            None, session["alice"])
        return f"http-{status}", ("PASS" if status == 422 else "FAIL"), {"http_status": status}

    step("crud.read-after-delete", "http.priority-read-after-delete", "http-422",
         do_read_deleted)

    return records


def assemble_evidence(records: list[dict[str, Any]], execution_id: str,
                      generated_at: str) -> dict[str, Any]:
    """Canonical D27 evidence: raw facts + normalized form + invariants.
    Interpretation-free; production stays false."""
    identity = verify_deployment_identity()
    for record in records:
        OBS.validate_record(record)
    normalized = OBS.normalize_evidence(records)
    evidence: dict[str, Any] = {
        "contract": OBSERVATION_CONTRACT,
        "execution_id": execution_id,
        "deployment_id": identity["deployment_id"],
        "deployment_hash": identity["deployment_hash"],
        "manifest_hash": identity["manifest_hash"],
        "implementation_id": identity["implementation_id"],
        "implementation_hash": identity["implementation_hash"],
        "architecture_id": identity["architecture_id"],
        "objective_id": identity["objective_id"],
        "isr_hash": identity["isr_hash"],
        "summary": OBS.summarize(records),
        "constitutional_invariants": OBS.check_constitutional_invariants(),
        "security_invariants": OBS.check_security_invariants(records),
        "behavioral_invariants": OBS.check_behavioral_invariants(records),
        "observations": sorted(records, key=lambda r: r["observation_id"]),
        "normalized": normalized,
        "production_authorization": False,
        "observation_status": "PERFORMED",
        "behavioral_claims": "NONE",
        "provenance": provenance_block(execution_id) | {"generated_at": generated_at},
    }
    check = {k: v for k, v in evidence.items() if k != "provenance"}
    provenance = dict(evidence["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    evidence["normalized_hash"] = _sha(_canon(check))
    return evidence
