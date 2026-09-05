"""VS-D02 — canonical ISR revision for the VS-1 task tracker.

Built from the frozen VS-D01 RequirementGraph (`vertical_slice.requirements`).
Every functional and non-functional requirement is represented by a
REQUIREMENT_REF node whose ref_id resolves to the requirement ID, preserving
lineage. Technology-neutral and fail-closed per isr/core invariants
(including the R1-D.1 testing-mechanism check).

Deterministic: fixed provenance timestamp, stable IDs, no randomness.
"""

from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from vertical_slice.requirements import build_task_tracker_requirements

SYSTEM_ID = "vs1-task-tracker"
REVISION_ID = "vs1-rev1"
SCHEMA_VERSION = "1.0"
# Fixed for determinism (content_hash excludes provenance, but revision
# equality across builds requires a stable timestamp).
FIXED_CREATED_AT = "2026-09-06T00:00:00+00:00"


def _node(id: str, type: NodeType, **props: object) -> Node:
    return Node(id=id, type=type, properties=dict(props))


def _edge(id: str, type: EdgeType, source_id: str, target_id: str) -> Edge:
    return Edge(id=id, type=type, source_id=source_id, target_id=target_id)


# (capability node id, requirement id, service node id)
_CAPABILITIES: tuple[tuple[str, str, str], ...] = (
    ("cap-registration", "req-auth-register", "svc-identity"),
    ("cap-authentication", "req-auth-login", "svc-identity"),
    ("cap-task-create", "req-task-create", "svc-task"),
    ("cap-task-read", "req-task-read", "svc-task"),
    ("cap-task-update", "req-task-update", "svc-task"),
    ("cap-task-delete", "req-task-delete", "svc-task"),
    ("cap-task-assign", "req-task-assign", "svc-task"),
    ("cap-membership-mgmt", "req-workspace-members", "svc-workspace"),
)


def build_task_tracker_isr() -> ISRRevision:
    """Build the VS-1 canonical ISR revision (deterministic)."""
    graph = build_task_tracker_requirements()  # frozen upstream input
    nodes: dict[str, Node] = {}
    edges: dict[str, Edge] = {}

    # --- capabilities + requirement refs ----------------------------------
    for cap_id, req_id, _svc in _CAPABILITIES:
        if req_id not in graph.nodes:
            raise ValueError(f"VS-D02 lineage break: {req_id} missing from requirements graph")
        label = graph.nodes[req_id].statement
        nodes[cap_id] = _node(cap_id, NodeType.CAPABILITY, label=label)
        nodes[f"reqref-{req_id[4:]}"] = _node(
            f"reqref-{req_id[4:]}", NodeType.REQUIREMENT_REF, ref_id=req_id)
        edges[f"sat-{cap_id[4:]}"] = _edge(
            f"sat-{cap_id[4:]}", EdgeType.SATISFIES, cap_id, f"reqref-{req_id[4:]}")

    # non-functional requirement refs (lineage; satisfied structurally below)
    for req_id in ("req-credential-safety", "req-tenant-isolation", "req-durability"):
        if req_id not in graph.nodes:
            raise ValueError(f"VS-D02 lineage break: {req_id} missing from requirements graph")
        nodes[f"reqref-{req_id[4:]}"] = _node(
            f"reqref-{req_id[4:]}", NodeType.REQUIREMENT_REF, ref_id=req_id)

    # --- services + APIs ----------------------------------------------------
    nodes["svc-identity"] = _node("svc-identity", NodeType.SERVICE, label="identity service")
    nodes["svc-task"] = _node("svc-task", NodeType.SERVICE, label="task service")
    nodes["svc-workspace"] = _node("svc-workspace", NodeType.SERVICE, label="workspace service")
    nodes["api-identity"] = _node("api-identity", NodeType.API, label="identity interface")
    nodes["api-task"] = _node("api-task", NodeType.API, label="task interface")
    nodes["api-workspace"] = _node("api-workspace", NodeType.API, label="workspace interface")
    for svc, api in (("svc-identity", "api-identity"), ("svc-task", "api-task"),
                     ("svc-workspace", "api-workspace")):
        edges[f"exp-{svc[4:]}"] = _edge(f"exp-{svc[4:]}", EdgeType.EXPOSES, svc, api)
    for cap_id, _req, svc in _CAPABILITIES:
        edges[f"impl-{cap_id[4:]}"] = _edge(
            f"impl-{cap_id[4:]}", EdgeType.IMPLEMENTED_BY, cap_id, svc)

    # --- data models ----------------------------------------------------------
    nodes["dm-task"] = _node("dm-task", NodeType.DATA_MODEL, entity_name="task")
    nodes["dm-workspace"] = _node("dm-workspace", NodeType.DATA_MODEL, entity_name="workspace")
    nodes["dm-user-account"] = _node(
        "dm-user-account", NodeType.DATA_MODEL, entity_name="user account")
    for eid, svc, dm in (("pers-identity", "svc-identity", "dm-user-account"),
                         ("pers-task", "svc-task", "dm-task"),
                         ("pers-workspace", "svc-task", "dm-workspace"),
                         ("pers-ws", "svc-workspace", "dm-workspace")):
        edges[eid] = _edge(eid, EdgeType.PERSISTS, svc, dm)

    # --- events ------------------------------------------------------------------
    nodes["ev-task-created"] = _node(
        "ev-task-created", NodeType.EVENT, label="task created")
    nodes["ev-task-updated"] = _node(
        "ev-task-updated", NodeType.EVENT, label="task updated")
    for eid, ev in (("pub-created", "ev-task-created"), ("pub-updated", "ev-task-updated")):
        edges[eid] = _edge(eid, EdgeType.PUBLISHES, "svc-task", ev)

    # --- security policies ---------------------------------------------------------
    nodes["sec-credential-safety"] = _node(
        "sec-credential-safety", NodeType.SECURITY_POLICY,
        label="credential safety policy")
    nodes["sec-tenant-isolation"] = _node(
        "sec-tenant-isolation", NodeType.SECURITY_POLICY,
        label="workspace isolation policy")
    for svc in ("svc-identity", "svc-task", "svc-workspace"):
        for pol in ("sec-credential-safety", "sec-tenant-isolation"):
            eid = f"sec-{svc[4:]}-{pol[4:]}"
            edges[eid] = _edge(eid, EdgeType.SECURED_BY, svc, pol)

    # --- service dependencies ---------------------------------------------------------
    for eid, src, tgt in (("dep-task-identity", "svc-task", "svc-identity"),
                          ("dep-workspace-identity", "svc-workspace", "svc-identity")):
        edges[eid] = _edge(eid, EdgeType.DEPENDS_ON, src, tgt)

    isr_graph = ISRGraph(nodes=nodes, edges=edges)
    requirement_ids = sorted(
        n.id for n in graph.nodes.values()
        if n.id.startswith("req-") or n.id.startswith("con-"))
    return ISRRevision.create(
        system_id=SYSTEM_ID,
        revision_id=REVISION_ID,
        schema_version=SCHEMA_VERSION,
        graph=isr_graph,
        provenance=Provenance(
            requirement_refs=requirement_ids,
            derivation_refs=["vs1-manual-intake-v1", "vs-d02-builder-v1"],
            created_by="vs1-slice",
            created_at=FIXED_CREATED_AT,
        ),
    )
