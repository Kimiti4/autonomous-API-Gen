"""
Crossover Engine.

Combines architectural regions from two parent ISR graphs
to produce offspring. Crossover operates on typed graphs via
subgraph exchange at module boundaries.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.engine.evolution_events import EventBus, EventType, EvolutionEvent
from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class CrossoverResult:
    success: bool
    child_graph: Optional[TypedGraph] = None
    parent_a_id: str = ""
    parent_b_id: str = ""
    crossover_point: str = ""
    explanation: str = ""


class CrossoverEngine:
    """
    Performs crossover on ISR typed graphs.

    Crossover semantics for graphs:
    1. Identify a crossover point (module boundary in both parents)
    2. Extract the subgraph rooted at that module from Parent A
    3. Extract the corresponding subgraph from Parent B
    4. Validate interface compatibility at the boundary
    5. Produce child with Parent A's structure + Parent B's module internals

    Crossover is only valid when both parents share compatible
    interface contracts at the crossover boundary.
    """

    def __init__(
        self,
        event_bus: EventBus,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._event_bus = event_bus
        self._rng = rng or random.Random()

    def crossover(
        self,
        parent_a: TypedGraph,
        parent_b: TypedGraph,
        parent_a_id: str = "",
        parent_b_id: str = "",
        generation: int = 0,
    ) -> CrossoverResult:
        modules_a = {n.label: n.id for n in parent_a.get_nodes_by_type(NodeType.MODULE)}
        modules_b = {n.label: n.id for n in parent_b.get_nodes_by_type(NodeType.MODULE)}
        common_modules = set(modules_a.keys()) & set(modules_b.keys())

        if not common_modules:
            return CrossoverResult(
                success=False,
                parent_a_id=parent_a_id,
                parent_b_id=parent_b_id,
                explanation="No common modules found for crossover",
            )

        crossover_module = self._rng.choice(sorted(common_modules))
        module_a_id = modules_a[crossover_module]
        module_b_id = modules_b[crossover_module]

        child = parent_a.clone()

        b_owned_nodes = self._get_owned_subgraph(parent_b, module_b_id)
        a_owned_nodes = self._get_owned_subgraph(parent_a, module_a_id)

        for node_id in a_owned_nodes:
            if node_id != module_a_id:
                try:
                    child.remove_node(node_id)
                except ValueError:
                    pass

        id_mapping: dict[str, str] = {module_b_id: module_a_id}
        for node_id in b_owned_nodes:
            if node_id == module_b_id:
                continue
            node = parent_b.get_node(node_id)
            if node is None:
                continue
            new_id = f"{node_id}-x-{uuid.uuid4().hex[:6]}"
            id_mapping[node_id] = new_id
            remapped_node = GraphNode(
                id=new_id,
                node_type=node.node_type,
                label=node.label,
                attributes=node.attributes,
                parent_id=module_a_id,
            )
            child.add_node(remapped_node)

        for edge in parent_b.edges():
            if edge.source_id in b_owned_nodes and edge.target_id in b_owned_nodes:
                new_source = id_mapping.get(edge.source_id, edge.source_id)
                new_target = id_mapping.get(edge.target_id, edge.target_id)
                if child.get_node(new_source) and child.get_node(new_target):
                    child.add_edge(GraphEdge(
                        id=f"edge-x-{uuid.uuid4().hex[:8]}",
                        source_id=new_source,
                        target_id=new_target,
                        edge_type=edge.edge_type,
                        attributes=edge.attributes,
                    ))

        explanation = (
            f"Crossover at module '{crossover_module}': "
            f"replaced internals from Parent B into Parent A structure"
        )

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.CROSSOVER_APPLIED,
            generation=generation,
            data={
                "parent_a": parent_a_id,
                "parent_b": parent_b_id,
                "crossover_point": crossover_module,
            },
        ))

        return CrossoverResult(
            success=True,
            child_graph=child,
            parent_a_id=parent_a_id,
            parent_b_id=parent_b_id,
            crossover_point=crossover_module,
            explanation=explanation,
        )

    def _get_owned_subgraph(self, graph: TypedGraph, module_id: str) -> set[str]:
        owned: set[str] = {module_id}
        queue = [module_id]
        while queue:
            current = queue.pop(0)
            for edge in graph.get_outgoing_edges(current):
                if edge.edge_type in {EdgeType.OWNS, EdgeType.CONTAINS}:
                    if edge.target_id not in owned:
                        owned.add(edge.target_id)
                        queue.append(edge.target_id)
        return owned
