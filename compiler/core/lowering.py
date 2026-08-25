"""isr_to_plan — lower an ISRRevision into a CompilationPlan."""
from __future__ import annotations
from isr.core.revision import ISRRevision
from isr.core.graph import NodeType, EdgeType
from compiler.core.plan import (
    CompilationPlan,
    DataModel,
    Event,
    SecurityPolicy,
    Service,
)


def isr_to_plan(revision: ISRRevision) -> CompilationPlan:
    """Lower an ISR revision to a technology-neutral CompilationPlan.

    This function operates over the ISR graph taxonomy:
    - SERVICE nodes become Plan Services
    - DATA_MODEL nodes (persisted by services) become Plan DataModels
    - EVENT nodes (published/consumed by services) become Plan Events
    - SECURITY_POLICY nodes (securing services) become Plan SecurityPolicies
    """
    graph = revision.graph

    services: list[Service] = []
    dm_by_id: dict[str, DataModel] = {}
    ev_by_id: dict[str, Event] = {}
    sec_by_id: dict[str, SecurityPolicy] = {}

    svc_data_models: dict[str, list[DataModel]] = {}
    svc_pub_events: dict[str, list[Event]] = {}
    svc_cons_events: dict[str, list[Event]] = {}
    svc_security: dict[str, list[SecurityPolicy]] = {}

    for nid, node in graph.nodes.items():
        if node.type == NodeType.DATA_MODEL:
            name = node.properties.get("label", nid.split(":", 1)[-1])
            dm_by_id[nid] = DataModel(id=nid, entity_name=name)
        elif node.type == NodeType.EVENT:
            name = node.properties.get("label", nid.split(":", 1)[-1])
            ev_by_id[nid] = Event(id=nid, name=name)
        elif node.type == NodeType.SECURITY_POLICY:
            sec_by_id[nid] = SecurityPolicy(policy_id=nid)

    for eid, edge in graph.edges.items():
        if edge.type == EdgeType.PERSISTS and edge.target_id in dm_by_id:
            svc_data_models.setdefault(edge.source_id, []).append(dm_by_id[edge.target_id])
        elif edge.type == EdgeType.PUBLISHES and edge.target_id in ev_by_id:
            svc_pub_events.setdefault(edge.source_id, []).append(ev_by_id[edge.target_id])
        elif edge.type == EdgeType.CONSUMED_BY and edge.source_id in ev_by_id:
            svc_cons_events.setdefault(edge.target_id, []).append(ev_by_id[edge.source_id])
        elif edge.type == EdgeType.SECURED_BY and edge.target_id in sec_by_id:
            svc_security.setdefault(edge.source_id, []).append(sec_by_id[edge.target_id])

    for nid, node in graph.nodes.items():
        if node.type == NodeType.SERVICE:
            name = node.properties.get("label", nid.split(":", 1)[-1])
            services.append(Service(
                id=nid,
                name=name,
                data_models=svc_data_models.get(nid, []),
                published_events=svc_pub_events.get(nid, []),
                consumed_events=svc_cons_events.get(nid, []),
            ))

    all_security = list(sec_by_id.values())

    return CompilationPlan(
        plan_id=f"plan:{revision.content_hash[:16]}",
        isr_id=revision.system_id,
        services=services,
        security=all_security,
    )
