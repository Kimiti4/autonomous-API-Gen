"""VS-D15 — selected evolved architecture regeneration (compiler boundary).

Transforms the D14-selected evolved architecture (central-policy) into the
executable vs1-impl-v2 implementation while preserving frozen requirements,
ISR, authorization constraints, and lineage. Never mutates upstream
authority artifacts. See folder/VS1_REGENERATION.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

IMPLEMENTATION_ID = "vs1-impl-v2"
PARENT_IMPLEMENTATION_ID = "vs1-impl-v1"
REGENERATION_CONTRACT_VERSION = "vs1-regeneration-v1"

# implementation component → evolved architecture component → ISR → requirement.
COMPONENT_MAP: tuple[tuple[str, str, str, str], ...] = (
    # central authorization policy boundary (the architectural delta)
    ("app_v2.policy.AuthorizationPolicy", "authorization-policy-component",
     "sec-credential-safety", "req-credential-safety"),
    ("app_v2.policy.AuthorizationPolicy.check_session", "authorization-decision-flow",
     "sec-credential-safety", "req-auth-login"),
    ("app_v2.policy.AuthorizationPolicy.check_member", "authorization-decision-flow",
     "sec-tenant-isolation", "req-tenant-isolation"),
    ("app_v2.policy.AuthorizationPolicy.check_admin", "authorization-decision-flow",
     "sec-tenant-isolation", "req-workspace-members"),
    # services (delegating to the policy boundary)
    ("app_v2.service.register", "svc-identity", "svc-identity", "req-auth-register"),
    ("app_v2.service.login", "svc-identity", "svc-identity", "req-auth-login"),
    ("app_v2.service.create_task", "svc-task", "svc-task", "req-task-create"),
    ("app_v2.service.list_tasks", "svc-task", "svc-task", "req-task-read"),
    ("app_v2.service.get_task", "svc-task", "svc-task", "req-task-read"),
    ("app_v2.service.update_task", "svc-task", "svc-task", "req-task-update"),
    ("app_v2.service.assign_task", "svc-task", "svc-task", "req-task-assign"),
    ("app_v2.service.delete_task", "svc-task", "svc-task", "req-task-delete"),
    ("app_v2.service.add_member", "svc-workspace", "svc-workspace", "req-workspace-members"),
    ("app_v2.service.remove_member", "svc-workspace", "svc-workspace", "req-workspace-members"),
    # APIs (contract-identical to v1 surface)
    ("app_v2.api.register", "api-identity", "api-identity", "req-auth-register"),
    ("app_v2.api.login", "api-identity", "api-identity", "req-auth-login"),
    ("app_v2.api.create_task", "api-task", "api-task", "req-task-create"),
    ("app_v2.api.list_tasks", "api-task", "api-task", "req-task-read"),
    ("app_v2.api.get_task", "api-task", "api-task", "req-task-read"),
    ("app_v2.api.update_task", "api-task", "api-task", "req-task-update"),
    ("app_v2.api.delete_task", "api-task", "api-task", "req-task-delete"),
    ("app_v2.api.add_member", "api-workspace", "api-workspace", "req-workspace-members"),
    ("app_v2.api.remove_member", "api-workspace", "api-workspace", "req-workspace-members"),
    # data models (reused semantics)
    ("app_v2.model.user", "dm-user-account", "dm-user-account", "req-auth-register"),
    ("app_v2.model.task", "dm-task", "dm-task", "req-task-create"),
    ("app_v2.model.workspace", "dm-workspace", "dm-workspace", "req-workspace-members"),
    # events (reused semantics)
    ("app_v2.event.task-created", "ev-task-created", "ev-task-created", "req-task-create"),
    ("app_v2.event.task-updated", "ev-task-updated", "ev-task-updated", "req-task-update"),
    # durability (reused file-repository semantics)
    ("store.file-repository", "dm-task", "dm-task", "req-durability"),
    # explicit constraints (satisfied structurally, documented honestly)
    ("app_v2.security.session-auth", "svc-identity", "svc-identity", "con-multiuser"),
    ("app_v2.api.single-interface", "api-task", "api-task", "con-api-surface"),
    # security policies (strengthened, not weakened)
    ("app_v2.security.password-hashing", "sec-credential-safety",
     "sec-credential-safety", "req-credential-safety"),
    ("app_v2.security.session-auth", "sec-credential-safety",
     "sec-credential-safety", "req-auth-login"),
    ("app_v2.security.membership-authz", "sec-tenant-isolation",
     "sec-tenant-isolation", "req-tenant-isolation"),
)


class RegenerationError(Exception):
    """Fail-closed regeneration failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def load_selection(
    path: str = "vertical_slice/evolution_selection_evidence.json",
) -> dict[str, Any]:
    """Load + validate the frozen D14 selection record (fail-closed, read-only)."""
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as exc:
        raise RegenerationError(f"D14 selection unavailable: {exc}")
    if not isinstance(record, dict):
        raise RegenerationError("D14 selection malformed")
    for field in ("selected_candidate_id", "selected_candidate_hash",
                  "parent_architecture_id", "objective_id",
                  "authorization_id", "selection_hash", "upstream"):
        if field not in record:
            raise RegenerationError(f"D14 selection missing field: {field}")
    if record.get("selection_mode") != "SYNTHETIC_TEST_ONLY":
        raise RegenerationError("D14 selection mode drift")
    if record.get("production_authorization") is not False:
        raise RegenerationError("D14 production flag drift")
    if record["selected_candidate_id"] != "vs1-evolved-96fe2d29fd76":
        raise RegenerationError("D14 winner drift")
    from vertical_slice import evolution_selection as SEL

    recomputed = SEL.choose_candidate()
    if recomputed["selected_candidate_id"] != record["selected_candidate_id"]:
        raise RegenerationError("D14 winner mismatch on recomputation")
    if recomputed["selection_hash"] != record.get("selection_hash"):
        raise RegenerationError("D14 selection hash drift")
    return record


