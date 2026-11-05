"""Loss-aware ISRRevision -> CompilationPlan projection."""
from __future__ import annotations

from isr.core.behavior import ConsequenceBehavior, validate_behavior_payload
from isr.core.graph import EdgeType, NodeType
from isr.core.revision import ISRRevision
from compiler.core.plan import (
    ApiOperation,
    CompilationPlan,
    Consequence,
    EffectBinding,
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


def _isr_to_plan_stabilization(revision: ISRRevision) -> CompilationPlan:
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
    api_services: dict[str, list[str]] = {}
    services: list[Service] = []
    apis: list[ApiOperation] = []
    effects: list[Effect] = []
    invariants: list[Invariant] = []
    consequence_nodes: dict[str, object] = {}

    for node_id, node in sorted(graph.nodes.items()):
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
            effects.append(Effect(
                id=node_id,
                name=label,
                behavior=_behavior(node),
                declared_policy={
                    key: value for key, value in node.properties.items()
                    if key not in {"label", "behavior"}
                },
            ))
        elif node.type == NodeType.INVARIANT:
            invariants.append(Invariant(id=node_id, name=label, behavior=_behavior(node)))
        elif node.type == NodeType.CONSEQUENCE:
            consequence_nodes[node_id] = node

    effects_by_id = {effect.id: effect for effect in effects}
    api_ids = {api.id for api in apis}
    effect_bindings: list[EffectBinding] = []
    consequence_targets: dict[str, list[str]] = {}

    for _, edge in sorted(graph.edges.items()):
        if edge.type == EdgeType.EXPOSES and edge.target_id in api_ids:
            api_services.setdefault(edge.target_id, []).append(edge.source_id)
        elif edge.type == EdgeType.CAUSES_EFFECT:
            if edge.target_id not in effects_by_id or edge.source_id not in graph.nodes:
                raise ValueError(
                    f"CAUSES_EFFECT edge {edge.id!r} has an unresolved source or effect target"
                )
            effect_bindings.append(EffectBinding(
                edge_id=edge.id, source_id=edge.source_id, effect_id=edge.target_id
            ))
            if graph.nodes[edge.source_id].type == NodeType.SERVICE:
                svc_effects.setdefault(edge.source_id, []).append(effects_by_id[edge.target_id])
        elif edge.type == EdgeType.CONSEQUENCE_OF:
            if edge.source_id not in consequence_nodes:
                raise ValueError(
                    f"CONSEQUENCE_OF edge {edge.id!r} does not originate at a consequence node"
                )
            if edge.target_id not in effects_by_id and edge.target_id not in {item.id for item in invariants}:
                raise ValueError(
                    f"CONSEQUENCE_OF edge {edge.id!r} has an unresolved effect/invariant target"
                )
            consequence_targets.setdefault(edge.source_id, []).append(edge.target_id)
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

    ambiguous_api_services = {
        api_id: sorted(set(service_ids))
        for api_id, service_ids in api_services.items()
        if len(set(service_ids)) != 1
    }
    if ambiguous_api_services:
        raise ValueError(
            "API operations must have exactly one explicit EXPOSES service binding: "
            f"{ambiguous_api_services}"
        )
    apis = [
        api.model_copy(update={
            "security_policies": api_security.get(api.id, []),
            "service_id": next(iter(api_services.get(api.id, ())), None),
        })
        for api in apis
    ]

    api_by_id = {api.id: api for api in apis}
    frontend_interactions: dict[str, FrontendInteraction] = {}
    for node_id, node in sorted(graph.nodes.items()):
        if node.type != NodeType.FRONTEND_INTERACTION:
            continue
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        target_ids = [
            edge.target_id for _, edge in sorted(graph.edges.items())
            if edge.type == EdgeType.INVOKES and edge.source_id == node_id
        ]
        if len(target_ids) > 1:
            raise ValueError(
                f"frontend interaction {node_id!r} has multiple INVOKES targets: {sorted(target_ids)}"
            )
        target_api = None
        if target_ids:
            target_id = target_ids[0]
            if target_id not in graph.nodes:
                raise ValueError(
                    f"frontend interaction {node_id!r} invokes missing target {target_id!r}"
                )
            if graph.nodes[target_id].type != NodeType.API or target_id not in api_by_id:
                raise ValueError(
                    f"frontend interaction {node_id!r} invokes unsupported non-API target {target_id!r}"
                )
            target_api = api_by_id[target_id]
        else:
            interaction_behavior = _behavior(node)
            if interaction_behavior is None or interaction_behavior.action != "toggle":
                raise ValueError(
                    f"frontend interaction {node_id!r} has no explicit INVOKES target "
                    "and is not a declared local toggle"
                )
        frontend_interactions[node_id] = FrontendInteraction(
            id=node_id,
            name=label,
            behavior=_behavior(node),
            target_api_operation=target_api,
        )

    frontend_routes: list[FrontendRoute] = []
    for node_id, node in sorted(graph.nodes.items()):
        if node.type != NodeType.FRONTEND_ROUTE:
            continue
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        route_api_ids = [
            edge.target_id for _, edge in sorted(graph.edges.items())
            if edge.type == EdgeType.ROUTES_TO and edge.source_id == node_id
        ]
        interaction_ids = [
            edge.target_id for _, edge in sorted(graph.edges.items())
            if edge.type == EdgeType.CONTAINS and edge.source_id == node_id
            and edge.target_id in frontend_interactions
        ]
        missing_route_apis = sorted(set(route_api_ids) - set(api_by_id))
        if missing_route_apis:
            raise ValueError(
                f"frontend route {node_id!r} references unresolved API targets: {missing_route_apis}"
            )
        frontend_routes.append(FrontendRoute(
            id=node_id,
            name=label,
            behavior=_behavior(node),
            api_operations=[api_by_id[item] for item in sorted(set(route_api_ids))],
            interactions=[frontend_interactions[item] for item in sorted(set(interaction_ids))],
        ))

    for node_id, node in sorted(graph.nodes.items()):
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

    consequences: list[Consequence] = []
    for consequence_id, node in sorted(consequence_nodes.items()):
        targets = tuple(sorted(set(consequence_targets.get(consequence_id, ()))))
        if not targets:
            raise ValueError(
                f"consequence {consequence_id!r} has no explicit CONSEQUENCE_OF binding"
            )
        properties = {
            key: value for key, value in node.properties.items() if key != "label"
        }
        behavior = ConsequenceBehavior.model_validate(properties)
        consequences.append(Consequence(
            id=consequence_id, behavior=behavior, related_node_ids=targets
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
        effect_bindings=effect_bindings,
        consequences=consequences,
        invariants=invariants,
        frontend_routes=frontend_routes,
        frontend_interactions=list(frontend_interactions.values()),
    )



def isr_revision_to_compiler_ir(
    revision: ISRRevision,
    *,
    source_architecture_candidate_content_hash: str | None = None,
    architecture_reference_reason: str | None = None,
):
    """Create the canonical CompilerIR, retaining the legacy plan as projection."""
    from compiler.core.canonical_ir import CompilerIR

    execution_plan = _isr_to_plan_stabilization(revision)
    return CompilerIR.from_revision(
        revision,
        execution_plan,
        source_architecture_candidate_content_hash=source_architecture_candidate_content_hash,
        architecture_reference_reason=architecture_reference_reason,
    )


def isr_to_plan(revision: ISRRevision) -> CompilationPlan:
    """Compatibility adapter routed through canonical CompilerIR.

    The returned plan retains the historical plan_id derivation from the ISR
    content_hash. New code should consume isr_revision_to_compiler_ir and treat
    CompilationPlan only as its transitional execution_plan projection.
    """
    compiler_ir = isr_revision_to_compiler_ir(
        revision,
        architecture_reference_reason=(
            "This compatibility entry point receives only an ISRRevision; "
            "its source route supplies no ArchitectureCandidate reference."
        ),
    )
    return compiler_ir.execution_plan
