"""VS-D10 — controlled evidence acquisition runner (execution only).

Executes the two frozen D09 plans (4 authorization observations + 3
independent deployment cycles) and produces normalized evidence records.
Records outcomes (PASS/FAIL/UNDETERMINED/BLOCKED) against explicit criteria.
Emits no hypothesis conclusions and no evolution authorizations. See
folder/VS1_EVIDENCE_ACQUISITION_RESULTS.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any

RUN_CONTRACT_VERSION = "vs1-evidence-run-v1"
RUN_CONTRACT_ID = "vs1-evidence-run-v1"

_OUTCOMES = ("PASS", "FAIL", "UNDETERMINED", "BLOCKED")

_PLAN_FIELDS = (
    "plan_id", "hypothesis_id", "objective", "unknown_to_resolve",
    "required_observation", "observation_count", "independence_requirement",
    "success_criteria", "falsification_criteria", "termination_condition",
    "scope", "out_of_scope", "risk_constraints", "provenance_requirements",
    "privacy_requirements", "security_requirements",
    "reproducibility_requirements",
)


class RunnerError(Exception):
    """Fail-closed runner failure (never fabricate evidence)."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_plans() -> list[dict[str, Any]]:
    """Recompute (never trust copies) the frozen D09 gate output."""
    from vertical_slice import evidence_acquisition as ACQ

    record = ACQ.run_gate()
    if record.get("outcome") != "EVIDENCE_PLAN_REQUIRED":
        raise RunnerError(
            f"D09 outcome is {record.get('outcome')}, not EVIDENCE_PLAN_REQUIRED")
    plans = record.get("plans", [])
    if len(plans) != 2:
        raise RunnerError(f"expected 2 plans, found {len(plans)}")
    for plan in plans:
        check_plan_integrity(plan)
    total = sum(p["observation_count"] for p in plans)
    if total != 7:
        raise RunnerError(f"authorized observations must total 7, found {total}")
    return sorted(plans, key=lambda p: p["plan_id"])


def check_plan_integrity(plan: dict[str, Any]) -> None:
    """Fail closed on any missing plan field (§4)."""
    for field in _PLAN_FIELDS:
        if field not in plan:
            raise RunnerError(f"plan missing field: {field}")
    if not isinstance(plan["observation_count"], int) or plan["observation_count"] < 1:
        raise RunnerError("plan observation_count invalid")