def upstream_identities(selection: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities D01–D14 (fail-closed)."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    with open("vertical_slice/evolution_decision_v2_evidence.json",
              encoding="utf-8") as f:
        real_decision = json.load(f)
    if real_decision.get("decision") != "NO_CHANGE":
        raise RegenerationError("real D12 decision drift")
    with open("vertical_slice/evolution_evidence.json",
              encoding="utf-8") as f:
        evolution_record = json.load(f)
    if len(evolution_record.get("candidates", [])) != 3:
        raise RegenerationError("D13 candidate set drift")
    expected = {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": "vs1-candidate-a",
        "vs-d03-policy": C.SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
        "vs-d07-interpretation": "vs1-interpret-v1",
        "vs-d08-decision": DEC.decide()["decision"],
        "vs-d09-policy": ACQ.run_gate()["policy"],
        "vs-d10-contract": "vs1-evidence-run-v1",
        "vs-d11-contract": "vs1-interpretation-v2",
        "vs-d12-decision": "NO_CHANGE",
        "vs-d14-selection": selection["selected_candidate_id"],
        "vs-d14-hash": selection["selection_hash"],
    }
    if selection.get("production_authorization") is not False:
        raise RegenerationError("production authorization drift")
    return expected


def validate_lineage() -> dict[str, list[str]]:
    """Every COMPONENT_MAP row must resolve upstream. Fail-closed."""
    from vertical_slice.isr import build_task_tracker_isr
    from vertical_slice.requirements import build_task_tracker_requirements

    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    unresolved_isr: list[str] = []
    unresolved_req: list[str] = []
    for _component, _arch, isr_id, req_id in COMPONENT_MAP:
        if isr_id not in rev.graph.nodes:
            unresolved_isr.append(isr_id)
        if req_id not in graph.nodes:
            unresolved_req.append(req_id)
    if unresolved_isr or unresolved_req:
        raise RegenerationError(
            f"VS-D15 lineage break: isr={unresolved_isr} req={unresolved_req}")
    return {"unresolved_isr": unresolved_isr, "unresolved_req": unresolved_req}


def requirement_coverage() -> list[str]:
    return sorted({req for _, _, _, req in COMPONENT_MAP})


def isr_coverage() -> list[str]:
    return sorted({isr for _, _, isr, _ in COMPONENT_MAP})


def compare_parent() -> dict[str, Any]:
    """Machine-readable v1/v2 comparison: intentional change vs regression."""
    return {
        "architecture_change": [
            "authorization decisions centralized in app_v2.policy.AuthorizationPolicy",
            "services delegate session/member/admin checks to the policy boundary",
        ],
        "behavior_preserved": [
            "task creation", "task retrieval", "task update", "task deletion",
            "role restrictions", "data isolation", "credential handling",
            "password hashing", "persistence", "event emission",
            "restart durability", "API behavior",
        ],
        "security_preserved": [
            "authentication boundaries", "authorization boundaries",
            "role restrictions", "credential handling", "password hashing",
            "unauthorized-access rejection",
        ],
        "requirement_preserved": sorted({
            "req-auth-register", "req-auth-login", "req-task-create",
            "req-task-read", "req-task-update", "req-task-delete",
            "req-task-assign", "req-workspace-members",
            "req-credential-safety", "req-tenant-isolation", "req-durability",
        }),
        "implementation_change": [
            "vertical_slice/app_v2/policy.py (new central boundary)",
            "vertical_slice/app_v2/service.py (delegating service layer)",
            "vertical_slice/app_v2/api.py (rewired routes, identical contract)",
        ],
    }


def build_evidence() -> dict[str, Any]:
    """Deterministic regeneration evidence (no servers, no deployment)."""
    selection = load_selection()
    identities = upstream_identities(selection)
    validate_lineage()
    comparison = compare_parent()
    record = {
        "contract": REGENERATION_CONTRACT_VERSION,
        "policy": "vs1-regeneration-policy-v1",
        "implementation_id": IMPLEMENTATION_ID,
        "parent_implementation_id": PARENT_IMPLEMENTATION_ID,
        "selected_architecture_id": selection["selected_candidate_id"],
        "selected_architecture_hash": selection["selected_candidate_hash"],
        "evolution_id": "vs1-evolution-synthetic-001",
        "objective_id": selection["objective_id"],
        "authorization_id": selection["authorization_id"],
        "selection_id": selection["selection_id"],
        "selection_hash": selection["selection_hash"],
        "isr_hash": identities["vs-d02-isr-content-hash"],
        "backend_id": "python-fastapi",
        "component_mappings": [
            {"component": comp, "architecture": arch, "isr": isr, "requirement": req}
            for comp, arch, isr, req in COMPONENT_MAP
        ],
        "requirement_coverage": requirement_coverage(),
        "security_coverage": ["sec-credential-safety", "sec-tenant-isolation"],
        "architecture_coverage": sorted({arch for _, arch, _, _ in COMPONENT_MAP}),
        "parent_comparison": comparison,
        "production_authorization": False,
        "upstream": identities,
    }
    record["implementation_hash"] = _sha(_canon(
        {k: v for k, v in record.items() if k != "implementation_hash"}))
    return record
