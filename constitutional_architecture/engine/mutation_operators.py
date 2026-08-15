"""
Concrete Mutation Operators — Typed graph mutations that produce EIRs.

Each operator is a first-class MutationOperatorSpec registered with the
MutationRegistry. Operators never know about ISR model objects — they
operate exclusively on TypedGraph and produce Transformations.

Constitutional constraint: zero knowledge of compilers, backends, or frameworks.
"""

from __future__ import annotations

import uuid
from typing import Any

from constitutional_architecture.engine.mutation_registry import MutationOperatorSpec, MutationRegistry
from constitutional_architecture.isr.eir.taxonomy import KNOWN_TRANSFORMATIONS, MutationCategory, MutationClass
from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeAttributes, EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


def register_all_operators(registry: MutationRegistry) -> None:
    """Register every concrete mutation operator with the registry."""

    # ------------------------------------------------------------------ #
    # STRUCTURAL: Add Entity
    # ------------------------------------------------------------------ #
    def _add_entity_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None and any(
            graph.get_node(n.id).node_type == NodeType.MODULE
            for n in [graph.get_node(target)] if n
        )

    def _add_entity_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        name = params.get("name", "NewEntity")
        eid = f"ent:{uuid.uuid4().hex[:8]}"
        g.add_node(GraphNode(
            id=eid, node_type=NodeType.ENTITY, label=name,
            attributes={"name": name},
            parent_id=target,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{eid}:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=eid, edge_type=EdgeType.OWNS,
        ))
        return g, {"entity_id": eid, "entity_name": name}

    registry.register(MutationOperatorSpec(
        identifier="structural_add_entity",
        category=MutationCategory.STRUCTURAL,
        mutation_class=MutationClass.ADDITIVE,
        description="Add a new entity to a module",
        risk_level="low",
        affected_node_types=("entity",),
        expected_fitness_impact={"complexity": 0.02, "maintainability": -0.01},
        precondition_fn=_add_entity_precondition,
        apply_fn=_add_entity_apply,
    ))

    # ------------------------------------------------------------------ #
    # STRUCTURAL: Add Service
    # ------------------------------------------------------------------ #
    def _add_service_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None and any(
            graph.get_node(n.id).node_type == NodeType.MODULE
            for n in [graph.get_node(target)] if n
        )

    def _add_service_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        name = params.get("name", "NewService")
        sid = f"svc:{uuid.uuid4().hex[:8]}"
        g.add_node(GraphNode(
            id=sid, node_type=NodeType.SERVICE, label=name,
            attributes={"name": name, "is_stateless": True},
            parent_id=target,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{sid}:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=sid, edge_type=EdgeType.OWNS,
        ))
        return g, {"service_id": sid, "service_name": name}

    registry.register(MutationOperatorSpec(
        identifier="structural_add_service",
        category=MutationCategory.STRUCTURAL,
        mutation_class=MutationClass.ADDITIVE,
        description="Add a new service to a module",
        risk_level="low",
        affected_node_types=("service",),
        expected_fitness_impact={"complexity": 0.03, "scalability": 0.02},
        precondition_fn=_add_service_precondition,
        apply_fn=_add_service_apply,
    ))

    # ------------------------------------------------------------------ #
    # STRUCTURAL: Split Module
    # ------------------------------------------------------------------ #
    def _split_module_precondition(graph: TypedGraph, target: str) -> bool:
        node = graph.get_node(target)
        if node is None or node.node_type != NodeType.MODULE:
            return False
        children = [n for n in graph._nodes.values() if n.parent_id == target]
        entity_count = sum(1 for c in children if c.node_type == NodeType.ENTITY)
        return entity_count >= 2

    def _split_module_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        extract_names = params.get("extract_entities", [])
        new_mod_name = params.get("new_module_name", "SplitModule")

        orig = g.get_node(target)
        if orig is None:
            return g, {"error": "target not found"}

        children = [n for n in g._nodes.values() if n.parent_id == target]

        new_mod_id = f"mod:{uuid.uuid4().hex[:8]}"
        sys_id = orig.parent_id or ""
        g.add_node(GraphNode(
            id=new_mod_id, node_type=NodeType.MODULE, label=new_mod_name,
            parent_id=sys_id,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{sys_id}->{new_mod_id}:{uuid.uuid4().hex[:4]}",
            source_id=sys_id, target_id=new_mod_id, edge_type=EdgeType.OWNS,
        ))

        moved = []
        for child in children:
            if child.label in extract_names or child.id in extract_names:
                g._nodes[child.id] = GraphNode(
                    id=child.id, node_type=child.node_type, label=child.label,
                    attributes=child.attributes, parent_id=new_mod_id,
                )
                moved.append(child.id)

        return g, {"new_module_id": new_mod_id, "new_module_name": new_mod_name, "moved_nodes": moved}

    registry.register(MutationOperatorSpec(
        identifier="structural_split_module",
        category=MutationCategory.STRUCTURAL,
        mutation_class=MutationClass.STRUCTURAL,
        description="Split a module into two by extracting entities/services",
        risk_level="high",
        affected_node_types=("module", "entity"),
        expected_fitness_impact={"maintainability": 0.1, "cohesion": 0.08, "complexity": 0.05},
        reversible=True,
        precondition_fn=_split_module_precondition,
        apply_fn=_split_module_apply,
    ))

    # ------------------------------------------------------------------ #
    # STRUCTURAL: Extract Interface
    # ------------------------------------------------------------------ #
    def _extract_iface_precondition(graph: TypedGraph, target: str) -> bool:
        node = graph.get_node(target)
        if node is None or node.node_type != NodeType.SERVICE:
            return False
        has_iface = any(
            e.edge_type == EdgeType.IMPLEMENTS
            for e in graph.get_outgoing_edges(target)
        )
        return not has_iface

    def _extract_iface_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        svc = g.get_node(target)
        if svc is None:
            return g, {"error": "target not found"}
        mod_id = svc.parent_id or ""

        iface_id = f"iface:{uuid.uuid4().hex[:8]}"
        iface_name = params.get("name", f"{svc.label}API")
        g.add_node(GraphNode(
            id=iface_id, node_type=NodeType.INTERFACE, label=iface_name,
            attributes={"name": iface_name, "interface_type": "REST"},
            parent_id=mod_id,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{mod_id}->{iface_id}:{uuid.uuid4().hex[:4]}",
            source_id=mod_id, target_id=iface_id, edge_type=EdgeType.OWNS,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{iface_id}:impl:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=iface_id, edge_type=EdgeType.IMPLEMENTS,
        ))

        return g, {"interface_id": iface_id, "interface_name": iface_name}

    registry.register(MutationOperatorSpec(
        identifier="structural_extract_interface",
        category=MutationCategory.STRUCTURAL,
        mutation_class=MutationClass.STRUCTURAL,
        description="Extract an interface from a service",
        risk_level="medium",
        affected_node_types=("service", "interface"),
        expected_fitness_impact={"extensibility": 0.12, "maintainability": 0.05},
        precondition_fn=_extract_iface_precondition,
        apply_fn=_extract_iface_apply,
    ))

    # ------------------------------------------------------------------ #
    # TOPOLOGICAL: Add Depends-on Edge
    # ------------------------------------------------------------------ #
    def _add_depends_on_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None

    def _add_depends_on_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        dep_target = params.get("depends_on", "")
        if not dep_target or not g.get_node(dep_target):
            return g, {"error": f"dependency target '{dep_target}' not found"}
        g.add_edge(GraphEdge(
            id=f"e:{target}->{dep_target}:dep:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=dep_target, edge_type=EdgeType.DEPENDS_ON,
        ))
        return g, {"source": target, "target": dep_target}

    registry.register(MutationOperatorSpec(
        identifier="topological_add_dependency",
        category=MutationCategory.TOPOLOGICAL,
        mutation_class=MutationClass.ADDITIVE,
        description="Add a depends-on edge between two nodes",
        risk_level="medium",
        affected_node_types=("service", "module"),
        expected_fitness_impact={"coupling": -0.05},
        precondition_fn=_add_depends_on_precondition,
        apply_fn=_add_depends_on_apply,
    ))

    # ------------------------------------------------------------------ #
    # SECURITY: Add Security Policy to Interface
    # ------------------------------------------------------------------ #
    def _add_policy_precondition(graph: TypedGraph, target: str) -> bool:
        node = graph.get_node(target)
        if node is None or node.node_type != NodeType.INTERFACE:
            return False
        already_secured = any(
            e.edge_type == EdgeType.SECURED_BY
            for e in graph.get_outgoing_edges(target)
        )
        return not already_secured

    def _add_policy_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        iface = g.get_node(target)
        mod_id = iface.parent_id if iface else ""
        pol_name = params.get("policy", "AuthPolicy")

        pol_id = f"pol:{uuid.uuid4().hex[:8]}"
        g.add_node(GraphNode(
            id=pol_id, node_type=NodeType.POLICY, label=pol_name,
            attributes={
                "name": pol_name,
                "strategy": params.get("strategy", "OAuth2"),
                "policy_type": "authentication",
            },
            parent_id=mod_id,
        ))
        if mod_id:
            g.add_edge(GraphEdge(
                id=f"e:{mod_id}->{pol_id}:{uuid.uuid4().hex[:4]}",
                source_id=mod_id, target_id=pol_id, edge_type=EdgeType.OWNS,
            ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{pol_id}:sec:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=pol_id, edge_type=EdgeType.SECURED_BY,
        ))
        return g, {"policy_id": pol_id, "policy_name": pol_name}

    registry.register(MutationOperatorSpec(
        identifier="security_add_policy",
        category=MutationCategory.SECURITY,
        mutation_class=MutationClass.ADDITIVE,
        description="Add a security policy to an interface",
        risk_level="low",
        affected_node_types=("interface", "policy"),
        expected_fitness_impact={"security_coverage": 0.15},
        precondition_fn=_add_policy_precondition,
        apply_fn=_add_policy_apply,
    ))

    # ------------------------------------------------------------------ #
    # PERFORMANCE: Add Event (for async decoupling)
    # ------------------------------------------------------------------ #
    def _add_event_precondition(graph: TypedGraph, target: str) -> bool:
        node = graph.get_node(target)
        return node is not None and node.node_type == NodeType.SERVICE

    def _add_event_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        svc = g.get_node(target)
        mod_id = svc.parent_id if svc else ""
        evt_name = params.get("name", f"{svc.label}Event" if svc else "DomainEvent")

        evt_id = f"evt:{uuid.uuid4().hex[:8]}"
        g.add_node(GraphNode(
            id=evt_id, node_type=NodeType.EVENT, label=evt_name,
            attributes={"name": evt_name, "routing_key": evt_name.lower()},
            parent_id=mod_id,
        ))
        if mod_id:
            g.add_edge(GraphEdge(
                id=f"e:{mod_id}->{evt_id}:{uuid.uuid4().hex[:4]}",
                source_id=mod_id, target_id=evt_id, edge_type=EdgeType.OWNS,
            ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{evt_id}:emit:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=evt_id, edge_type=EdgeType.EMITS,
        ))
        return g, {"event_id": evt_id, "event_name": evt_name}

    registry.register(MutationOperatorSpec(
        identifier="performance_add_event",
        category=MutationCategory.PERFORMANCE,
        mutation_class=MutationClass.ADDITIVE,
        description="Add a domain event to a service",
        risk_level="low",
        affected_node_types=("service", "event"),
        expected_fitness_impact={"scalability": 0.05, "reliability": 0.03},
        precondition_fn=_add_event_precondition,
        apply_fn=_add_event_apply,
    ))

    # ------------------------------------------------------------------ #
    # OPERATIONAL: Add Documentation Node
    # ------------------------------------------------------------------ #
    def _add_doc_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None

    def _add_doc_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        doc_name = params.get("name", "ADR")
        doc_id = f"doc:{uuid.uuid4().hex[:8]}"
        g.add_node(GraphNode(
            id=doc_id, node_type=NodeType.DOCUMENTATION, label=doc_name,
            attributes={"name": doc_name},
            parent_id=target,
        ))
        g.add_edge(GraphEdge(
            id=f"e:{target}->{doc_id}:doc:{uuid.uuid4().hex[:4]}",
            source_id=target, target_id=doc_id, edge_type=EdgeType.DOCUMENTS,
        ))
        return g, {"doc_id": doc_id, "doc_name": doc_name}

    registry.register(MutationOperatorSpec(
        identifier="operational_add_documentation",
        category=MutationCategory.OPERATIONAL,
        mutation_class=MutationClass.ADDITIVE,
        description="Add an ADR or documentation node to an architectural element",
        risk_level="low",
        affected_node_types=("documentation",),
        expected_fitness_impact={"documentation": 0.1},
        precondition_fn=_add_doc_precondition,
        apply_fn=_add_doc_apply,
    ))

    # ------------------------------------------------------------------ #
    # PARAMETRIC: Change Service Attribute
    # ------------------------------------------------------------------ #
    def _change_attr_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None

    def _change_attr_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        node = g.get_node(target)
        if node is None:
            return g, {"error": "target not found"}
        attr = params.get("attribute", "")
        value = params.get("value")
        if attr:
            new_attrs = dict(node.attributes)
            new_attrs[attr] = value
            g._nodes[target] = GraphNode(
                id=node.id, node_type=node.node_type, label=node.label,
                attributes=new_attrs, parent_id=node.parent_id,
            )
        return g, {"attribute": attr, "new_value": value}

    registry.register(MutationOperatorSpec(
        identifier="parametric_change_attribute",
        category=MutationCategory.MAINTAINABILITY,
        mutation_class=MutationClass.PARAMETRIC,
        description="Change a node attribute value",
        risk_level="low",
        affected_node_types=(),
        expected_fitness_impact={},
        precondition_fn=_change_attr_precondition,
        apply_fn=_change_attr_apply,
    ))

    # ------------------------------------------------------------------ #
    # REVERSAL: Remove Node
    # ------------------------------------------------------------------ #
    def _remove_node_precondition(graph: TypedGraph, target: str) -> bool:
        return graph.get_node(target) is not None

    def _remove_node_apply(graph: TypedGraph, target: str, params: dict[str, Any]) -> tuple[TypedGraph, dict]:
        g = _clone(graph)
        node = g.get_node(target)
        if node is None:
            return g, {"error": "target not found"}
        children = [n.id for n in g._nodes.values() if n.parent_id == target]
        for cid in children:
            _remove_node_recursive(g, cid)
        outgoing = list(g._adjacency.get(target, []))
        incoming = list(g._reverse_adjacency.get(target, []))
        for eid in outgoing + incoming:
            if eid in g._edges:
                del g._edges[eid]
        if target in g._nodes:
            del g._nodes[target]
        if target in g._adjacency:
            del g._adjacency[target]
        if target in g._reverse_adjacency:
            del g._reverse_adjacency[target]
        return g, {"removed_id": target, "label": node.label}

    registry.register(MutationOperatorSpec(
        identifier="structural_remove_node",
        category=MutationCategory.STRUCTURAL,
        mutation_class=MutationClass.STRUCTURAL,
        description="Remove a node and its children from the graph",
        risk_level="high",
        affected_node_types=(),
        expected_fitness_impact={"complexity": -0.05},
        reversible=False,
        precondition_fn=_remove_node_precondition,
        apply_fn=_remove_node_apply,
    ))


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _clone(graph: TypedGraph) -> TypedGraph:
    """Deep-clone a TypedGraph for immutable mutation."""
    g = TypedGraph()
    for node in graph._nodes.values():
        g._nodes[node.id] = GraphNode(
            id=node.id, node_type=node.node_type, label=node.label,
            attributes=dict(node.attributes), parent_id=node.parent_id,
        )
    for eid, edge in graph._edges.items():
        g._edges[eid] = GraphEdge(
            id=edge.id, source_id=edge.source_id, target_id=edge.target_id,
            edge_type=edge.edge_type,
            attributes=EdgeAttributes(
                coupling_strength=edge.attributes.coupling_strength,
                communication_mode=edge.attributes.communication_mode,
                criticality=edge.attributes.criticality,
                latency_budget_ms=edge.attributes.latency_budget_ms,
                description=edge.attributes.description,
            ),
            metadata=dict(edge.metadata),
        )
    for nid in graph._adjacency:
        g._adjacency[nid] = list(graph._adjacency[nid])
    for nid in graph._reverse_adjacency:
        g._reverse_adjacency[nid] = list(graph._reverse_adjacency[nid])
    return g


def _remove_node_recursive(graph: TypedGraph, node_id: str) -> None:
    """Recursively remove a node and all descendants."""
    children = [n.id for n in graph._nodes.values() if n.parent_id == node_id]
    for cid in children:
        _remove_node_recursive(graph, cid)
    if node_id in graph._nodes:
        del graph._nodes[node_id]
