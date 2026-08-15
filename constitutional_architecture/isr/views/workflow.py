"""
Workflow View.

Projects the ISR graph into a business process view
consumed by the Domain Expert agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class WorkflowView:
    """The workflow view of the ISR."""

    workflows: tuple[dict, ...] = ()
    events: tuple[dict, ...] = ()
    total_states: int = 0
    total_transitions: int = 0


class WorkflowViewBuilder:
    """Builds the workflow view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> WorkflowView:
        workflows = tuple(
            {"id": w.id, "label": w.label, "attributes": w.attributes}
            for w in graph.get_nodes_by_type(NodeType.WORKFLOW)
        )
        events = tuple(
            {"id": e.id, "label": e.label, "attributes": e.attributes}
            for e in graph.get_nodes_by_type(NodeType.EVENT)
        )
        states = graph.get_nodes_by_type(NodeType.STATE)
        transitions = graph.get_nodes_by_type(NodeType.TRANSITION)

        return WorkflowView(
            workflows=workflows,
            events=events,
            total_states=len(states),
            total_transitions=len(transitions),
        )
