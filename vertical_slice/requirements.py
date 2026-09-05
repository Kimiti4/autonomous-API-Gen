"""VS-D01 — task-tracking CRUD SaaS requirements as a canonical RequirementGraph.

Manual intake (per folder/vs1.md: autonomous intake is NOT required for VS-1).
Technology-neutral: no backend/framework/storage terms (enforced by
reqgraph.core.invariants.validate_requirement_graph, fail-closed).

The graph is deterministic: same builder revision always yields the same
graph. Requirement IDs are stable strings; the builder carries no randomness.
"""

from __future__ import annotations

from reqgraph.core.graph import (
    Priority,
    RequirementEdge,
    RequirementEdgeType,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)

SCHEMA_VERSION = "1.0"
SOURCE_REF = "vs1-manual-intake-v1"


def _n(
    id: str,
    kind: RequirementKind,
    statement: str,
    priority: Priority,
    acceptance_criteria: list[str] | tuple[str, ...] = (),
    ambiguity_score: float = 0.0,
    resolution_ref: str | None = None,
) -> RequirementNode:
    return RequirementNode(
        id=id,
        kind=kind,
        statement=statement,
        priority=priority,
        acceptance_criteria=list(acceptance_criteria),
        ambiguity_score=ambiguity_score,
        resolution_ref=resolution_ref,
        source_refs=[SOURCE_REF],
    )


def _e(id: str, type: RequirementEdgeType, source_id: str, target_id: str,
       resolution_ref: str | None = None) -> RequirementEdge:
    return RequirementEdge(
        id=id, type=type, source_id=source_id, target_id=target_id,
        resolution_ref=resolution_ref,
    )