def upstream_identities() -> dict[str, str]:
    """Recompute frozen upstream identities D01–D09."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    decision = DEC.decide()
    gate = ACQ.run_gate()
    return {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": "vs1-candidate-a",
        "vs-d03-policy": C.SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
        "vs-d07-interpretation": "vs1-interpret-v1",
        "vs-d08-decision": decision["decision"],
        "vs-d08-policy": decision["policy_id"],
        "vs-d09-policy": gate["policy"],
        "vs-d09-outcome": gate["outcome"],
    }


def classify_observation(expected: Any, observed: Any,
                         executable: bool = True) -> str:
    """Mechanical outcome classification (pure; §8)."""
    if not executable:
        return "BLOCKED"
    if expected is None or observed is None:
        return "UNDETERMINED"
    if isinstance(expected, (list, tuple, set)):
        return "PASS" if observed in expected else "FAIL"
    return "PASS" if observed == expected else "FAIL"


def _http(method: str, url: str, body: object = None,
          token: str | None = None) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=(
        json.dumps(body).encode() if body is not None else None),
        headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw) if raw else None
        except ValueError:
            return exc.code, raw


def _launch(store_dir: str) -> tuple[subprocess.Popen, str]:
    env = dict(os.environ, VS1_STORE_DIR=store_dir, VS1_PORT="0",
               PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(
        [sys.executable, "-m", "vertical_slice.serve"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=os.getcwd())
    assert proc.stdout is not None
    pattern = re.compile(r"Uvicorn running on http://127\.0\.0\.1:(\d+)")
    base, deadline = "", time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        match = pattern.search(line)
        if match:
            base = f"http://127.0.0.1:{match.group(1)}"
            break
    if not base or proc.poll() is not None:
        proc.kill()
        raise RunnerError("deployment target did not start")
    ready_by = time.time() + 20
    while time.time() < ready_by:
        try:
            status, body = _http("GET", base + "/health")
            if status == 200 and body == {"status": "ok"}:
                return proc, base
        except OSError:
            pass
        time.sleep(0.2)
    proc.kill()
    raise RunnerError("readiness condition never satisfied")


def _shutdown(proc: subprocess.Popen) -> int | None:
    proc.terminate()
    try:
        return proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        return proc.wait(timeout=15)


def _seed(store_dir: str) -> dict[str, str]:
    """Pre-launch seeding via in-process service (setup, not product use)."""
    from vertical_slice.app.models import Membership
    from vertical_slice.app.service import TaskTrackerService
    from vertical_slice.app.store import TaskTrackerStore

    state = {"n": 0}

    def generate() -> str:
        state["n"] += 1
        return f"vs1-d10-token-{state['n']:04d}"

    store = TaskTrackerStore(store_dir)
    service = TaskTrackerService(store, token_generator=generate)
    store.ensure_workspace("ws-a", "Alpha")
    alice = service.register("alice", "alice-secret-pw")
    admin = service.register("cara-admin", "cara-secret-pw")
    store.put_membership(Membership("ws-a", alice.user_id, "member"))
    store.put_membership(Membership("ws-a", admin.user_id, "admin"))
    return {
        "alice": service.login("alice", "alice-secret-pw"),
        "admin": service.login("cara-admin", "cara-secret-pw"),
        "alice_id": alice.user_id,
        "admin_id": admin.user_id,
    }


def _record(plan_id: str, hypothesis_id: str, observation_id: str, run_id: str,
            cycle_id: str, target: str, expected: Any, observed: Any,
            executable: bool, provenance: dict[str, str]) -> dict[str, Any]:
    outcome = classify_observation(expected, observed, executable)
    normalized = {"expected": expected, "observed": observed, "outcome": outcome}
    record = {
        "evidence_id": _sha("|".join([
            plan_id, observation_id, run_id,
            json.dumps(normalized, sort_keys=True)]))[:16],
        "plan_id": plan_id,
        "hypothesis_id": hypothesis_id,
        "observation_id": observation_id,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "target": target,
        "expected_condition": expected,
        "observed_result": observed,
        "outcome": outcome,
        "normalized_result": normalized,
        "provenance": dict(provenance),
    }
    _assert_no_secrets(record)
    return record


def _assert_no_secrets(record: dict[str, Any]) -> None:
    blob = json.dumps(record).lower()
    for marker in ("alice-secret", "bob-secret", "cara-secret", "eve-secret",
                   "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                   "vs1-d10-token"):
        if marker in blob:
            raise RunnerError(f"secret material in evidence: {marker}")


def _base_provenance(identities: dict[str, str]) -> dict[str, str]:
    return {
        "observation_contract": "vs1-observe-v1",
        "deployment_id": "vs1-local-loopback",
        "implementation_id": "vs1-impl-v1",
        "vs-d01-graph-sha256": identities["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identities["vs-d02-isr-content-hash"],
        "vs-d03-selected": identities["vs-d03-selected"],
        "vs-d09-policy": identities["vs-d09-policy"],
    }


def run_auth_plan(plan: dict[str, Any], identities: dict[str, str],
                  run_id: str) -> list[dict[str, Any]]:
    """Execute the 4 authorized authorization observations on one fresh deployment."""
    if plan["observation_count"] != 4:
        raise RunnerError("auth plan authorizes exactly 4 observations")
    provenance = _base_provenance(identities)
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="vs1-d10-auth-") as tmp:
        tokens = _seed(tmp)
        proc, base = _launch(tmp)
        try:
            # 1. admin-allowed member administration → 201
            status, _ = _http(
                "POST", base + "/workspaces/ws-a/members",
                {"user_id": tokens["alice_id"], "role": "member"},
                token=tokens["admin"])
            records.append(_record(
                plan["plan_id"], plan["hypothesis_id"], "auth-admin-allowed",
                run_id, "n/a", "/workspaces/{ws}/members", 201, status, True,
                provenance))
            # 2. member-attempted admin action → 403
            status, _ = _http(
                "POST", base + "/workspaces/ws-a/members",
                {"user_id": tokens["alice_id"], "role": "member"},
                token=tokens["alice"])
            records.append(_record(
                plan["plan_id"], plan["hypothesis_id"], "auth-member-denied",
                run_id, "n/a", "/workspaces/{ws}/members", 403, status, True,
                provenance))
            # 3. repeated wrong-password logins → 401 with identical errors
            attempts = []
            for _ in range(3):
                status, body = _http(
                    "POST", base + "/users/login",
                    {"username": "alice", "password": "wrong-secret"})
                attempts.append((status, body))
            identical = len({json.dumps(a, sort_keys=True) for a in attempts}) == 1
            statuses = [a[0] for a in attempts]
            records.append(_record(
                plan["plan_id"], plan["hypothesis_id"], "auth-credential-rejection",
                run_id, "n/a", "/users/login",
                {"attempts": [401, 401, 401], "identical_errors": True},
                {"attempts": statuses, "identical_errors": identical},
                True, provenance))
            # 4. outsider isolation → 403
            status, outsider = _http(
                "POST", base + "/users/register",
                {"username": "d10-outsider", "password": "x"})
            if status != 201:
                raise RunnerError(f"auth setup failed: {status}")
            status, login = _http(
                "POST", base + "/users/login",
                {"username": "d10-outsider", "password": "x"})
            if status != 200:
                raise RunnerError(f"auth login failed: {status}")
            status, _ = _http("GET", base + "/workspaces/ws-a/tasks",
                              token=login["token"])
            records.append(_record(
                plan["plan_id"], plan["hypothesis_id"], "auth-outsider-isolated",
                run_id, "n/a", "/workspaces/{ws}/tasks", 403, status, True,
                provenance))
        finally:
            _shutdown(proc)
    if len(records) != 4:
        raise RunnerError("auth plan must yield exactly 4 records")
    return records


def run_deploy_plan(plan: dict[str, Any], identities: dict[str, str],
                    run_id: str) -> list[dict[str, Any]]:
    """Execute 3 independent deployment cycles (fresh process/store/port each)."""
    if plan["observation_count"] != 3:
        raise RunnerError("deploy plan authorizes exactly 3 observations")
    provenance = _base_provenance(identities)
    records: list[dict[str, Any]] = []
    store_dirs: list[str] = []
    cycle_stores: dict[str, str] = {}
    for cycle in (1, 2, 3):
        cycle_id = f"cycle-{cycle:02d}"
        with tempfile.TemporaryDirectory(prefix=f"vs1-d10-{cycle_id}-") as tmp:
            store_dirs.append(os.path.basename(tmp))
            cycle_stores[cycle_id] = os.path.basename(tmp)
            tokens = _seed(tmp)
            proc, base = _launch(tmp)
            try:
                status, body = _http("GET", base + "/health")
                ready = (status == 200 and body == {"status": "ok"})
                status, created = _http(
                    "POST", base + "/workspaces/ws-a/tasks",
                    {"title": f"Cycle {cycle} probe"}, token=tokens["alice"])
                crud_ok = (status == 201 and bool(created.get("task_id")))
            finally:
                _shutdown(proc)
            try:
                _http("GET", base + "/health")
                released = False
            except OSError:
                released = True
            cycle_ok = bool(ready and crud_ok and released)
            records.append(_record(
                plan["plan_id"], plan["hypothesis_id"],
                f"deploy-cycle-{cycle:02d}", run_id, cycle_id,
                "local-uvicorn-loopback",
                {"ready": True, "crud": True, "released": True,
                 "cycle_store": cycle_stores[cycle_id]},
                {"ready": ready, "crud": crud_ok, "released": released,
                 "cycle_store": cycle_stores[cycle_id]},
                True, provenance))
            if not cycle_ok:
                # Record the failure; the plan has no retry authorization.
                records[-1] = dict(records[-1], outcome=(
                    "FAIL" if ready else "BLOCKED"))
    if len(records) != 3:
        raise RunnerError("deploy plan must yield exactly 3 records")
    if len(set(store_dirs)) != 3:
        raise RunnerError("cycle isolation violated: store dirs not distinct")
    return records


def normalize_evidence(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic normalization: order by (plan, observation, run, cycle)."""
    for record in records:
        for field in ("evidence_id", "plan_id", "hypothesis_id",
                      "observation_id", "run_id", "cycle_id", "target",
                      "expected_condition", "observed_result", "outcome",
                      "normalized_result", "provenance"):
            if field not in record:
                raise RunnerError(f"record missing field: {field}")
        if record["outcome"] not in _OUTCOMES:
            raise RunnerError(f"unknown outcome: {record['outcome']}")
        _assert_no_secrets(record)
    return sorted(records, key=lambda r: (
        r["plan_id"], r["observation_id"], r["run_id"], r["cycle_id"]))


