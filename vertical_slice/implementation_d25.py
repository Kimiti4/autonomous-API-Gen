"""VS-D25 — selected-architecture implementation compiler record.

Compiles the D24-selected query-policy-separation architecture for
VS1-OBJ-001 into the executable vs1-impl-obj001-v1 (vertical_slice/app_v3).
Compilation record ONLY: no deployment, observation, optimization,
production change, commit, or push. ISR immutable. D22/D23/D24 read-only.
Parent implementations preserved untouched.

Implementation identity is content-addressed over the canonical app_v3
sources plus architecture/objective/ISR/backend pins — reproducible from
identical inputs, independent of machine, path, time, or process.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

IMPLEMENTATION_CONTRACT = "vs1-implementation-d25"
IMPLEMENTATION_ID = "vs1-impl-obj001-v1"
PARENT_IMPLEMENTATION_ID = "vs1-impl-v2"
BACKEND_ID = "python-fastapi"
D24_PATH = "vertical_slice/architecture_selection_d24_evidence.json"
D23_PATH = "vertical_slice/candidate_generation_d23_evidence.json"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"
APP_V3_FILES: tuple[str, ...] = (
    "vertical_slice/app_v3/__init__.py",
    "vertical_slice/app_v3/models.py",
    "vertical_slice/app_v3/policy.py",
    "vertical_slice/app_v3/tasks.py",
    "vertical_slice/app_v3/service.py",
    "vertical_slice/app_v3/api.py",
)

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_PROFILE = "query-policy-separation"

# implementation component → D24 architecture component → D23 candidate →
# ISR obligation (existing) ; objective obligation (SC codes are new-native).
COMPONENT_MAP: tuple[tuple[str, str, str, str, str], ...] = (
    ("app_v3.policy.PriorityQueryPolicy", "priority-query-policy",
     "vs1-obj001", "dm-task", "SC05"),
    ("app_v3.policy.build_filter", "priority-query-policy",
     "vs1-obj001", "svc-task", "SC07"),
    ("app_v3.tasks.TaskV3Repository", "task-persistence",
     "vs1-obj001", "dm-task", "SC01"),
    ("app_v3.service.create_task", "task-domain",
     "vs1-obj001", "svc-task", "SC02"),
    ("app_v3.service.update_task", "task-domain",
     "vs1-obj001", "svc-task", "SC03"),
    ("app_v3.service.list_tasks", "task-domain",
     "vs1-obj001", "svc-task", "SC04"),
    ("app_v3.service.get_task", "task-domain",
     "vs1-obj001", "svc-task", "SC04"),
    ("app_v3.api.priority-contract", "priority-contract",
     "vs1-obj001", "api-task", "SC06"),
    ("app_v3.service.auth-delegation", "svc-identity",
     "vs1-impl-v2", "sec-credential-safety", "req-auth-login"),
    ("app_v3.service.member-delegation", "svc-workspace",
     "vs1-impl-v2", "sec-tenant-isolation", "req-workspace-members"),
    ("app_v3.service.task-lifecycle", "svc-task",
     "vs1-impl-v2", "svc-task", "req-task-delete"),
    ("app_v3.service.event-emission", "svc-task",
     "vs1-impl-v2", "ev-task-created", "preserved"),
    ("app_v3.service.event-emission-updated", "svc-task",
     "vs1-impl-v2", "ev-task-updated", "preserved"),
    ("app_v3.service.durability", "task-persistence",
     "vs1-impl-v2", "dm-task", "req-durability"),
)


class ImplementationError(Exception):
    """Fail-closed implementation failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _load_json(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as exc:
        raise ImplementationError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise ImplementationError(f"input malformed: {path}")
    return record


def file_hashes() -> dict[str, str]:
    """Content hashes of the canonical implementation sources."""
    hashes = {}
    for rel in APP_V3_FILES:
        if not os.path.isfile(rel):
            raise ImplementationError(f"implementation file missing: {rel}")
        with open(rel, "rb") as f:
            hashes[rel] = hashlib.sha256(f.read()).hexdigest()
    return hashes


def verify_upstream(d24_path: str = D24_PATH, d23_path: str = D23_PATH,
                    d22_path: str = D22_PATH) -> dict[str, Any]:
    """D24 selection + D23 set + D22 admission + ISR pin (read-only)."""
    from vertical_slice import implementation as IMPL

    d24 = _load_json(d24_path)
    d23 = _load_json(d23_path)
    d22 = _load_json(d22_path)
    if d24.get("contract") != "vs1-architecture-selection-d24":
        raise ImplementationError("D24 contract drift")
    winner = d24.get("selected_candidate")
    if not winner or winner not in d23.get("candidate_ids", []):
        raise ImplementationError("selection not in D23 set")
    candidate = next(c for c in d23["candidates"] if c["candidate_id"] == winner)
    if candidate.get("architecture_profile") != EXPECTED_PROFILE:
        raise ImplementationError("selected profile drift")
    if candidate["architecture_profile"] != EXPECTED_PROFILE:
        raise ImplementationError("selected profile drift")
    check = {k: v for k, v in d24.items()
             if k not in ("provenance", "evidence_hash")}
    provenance = dict(d24["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    if _sha(_canon(check)) != d24.get("evidence_hash"):
        raise ImplementationError("D24 evidence drift")
    if d22.get("objective_id") != "VS1-OBJ-001":
        raise ImplementationError("objective drift")
    if IMPL.frozen_input_identity()["vs-d02-isr-content-hash"] != EXPECTED_ISR:
        raise ImplementationError("ISR drift")
    return {"d24": d24, "d23": d23, "d22": d22, "winner": candidate}


def detect_architecture_drift() -> dict[str, bool]:
    """Structural fidelity: the implementation must exhibit exactly the
    selected architecture's responsibilities — both policy delegations,
    the repository seam, no new service/event/auth boundaries."""
    import vertical_slice.app_v3.api as api
    import vertical_slice.app_v3.policy as policy
    import vertical_slice.app_v3.service as service
    import vertical_slice.app_v3.tasks as tasks

    import inspect as _inspect
    service_src = _inspect.getsource(service.TaskTrackerServiceV3)
    checks = {
        "delegates_authorization": "AuthorizationPolicy" in service_src
        and "self._policy" in service_src,
        "delegates_priority": "PriorityQueryPolicy" in service_src
        and "self._priority" in service_src,
        "repository_seam": hasattr(tasks, "TaskV3Repository"),
        "policy_boundary": all(hasattr(policy.PriorityQueryPolicy, name)
                               for name in ("validate_priority",
                                            "build_filter",
                                            "apply_legacy_default")),
        "api_entrypoint": hasattr(api, "create_app"),
        "no_new_event_contract": "task-created" in service_src
        and "task-updated" in service_src
        and "task-priority-" not in service_src,
        "closed_priority_domain": True,
    }
    from vertical_slice.app_v3.models import PRIORITY_VALUES
    checks["closed_priority_domain"] = sorted(PRIORITY_VALUES) == [
        "HIGH", "LOW", "MEDIUM"]
    if not all(checks.values()):
        raise ImplementationError(f"architecture drift: {checks}")
    return checks


def validate_lineage() -> None:
    """Every mapping row resolves: ISR nodes in the ISR graph,
    obligations in the requirements graph or the SC set. Fail-closed."""
    from vertical_slice.isr import build_task_tracker_isr
    from vertical_slice.requirements import build_task_tracker_requirements

    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    valid_sc = {f"SC{i:02d}" for i in range(1, 14)} | {"preserved"}
    for component, _arch, _cand, isr, obligation in COMPONENT_MAP:
        if isr not in rev.graph.nodes:
            raise ImplementationError(f"orphan ISR node: {isr} ({component})")
        if obligation not in graph.nodes and obligation not in valid_sc:
            raise ImplementationError(
                f"orphan obligation: {obligation} ({component})")


def implementation_hash() -> str:
    """Content-addressed implementation identity (reproducible)."""
    upstream = verify_upstream()
    identity = {
        "implementation_id": IMPLEMENTATION_ID,
        "parent": PARENT_IMPLEMENTATION_ID,
        "architecture": EXPECTED_PROFILE,
        "candidate": upstream["winner"]["candidate_id"],
        "candidate_hash": upstream["winner"]["candidate_hash"],
        "selection_hash": upstream["d24"]["selection_hash"],
        "objective": "VS1-OBJ-001",
        "objective_hash": upstream["d22"]["objective"]["objective_hash"],
        "isr": EXPECTED_ISR,
        "backend": BACKEND_ID,
        "sources": file_hashes(),
    }
    return _sha(_canon(identity))


def assemble_evidence(generated_at: str) -> dict[str, Any]:
    """Canonical implementation evidence. Deployment/observation flags are
    explicit falsehoods; production stays false."""
    upstream = verify_upstream()
    validate_lineage()
    drift = detect_architecture_drift()
    d24, d23, d22 = upstream["d24"], upstream["d23"], upstream["d22"]
    record: dict[str, Any] = {
        "contract": IMPLEMENTATION_CONTRACT,
        "implementation_id": IMPLEMENTATION_ID,
        "parent_implementation_id": PARENT_IMPLEMENTATION_ID,
        "selected_architecture_id": EXPECTED_PROFILE,
        "candidate_id": upstream["winner"]["candidate_id"],
        "candidate_hash": upstream["winner"]["candidate_hash"],
        "selection_hash": d24["selection_hash"],
        "objective_id": "VS1-OBJ-001",
        "objective_hash": d22["objective"]["objective_hash"],
        "objective_source_sha256": d22["source_reference"].split(
            "sha256:")[-1],
        "isr_hash": EXPECTED_ISR,
        "backend_id": BACKEND_ID,
        "component_mappings": [
            {"component": c, "architecture": a, "candidate": k,
             "isr": i, "obligation": o}
            for c, a, k, i, o in COMPONENT_MAP
        ],
        "architecture_coverage": sorted({a for _, a, _, _, _ in COMPONENT_MAP}),
        "requirement_coverage": sorted({o for _, _, _, _, o in COMPONENT_MAP}),
        "security_coverage": ["authentication", "authorization",
                              "tenant-isolation", "credential-safety",
                              "input-validation", "secret-handling"],
        "fidelity_checks": drift,
        "verification_summary": "behavioral + contract + security + "
                                "persistence suites in "
                                "tests/vs1/test_implementation_d25.py",
        "production_authorization": False,
        "deployment_performed": False,
        "observation_performed": False,
        "optimization_performed": False,
        "handoff": {
            "implementation_id": IMPLEMENTATION_ID,
            "selected_architecture_id": EXPECTED_PROFILE,
            "selection_hash": d24["selection_hash"],
            "candidate_id": upstream["winner"]["candidate_id"],
            "objective_id": "VS1-OBJ-001",
            "isr_hash": EXPECTED_ISR,
            "backend_id": BACKEND_ID,
            "parent_implementation_id": PARENT_IMPLEMENTATION_ID,
            "production_authorization": False,
            "deployment_performed": False,
        },
        "provenance": {
            "contract": IMPLEMENTATION_CONTRACT,
            "d24_selection": d24["selection_hash"],
            "d23_generation": d23["generation_hash"],
            "d22_intake": d22["intake_hash"],
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    record["implementation_hash"] = implementation_hash()
    return record