def build_task_tracker_requirements() -> RequirementGraph:
    """Build the VS-1 task-tracker RequirementGraph (deterministic)."""
    nodes: dict[str, RequirementNode] = {}
    edges: dict[str, RequirementEdge] = {}

    # --- stakeholders -----------------------------------------------------
    nodes["stk-end-user"] = _n(
        "stk-end-user", RequirementKind.STAKEHOLDER,
        "Person who tracks personal or team tasks in the product.",
        Priority.MUST,
    )
    nodes["stk-workspace-admin"] = _n(
        "stk-workspace-admin", RequirementKind.STAKEHOLDER,
        "Person who administers workspace membership and member roles.",
        Priority.SHOULD,
    )

    # --- domain concepts --------------------------------------------------
    nodes["dom-task"] = _n(
        "dom-task", RequirementKind.DOMAIN_CONCEPT,
        "A unit of trackable work with a title, a lifecycle status, and an owner.",
        Priority.MUST,
    )
    nodes["dom-workspace"] = _n(
        "dom-workspace", RequirementKind.DOMAIN_CONCEPT,
        "A shared boundary isolating one team's tasks and members from other teams.",
        Priority.MUST,
    )
    nodes["dom-user-account"] = _n(
        "dom-user-account", RequirementKind.DOMAIN_CONCEPT,
        "An identity with credentials used to access the product.",
        Priority.MUST,
    )

    # --- functional: identity ---------------------------------------------
    nodes["req-auth-register"] = _n(
        "req-auth-register", RequirementKind.FUNCTIONAL,
        "A person can create a user account with credentials.",
        Priority.MUST,
        acceptance_criteria=[
            "Valid credentials create exactly one account.",
            "A duplicate identity is rejected with an explicit error.",
            "Malformed credentials are rejected with an explicit error.",
        ],
    )
    nodes["req-auth-login"] = _n(
        "req-auth-login", RequirementKind.FUNCTIONAL,
        "An account holder can authenticate and receive a session usable for subsequent calls.",
        Priority.MUST,
        acceptance_criteria=[
            "Valid credentials authenticate successfully.",
            "Invalid credentials are rejected without revealing which part failed.",
            "Calls without a valid session are rejected.",
        ],
    )

    # --- functional: task CRUD --------------------------------------------
    nodes["req-task-create"] = _n(
        "req-task-create", RequirementKind.FUNCTIONAL,
        "An authenticated workspace member can create a task in that workspace.",
        Priority.MUST,
        acceptance_criteria=[
            "A created task is retrievable with its title, status, and owner.",
            "A task without a title is rejected with an explicit error.",
            "A caller who is not a workspace member is rejected.",
        ],
    )
    nodes["req-task-read"] = _n(
        "req-task-read", RequirementKind.FUNCTIONAL,
        "An authenticated workspace member can list and retrieve tasks in that workspace.",
        Priority.MUST,
        acceptance_criteria=[
            "A member sees exactly the tasks of workspaces they belong to.",
            "A caller sees no tasks from workspaces they do not belong to.",
        ],
    )
    nodes["req-task-update"] = _n(
        "req-task-update", RequirementKind.FUNCTIONAL,
        "An authenticated workspace member can modify a task's title, status, or assignee.",
        Priority.MUST,
        acceptance_criteria=[
            "Applied updates are persisted and retrievable.",
            "Updates to a nonexistent task are rejected with an explicit error.",
        ],
    )
    nodes["req-task-delete"] = _n(
        "req-task-delete", RequirementKind.FUNCTIONAL,
        "An authenticated workspace member can delete a task.",
        Priority.MUST,
        acceptance_criteria=[
            "A deleted task is no longer retrievable.",
            "Deleting a nonexistent task is rejected with an explicit error.",
        ],
    )
    nodes["req-task-assign"] = _n(
        "req-task-assign", RequirementKind.FUNCTIONAL,
        "An authenticated workspace member can assign a task to a member of the same workspace.",
        Priority.SHOULD,
        acceptance_criteria=[
            "The assignee is recorded on the task and retrievable.",
            "Assigning to a non-member is rejected with an explicit error.",
        ],
    )
    nodes["req-workspace-members"] = _n(
        "req-workspace-members", RequirementKind.FUNCTIONAL,
        "A workspace admin can add and remove workspace members and change member roles.",
        Priority.SHOULD,
        acceptance_criteria=[
            "An added member can access the workspace afterwards.",
            "A removed member can no longer access the workspace.",
            "A non-admin cannot change membership or roles.",
        ],
    )

    # --- non-functional ----------------------------------------------------
    nodes["req-credential-safety"] = _n(
        "req-credential-safety", RequirementKind.NON_FUNCTIONAL,
        "User credentials are stored only in non-reversible form and are never returned by the product.",
        Priority.MUST,
        acceptance_criteria=[
            "Stored credential material differs from the submitted secret.",
            "No product response contains secret material.",
        ],
    )
    nodes["req-tenant-isolation"] = _n(
        "req-tenant-isolation", RequirementKind.NON_FUNCTIONAL,
        "Activity in one workspace is invisible and unmodifiable from any other workspace.",
        Priority.MUST,
        acceptance_criteria=[
            "A member of workspace A cannot read workspace B resources.",
            "A member of workspace A cannot modify workspace B resources.",
        ],
    )
    nodes["req-durability"] = _n(
        "req-durability", RequirementKind.NON_FUNCTIONAL,
        "Committed task and membership state survives process restarts.",
        Priority.SHOULD,
        acceptance_criteria=[
            "State committed before a restart is retrievable after the restart.",
        ],
    )

    # --- constraints -------------------------------------------------------
    nodes["con-multiuser"] = _n(
        "con-multiuser", RequirementKind.CONSTRAINT,
        "The product serves multiple users concurrently with per-user authentication.",
        Priority.MUST,
    )
    nodes["con-api-surface"] = _n(
        "con-api-surface", RequirementKind.CONSTRAINT,
        "All product capabilities are exposed through a single versioned product interface.",
        Priority.SHOULD,
    )

    # --- deferred alternative (resolved conflict) --------------------------
    nodes["req-anon-sharing"] = _n(
        "req-anon-sharing", RequirementKind.FUNCTIONAL,
        "Anyone holding a task link can view that task without authenticating.",
        Priority.COULD,
        acceptance_criteria=[
            "If ever offered, link access is recorded in the task audit trail.",
        ],
        ambiguity_score=0.3,
        resolution_ref=(
            "decision-vs1-01: deferred; all access requires authentication "
            "(see req-auth-login) until an explicit sharing model is approved."
        ),
    )

    # --- ownership ----------------------------------------------------------
    owned_by_user = [
        "req-auth-register", "req-auth-login", "req-task-create", "req-task-read",
        "req-task-update", "req-task-delete", "req-task-assign",
        "req-credential-safety", "req-tenant-isolation", "req-durability",
        "req-anon-sharing", "con-multiuser", "con-api-surface",
        "dom-task", "dom-workspace", "dom-user-account",
    ]
    for i, req_id in enumerate(owned_by_user):
        edges[f"own-{i:02d}"] = _e(
            f"own-{i:02d}", RequirementEdgeType.OWNED_BY, req_id, "stk-end-user")
    edges["own-admin"] = _e(
        "own-admin", RequirementEdgeType.OWNED_BY, "req-workspace-members",
        "stk-workspace-admin")

    # --- dependencies -------------------------------------------------------
    deps = [
        ("dep-01", "req-auth-login", "req-auth-register"),
        ("dep-02", "req-task-create", "req-auth-login"),
        ("dep-03", "req-task-read", "req-auth-login"),
        ("dep-04", "req-task-update", "req-task-create"),
        ("dep-05", "req-task-delete", "req-task-create"),
        ("dep-06", "req-task-assign", "req-task-create"),
        ("dep-07", "req-workspace-members", "req-auth-login"),
        ("dep-08", "req-tenant-isolation", "req-workspace-members"),
        ("dep-09", "req-credential-safety", "req-auth-register"),
        ("dep-10", "req-durability", "req-task-create"),
    ]
    for eid, src, tgt in deps:
        edges[eid] = _e(eid, RequirementEdgeType.DEPENDS_ON, src, tgt)

    # --- refinements ---------------------------------------------------------
    refines = [
        ("ref-01", "req-task-create", "dom-task"),
        ("ref-02", "req-task-read", "dom-task"),
        ("ref-03", "req-task-update", "dom-task"),
        ("ref-04", "req-task-delete", "dom-task"),
        ("ref-05", "req-task-assign", "dom-task"),
        ("ref-06", "req-workspace-members", "dom-workspace"),
        ("ref-07", "req-auth-register", "dom-user-account"),
        ("ref-08", "req-auth-login", "dom-user-account"),
    ]
    for eid, src, tgt in refines:
        edges[eid] = _e(eid, RequirementEdgeType.REFINES, src, tgt)

    # --- resolved conflict ----------------------------------------------------
    edges["confl-01"] = _e(
        "confl-01", RequirementEdgeType.CONFLICTS_WITH,
        "req-anon-sharing", "req-tenant-isolation",
        resolution_ref=(
            "decision-vs1-01: deferred; all access requires authentication "
            "(see req-auth-login) until an explicit sharing model is approved."
        ),
    )

    return RequirementGraph(schema_version=SCHEMA_VERSION, nodes=nodes, edges=edges)
