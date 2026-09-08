"""VS-D04 — implementation builder/validator (selected: vs1-candidate-a).

Validates frozen inputs, validates the selected candidate, constructs
implementation evidence, validates lineage. Fail-closed. No deployment,
no observation, no evolution side effects.
"""

from __future__ import annotations

import hashlib
import json

from vertical_slice import candidates as candidates_module
from vertical_slice.isr import build_task_tracker_isr
from vertical_slice.requirements import build_task_tracker_requirements

IMPLEMENTATION_VERSION = "vs1-impl-v1"

# implementation component → ISR node → requirement reference.
COMPONENT_ISR_MAP: tuple[tuple[str, str, str], ...] = (
    # services
    ("service.register", "svc-identity", "req-auth-register"),
    ("service.login", "svc-identity", "req-auth-login"),
    ("service.create_task", "svc-task", "req-task-create"),
    ("service.list_tasks", "svc-task", "req-task-read"),
    ("service.get_task", "svc-task", "req-task-read"),
    ("service.update_task", "svc-task", "req-task-update"),
    ("service.assign_task", "svc-task", "req-task-assign"),
    ("service.delete_task", "svc-task", "req-task-delete"),
    ("service.add_member", "svc-workspace", "req-workspace-members"),
    ("service.remove_member", "svc-workspace", "req-workspace-members"),
    # APIs
    ("api.register", "api-identity", "req-auth-register"),
    ("api.login", "api-identity", "req-auth-login"),
    ("api.create_task", "api-task", "req-task-create"),
    ("api.list_tasks", "api-task", "req-task-read"),
    ("api.get_task", "api-task", "req-task-read"),
    ("api.update_task", "api-task", "req-task-update"),
    ("api.delete_task", "api-task", "req-task-delete"),
    ("api.add_member", "api-workspace", "req-workspace-members"),
    ("api.remove_member", "api-workspace", "req-workspace-members"),
    # data models
    ("model.user", "dm-user-account", "req-auth-register"),
    ("model.task", "dm-task", "req-task-create"),
    ("model.workspace", "dm-workspace", "req-workspace-members"),
    # events
    ("event.task-created", "ev-task-created", "req-task-create"),
    ("event.task-updated", "ev-task-updated", "req-task-update"),
    # security policies
    ("security.password-hashing", "sec-credential-safety", "req-credential-safety"),
    ("security.session-auth", "sec-credential-safety", "req-auth-login"),
    ("security.membership-authz", "sec-tenant-isolation", "req-tenant-isolation"),
    # durability + constraints
    ("store.file-repository", "dm-task", "req-durability"),
    ("security.session-auth", "svc-identity", "con-multiuser"),
    ("api.single-interface", "api-task", "con-api-surface"),
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_input_identity() -> dict[str, str]:
    """Recompute frozen upstream identities (fail-closed on drift)."""
    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    graph_hash = _sha(json.dumps(graph.model_dump(mode="json"), sort_keys=True,
                                 separators=(",", ":")))
    decision = candidates_module.select_candidate()
    if decision["selected"] != "vs1-candidate-a":
        raise ValueError("VS-D04 requires selected=vs1-candidate-a, "
                         f"got {decision['selected']}")
    return {
        "vs-d01-graph-sha256": graph_hash,
        "vs-d02-isr-content-hash": rev.content_hash,
        "vs-d03-policy": candidates_module.SELECTION_POLICY_VERSION,
        "vs-d03-selected": str(decision["selected"]),
        "vs-d03-score": str(decision["selection_score"]),
        "implementation-version": IMPLEMENTATION_VERSION,
    }


def validate_lineage() -> dict[str, list[str]]:
    """Every COMPONENT_ISR_MAP row must resolve upstream. Fail-closed."""
    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    unresolved_isr: list[str] = []
    unresolved_req: list[str] = []
    for _component, isr_id, req_id in COMPONENT_ISR_MAP:
        if isr_id not in rev.graph.nodes:
            unresolved_isr.append(isr_id)
        if req_id not in graph.nodes:
            unresolved_req.append(req_id)
    if unresolved_isr or unresolved_req:
        raise ValueError(f"VS-D04 lineage break: isr={unresolved_isr} req={unresolved_req}")
    return {"unresolved_isr": unresolved_isr, "unresolved_req": unresolved_req}


def build_evidence() -> dict[str, object]:
    """Deterministic machine-readable implementation evidence (§19)."""
    identity = frozen_input_identity()
    validate_lineage()
    requirements = sorted({req for _, _, req in COMPONENT_ISR_MAP})
    isr_nodes = sorted({isr for _, isr, _ in COMPONENT_ISR_MAP})
    components = sorted(comp for comp, _, _ in COMPONENT_ISR_MAP)
    return {
        **identity,
        "candidate_id": "vs1-candidate-a",
        "candidate_version": "1",
        "requirement_coverage": requirements,
        "isr_coverage": isr_nodes,
        "components": components,
    }
