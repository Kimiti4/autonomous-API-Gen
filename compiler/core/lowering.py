"""Loss-aware ISRRevision -> CompilationPlan projection."""
from __future__ import annotations

from isr.core.behavior import validate_behavior_payload
from isr.core.graph import EdgeType, NodeType
from isr.core.revision import ISRRevision
from compiler.core.plan import (
    ApiOperation,
    CompilationPlan,
    DataModel,
    Effect,
    Event,
    FrontendInteraction,
    FrontendRoute,
    Invariant,
    SecurityPolicy,
    Service,
)


def _behavior(node):
    if "behavior" not in node.properties:
        return None
    return validate_behavior_payload(node.type.value, node.properties["behavior"])


def isr_to_plan(revision: ISRRevision) -> CompilationPlan:
    """Project all supported behavioral node payloads without flattening.

    This preserves semantics in typed plan carriers. It does not claim an
    emitter implements those semantics; backend capability gates are separate.
    """
    graph = revision.graph
    dm_by_id: dict[str, DataModel] = {}
    ev_by_id: dict[str, Event] = {}
    sec_by_id: dict[str, SecurityPolicy] = {}
    svc_data_models: dict[str, list[DataModel]] = {}
    svc_pub_events: dict[str, list[Event]] = {}
    svc_cons_events: dict[str, list[Event]] = {}
    svc_security: dict[str, list[SecurityPolicy]] = {}
    svc_effects: dict[str, list[Effect]] = {}
    api_security: dict[str, list[SecurityPolicy]] = {}
    services: list[Service] = []
    apis: list[ApiOperation] = []
    effects: list[Effect] = []
    invariants: list[Invariant] = []

    for node_id, node in graph.nodes.items():
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        if node.type == NodeType.DATA_MODEL:
            dm_by_id[node_id] = DataModel(
                id=node_id, entity_name=label, behavior=_behavior(node)
            )
        elif node.type == NodeType.EVENT:
            ev_by_id[node_id] = Event(
                id=node_id, name=label, behavior=_behavior(node)
            )
        elif node.type == NodeType.SECURITY_POLICY:
            sec_by_id[node_id] = SecurityPolicy(
                policy_id=node_id, behavior=_behavior(node)
            )
        elif node.type == NodeType.API:
            apis.append(ApiOperation(
                id=node_id,
                name=label,
                behavior=_behavior(node),
                security_policies=[],
            ))
        elif node.type == NodeType.EFFECT:
            effects.append(Effect(id=node_id, name=label, behavior=_behavior(node)))
        elif node.type == NodeType.INVARIANT:
            invariants.append(Invariant(id=node_id, name=label, behavior=_behavior(node)))

    effects_by_id = {effect.id: effect for effect in effects}

    for edge in graph.edges.values():
        if edge.type == EdgeType.CAUSES_EFFECT and edge.target_id in effects_by_id:
            svc_effects.setdefault(edge.source_id, []).append(effects_by_id[edge.target_id])
        elif edge.type == EdgeType.PERSISTS and edge.target_id in dm_by_id:
            svc_data_models.setdefault(edge.source_id, []).append(dm_by_id[edge.target_id])
        elif edge.type == EdgeType.PUBLISHES and edge.target_id in ev_by_id:
            svc_pub_events.setdefault(edge.source_id, []).append(ev_by_id[edge.target_id])
        elif edge.type == EdgeType.CONSUMED_BY and edge.source_id in ev_by_id:
            svc_cons_events.setdefault(edge.target_id, []).append(ev_by_id[edge.source_id])
        elif edge.type == EdgeType.SECURED_BY and edge.target_id in sec_by_id:
            if edge.source_id in graph.nodes and graph.nodes[edge.source_id].type == NodeType.API:
                api_security.setdefault(edge.source_id, []).append(sec_by_id[edge.target_id])
            else:
                svc_security.setdefault(edge.source_id, []).append(sec_by_id[edge.target_id])

    apis = [api.model_copy(update={"security_policies": api_security.get(api.id, [])}) for api in apis]

    api_by_id = {api.id: api for api in apis}
    frontend_interactions: dict[str, FrontendInteraction] = {}
    for node_id, node in graph.nodes.items():
        if node.type != NodeType.FRONTEND_INTERACTION:
            continue
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        target_ids = [
            edge.target_id for edge in graph.edges.values()
            if edge.type == EdgeType.INVOKES and edge.source_id == node_id
        ]
        target_api = api_by_id.get(target_ids[0]) if len(target_ids) == 1 else None
        frontend_interactions[node_id] = FrontendInteraction(
            id=node_id,
            name=label,
            behavior=_behavior(node),
            target_api_operation=target_api,
        )

    frontend_routes: list[FrontendRoute] = []
    for node_id, node in graph.nodes.items():
        if node.type != NodeType.FRONTEND_ROUTE:
            continue
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        route_api_ids = [
            edge.target_id for edge in graph.edges.values()
            if edge.type == EdgeType.ROUTES_TO and edge.source_id == node_id
        ]
        interaction_ids = [
            edge.target_id for edge in graph.edges.values()
            if edge.type == EdgeType.CONTAINS and edge.source_id == node_id
            and edge.target_id in frontend_interactions
        ]
        frontend_routes.append(FrontendRoute(
            id=node_id,
            name=label,
            behavior=_behavior(node),
            api_operations=[api_by_id[item] for item in route_api_ids if item in api_by_id],
            interactions=[frontend_interactions[item] for item in interaction_ids],
        ))

    for node_id, node in graph.nodes.items():
        if node.type == NodeType.SERVICE:
            label = node.properties.get("label", node_id.split(":", 1)[-1])
            services.append(Service(
                id=node_id,
                name=label,
                data_models=svc_data_models.get(node_id, []),
                published_events=svc_pub_events.get(node_id, []),
                consumed_events=svc_cons_events.get(node_id, []),
                effects=svc_effects.get(node_id, []),
                behavior=_behavior(node),
                security_policies=svc_security.get(node_id, []),
            ))

    return CompilationPlan(
        plan_id=f"plan:{revision.content_hash[:16]}",
        isr_id=revision.system_id,
        services=services,
        data_models=list(dm_by_id.values()),
        events=list(ev_by_id.values()),
        security=list(sec_by_id.values()),
        apis=apis,
        effects=effects,
        invariants=invariants,
        frontend_routes=frontend_routes,
        frontend_interactions=list(frontend_interactions.values()),
    )