def build_artifact(run_id: str = "vs1-d10-run-001") -> dict[str, Any]:
    """Execute both plans and assemble the canonical evidence artifact."""
    plans = load_plans()
    identities = upstream_identities()
    by_hypothesis = {p["hypothesis_id"]: p for p in plans}
    auth_plan = by_hypothesis.get("vs1-hypothesis-auth-model-adequate")
    deploy_plan = by_hypothesis.get("vs1-hypothesis-deploy-repeatable")
    if auth_plan is None or deploy_plan is None:
        raise RunnerError("D09 plans unresolved")
    observations = run_auth_plan(auth_plan, identities, run_id)
    observations += run_deploy_plan(deploy_plan, identities, run_id)
    if len(observations) != 7:
        raise RunnerError(
            f"authorized observations = 7, executed = {len(observations)}")
    normalized = normalize_evidence(observations)
    summary: dict[str, Any] = {
        "authorized_observations": 7,
        "executed_observations": len(normalized),
        "pass": sum(1 for r in normalized if r["outcome"] == "PASS"),
        "fail": sum(1 for r in normalized if r["outcome"] == "FAIL"),
        "undetermined": sum(1 for r in normalized if r["outcome"] == "UNDETERMINED"),
        "blocked": sum(1 for r in normalized if r["outcome"] == "BLOCKED"),
        "plans_completed": sorted({r["plan_id"] for r in normalized}),
        "plans_incomplete": [],
    }
    artifact = {
        "contract_id": RUN_CONTRACT_ID,
        "policy_id": RUN_CONTRACT_VERSION,
        "execution_id": run_id,
        "upstream_identities": identities,
        "plans": sorted(
            ({k: p[k] for k in (
                "plan_id", "hypothesis_id", "objective", "observation_count",
                "success_criteria", "falsification_criteria",
                "termination_condition", "scope")} for p in plans),
            key=lambda p: p["plan_id"]),
        "observations": normalized,
        "summary": summary,
        "provenance": dict(normalized[0]["provenance"]),
    }
    artifact["content_hash"] = _sha(json.dumps(
        {k: v for k, v in artifact.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")))
    return artifact
