"""Tests for ISR completeness checking."""

import pytest

from constitutional_architecture.isr.completeness.checker import CompletenessChecker
from constitutional_architecture.isr.completeness.levels import CompletenessLevel
from constitutional_architecture.isr.graph.typed_graph import GraphNode, TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


class TestCompletenessChecker:
    def test_empty_graph_is_l0(self):
        graph = TypedGraph()
        graph.add_node(GraphNode(id="sys", node_type=NodeType.SYSTEM, label="Test"))
        assert CompletenessChecker.check(graph) == CompletenessLevel.L0_SKELETON

    def test_modules_and_entities_is_l1(self):
        graph = TypedGraph()
        graph.add_node(GraphNode(id="sys", node_type=NodeType.SYSTEM, label="Test"))
        graph.add_node(GraphNode(id="mod", node_type=NodeType.MODULE, label="Auth"))
        graph.add_node(GraphNode(id="ent", node_type=NodeType.ENTITY, label="User"))
        assert CompletenessChecker.check(graph) == CompletenessLevel.L1_STRUCTURAL

    def test_with_services_is_l2(self):
        graph = TypedGraph()
        graph.add_node(GraphNode(id="sys", node_type=NodeType.SYSTEM, label="Test"))
        graph.add_node(GraphNode(id="mod", node_type=NodeType.MODULE, label="Auth"))
        graph.add_node(GraphNode(id="ent", node_type=NodeType.ENTITY, label="User"))
        graph.add_node(GraphNode(id="svc", node_type=NodeType.SERVICE, label="AuthService"))
        graph.add_node(GraphNode(id="op", node_type=NodeType.OPERATION, label="login"))
        assert CompletenessChecker.check(graph) == CompletenessLevel.L2_BEHAVIOURAL

    def test_l1_allows_evolution(self):
        assert CompletenessLevel.L1_STRUCTURAL.allows_evolution

    def test_l0_does_not_allow_evolution(self):
        assert not CompletenessLevel.L0_SKELETON.allows_evolution

    def test_l2_allows_compilation(self):
        assert CompletenessLevel.L2_BEHAVIOURAL.allows_compilation

    def test_l1_does_not_allow_compilation(self):
        assert not CompletenessLevel.L1_STRUCTURAL.allows_compilation
