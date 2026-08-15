"""Tests for the ISR validation engine."""

import pytest

from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeAttributes, EdgeType
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.validation.validator import Validator


def _create_valid_graph() -> TypedGraph:
    graph = TypedGraph()
    graph.add_node(GraphNode(id="sys", node_type=NodeType.SYSTEM, label="Shop"))
    graph.add_node(GraphNode(id="mod-auth", node_type=NodeType.MODULE, label="Auth", parent_id="sys"))
    graph.add_node(GraphNode(id="mod-orders", node_type=NodeType.MODULE, label="Orders", parent_id="sys"))
    graph.add_node(GraphNode(id="entity-user", node_type=NodeType.ENTITY, label="User", parent_id="mod-auth"))
    graph.add_node(GraphNode(id="svc-auth", node_type=NodeType.SERVICE, label="AuthService", parent_id="mod-auth"))
    graph.add_node(GraphNode(id="svc-orders", node_type=NodeType.SERVICE, label="OrderService", parent_id="mod-orders"))

    graph.add_edge(GraphEdge(id="e1", source_id="sys", target_id="mod-auth", edge_type=EdgeType.OWNS))
    graph.add_edge(GraphEdge(id="e2", source_id="sys", target_id="mod-orders", edge_type=EdgeType.OWNS))
    graph.add_edge(GraphEdge(id="e3", source_id="mod-auth", target_id="entity-user", edge_type=EdgeType.OWNS))
    graph.add_edge(GraphEdge(id="e4", source_id="mod-auth", target_id="svc-auth", edge_type=EdgeType.OWNS))
    graph.add_edge(GraphEdge(id="e5", source_id="mod-orders", target_id="svc-orders", edge_type=EdgeType.OWNS))
    graph.add_edge(GraphEdge(id="e6", source_id="svc-orders", target_id="svc-auth", edge_type=EdgeType.DEPENDS_ON))

    return graph


def _create_cyclic_graph() -> TypedGraph:
    graph = _create_valid_graph()
    graph.add_edge(GraphEdge(id="e7", source_id="svc-auth", target_id="svc-orders", edge_type=EdgeType.DEPENDS_ON))
    return graph


class TestValidator:
    def test_valid_graph_passes(self):
        graph = _create_valid_graph()
        validator = Validator()
        result = validator.validate(graph)
        assert result.is_valid

    def test_cyclic_dependency_fails(self):
        graph = _create_cyclic_graph()
        validator = Validator()
        result = validator.validate(graph)
        assert not result.is_valid
        invariant_names = [r.invariant_name for r in result.invariant_results if not r.passed]
        assert "dependency_acyclicity" in invariant_names

    def test_invalid_edge_type_fails(self):
        graph = TypedGraph()
        graph.add_node(GraphNode(id="entity-1", node_type=NodeType.ENTITY, label="User"))
        graph.add_node(GraphNode(id="svc-1", node_type=NodeType.SERVICE, label="AuthService"))
        graph.add_edge(GraphEdge(id="e1", source_id="entity-1", target_id="svc-1", edge_type=EdgeType.DEPENDS_ON))

        validator = Validator()
        result = validator.validate(graph)
        assert not result.is_valid
        assert result.type_check.error_count > 0
