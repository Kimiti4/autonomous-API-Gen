"""Source obligations that must survive lowering into a candidate artifact.

The manifest is derived from the ISR graph, not from the plan under check.
A compiler that drops a binding and then emits a matching manifest still fails.
"""
from __future__ import annotations

from typing import Any

from isr.core.behavior import ConsequenceBehavior, validate_behavior_payload
from isr.core.graph import EdgeType, ISRGraph, NodeType

from compiler.core.plan import CompilationPlan, Consequence, Effect, EffectBinding, SecurityPolicy


def manifest_from_plan(plan: CompilationPlan) -> dict[str, Any]:
    """Candidate manifest for one plan. The revision hash is present only when lowering produced the plan."""
    manifest: dict[str, Any] = {
        "schema_version": "1",
        "effects": [item.model_dump(mode="json") for item in plan.effects],
        "effect_bindings": [item.model_dump(mode="json") for item in plan.effect_bindings],
        "consequences": [item.model_dump(mode="json") for item in plan.consequences],
    }
    if plan.obligation_revision:
        manifest["candidate_revision"] = plan.obligation_revision
    return manifest


def obligations_from_graph(graph: ISRGraph) -> dict[str, Any]:
    """Project effect, binding, and consequence obligations directly from ISR nodes and edges."""
    security = {
        node_id: node
        for node_id, node in graph.nodes.items()
        if node.type == NodeType.SECURITY_POLICY
    }
    effect_ids = {
        node_id for node_id, node in graph.nodes.items() if node.type == NodeType.EFFECT
    }
    invariant_ids = {
        node_id for node_id, node in graph.nodes.items() if node.type == NodeType.INVARIANT
    }
    policies_for: dict[str, list[SecurityPolicy]] = {}
    bindings: list[EffectBinding] = []
    targets: dict[str, list[str]] = {}
    for edge in graph.edges.values():
        if edge.type == EdgeType.SECURED_BY and edge.source_id in effect_ids and edge.target_id in security:
            node = security[edge.target_id]
            policies_for.setdefault(edge.source_id, []).append(SecurityPolicy(
                policy_id=node.id,
                behavior=validate_behavior_payload(node.type.value, node.properties["behavior"])
                if "behavior" in node.properties else None,
            ))
        elif edge.type == EdgeType.CAUSES_EFFECT and edge.target_id in effect_ids and edge.source_id in graph.nodes:
            bindings.append(EffectBinding(
                edge_id=edge.id, source_id=edge.source_id, effect_id=edge.target_id,
            ))
        elif edge.type == EdgeType.CONSEQUENCE_OF and edge.target_id in effect_ids | invariant_ids:
            source = graph.nodes.get(edge.source_id)
            if source is not None and source.type == NodeType.CONSEQUENCE:
                targets.setdefault(edge.source_id, []).append(edge.target_id)

    effects: list[Effect] = []
    consequences: list[Consequence] = []
    for node_id, node in graph.nodes.items():
        label = node.properties.get("label", node_id.split(":", 1)[-1])
        if node.type == NodeType.EFFECT:
            effects.append(Effect(
                id=node_id,
                name=label,
                behavior=validate_behavior_payload(node.type.value, node.properties["behavior"])
                if "behavior" in node.properties else None,
                declared_policy={
                    key: value for key, value in node.properties.items()
                    if key not in {"label", "behavior"}
                },
                security_policies=policies_for.get(node_id, []),
            ))
        elif node.type == NodeType.CONSEQUENCE:
            related = tuple(sorted(set(targets.get(node_id, ()))))
            properties = {key: value for key, value in node.properties.items() if key != "label"}
            consequences.append(Consequence(
                id=node_id,
                behavior=ConsequenceBehavior.model_validate(properties),
                related_node_ids=related,
            ))
    return {
        "effects": [item.model_dump(mode="json") for item in effects],
        "effect_bindings": [item.model_dump(mode="json") for item in bindings],
        "consequences": [item.model_dump(mode="json") for item in consequences],
    }


def assert_lowering_preserves_obligations(graph: ISRGraph, plan: CompilationPlan) -> None:
    """Fail when the plan is not the graph's effect, binding, and consequence set."""
    source = obligations_from_graph(graph)
    lowered = manifest_from_plan(plan)
    lowered = {
        "effects": lowered["effects"],
        "effect_bindings": lowered["effect_bindings"],
        "consequences": lowered["consequences"],
    }
    if source == lowered:
        return
    source_bindings = [(item["edge_id"], item["source_id"], item["effect_id"]) for item in source["effect_bindings"]]
    lowered_bindings = [(item["edge_id"], item["source_id"], item["effect_id"]) for item in lowered["effect_bindings"]]
    raise ValueError(
        "lowering dropped or rewrote an effect, consequence, or source binding: "
        f"effects { [item['id'] for item in source['effects']] } -> { [item['id'] for item in lowered['effects']] }; "
        f"bindings {source_bindings} -> {lowered_bindings}; "
        f"consequences { [item['id'] for item in source['consequences']] } -> { [item['id'] for item in lowered['consequences']] }"
    )
