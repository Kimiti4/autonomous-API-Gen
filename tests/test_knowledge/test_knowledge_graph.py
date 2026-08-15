"""Tests for the knowledge graph."""

import pytest

from constitutional_architecture.knowledge.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeEdge,
    KnowledgeCategory,
    RELATION_COMPOSES,
    RELATION_CONFLICTS_WITH,
)


class TestKnowledgeGraph:
    def test_add_and_get_node(self):
        g = KnowledgeGraph()
        node = KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN,
            label="CQRS", description="Command Query Responsibility Segregation",
        )
        g.add_node(node)
        assert g.get_node("n1") is node

    def test_add_edge(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN, label="A",
        ))
        g.add_node(KnowledgeNode(
            node_id="n2", category=KnowledgeCategory.PATTERN, label="B",
        ))
        edge = KnowledgeEdge(
            edge_id="e1", source_id="n1", target_id="n2",
            relation_type=RELATION_COMPOSES, weight=0.8,
        )
        g.add_edge(edge)
        assert len(g.get_outgoing_edges("n1")) == 1
        assert g.get_outgoing_edges("n1")[0].target_id == "n2"

    def test_get_neighbors(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN, label="A",
        ))
        g.add_node(KnowledgeNode(
            node_id="n2", category=KnowledgeCategory.PATTERN, label="B",
        ))
        g.add_edge(KnowledgeEdge(
            edge_id="e1", source_id="n1", target_id="n2",
            relation_type=RELATION_COMPOSES,
        ))
        neighbors = g.get_neighbors("n1")
        assert len(neighbors) == 1
        assert neighbors[0].label == "B"

    def test_get_nodes_by_category(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN, label="P1",
        ))
        g.add_node(KnowledgeNode(
            node_id="n2", category=KnowledgeCategory.ANTI_PATTERN, label="AP1",
        ))
        g.add_node(KnowledgeNode(
            node_id="n3", category=KnowledgeCategory.PATTERN, label="P2",
        ))
        patterns = g.get_nodes_by_category(KnowledgeCategory.PATTERN)
        assert len(patterns) == 2

    def test_find_path(self):
        g = KnowledgeGraph()
        for i in range(4):
            g.add_node(KnowledgeNode(
                node_id=f"n{i}", category=KnowledgeCategory.PATTERN,
                label=f"Node{i}",
            ))
        g.add_edge(KnowledgeEdge(edge_id="e1", source_id="n0", target_id="n1", relation_type="edge"))
        g.add_edge(KnowledgeEdge(edge_id="e2", source_id="n1", target_id="n2", relation_type="edge"))
        g.add_edge(KnowledgeEdge(edge_id="e3", source_id="n2", target_id="n3", relation_type="edge"))

        paths = g.find_path("n0", "n3", max_depth=5)
        assert len(paths) == 1
        assert len(paths[0]) == 4

    def test_query_by_text(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN,
            label="CQRS", description="Command Query Responsibility Segregation",
        ))
        g.add_node(KnowledgeNode(
            node_id="n2", category=KnowledgeCategory.PATTERN,
            label="Saga", description="Distributed transaction management",
        ))
        results = g.query(text_search="CQRS")
        assert len(results) == 1
        assert results[0].label == "CQRS"

    def test_clear(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(
            node_id="n1", category=KnowledgeCategory.PATTERN, label="A",
        ))
        assert g.node_count() == 1
        g.clear()
        assert g.node_count() == 0
