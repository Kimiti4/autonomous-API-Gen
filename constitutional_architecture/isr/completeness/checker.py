"""
Completeness Checker.

Determines the completeness level of an ISR.
"""

from __future__ import annotations

from constitutional_architecture.isr.completeness.levels import CompletenessLevel
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


class CompletenessChecker:
    """Determines the completeness level of an ISR graph."""

    @staticmethod
    def check(graph: TypedGraph) -> CompletenessLevel:
        if CompletenessChecker._satisfies_l5(graph):
            return CompletenessLevel.L5_COMPLETE
        if CompletenessChecker._satisfies_l4(graph):
            return CompletenessLevel.L4_INFRASTRUCTURE
        if CompletenessChecker._satisfies_l3(graph):
            return CompletenessLevel.L3_POLICY
        if CompletenessChecker._satisfies_l2(graph):
            return CompletenessLevel.L2_BEHAVIOURAL
        if CompletenessChecker._satisfies_l1(graph):
            return CompletenessLevel.L1_STRUCTURAL
        return CompletenessLevel.L0_SKELETON

    @staticmethod
    def _satisfies_l1(graph: TypedGraph) -> bool:
        has_modules = len(graph.get_nodes_by_type(NodeType.MODULE)) > 0
        has_entities = len(graph.get_nodes_by_type(NodeType.ENTITY)) > 0
        return has_modules and has_entities

    @staticmethod
    def _satisfies_l2(graph: TypedGraph) -> bool:
        has_services = len(graph.get_nodes_by_type(NodeType.SERVICE)) > 0
        has_operations = len(graph.get_nodes_by_type(NodeType.OPERATION)) > 0
        return CompletenessChecker._satisfies_l1(graph) and has_services and has_operations

    @staticmethod
    def _satisfies_l3(graph: TypedGraph) -> bool:
        has_policies = len(graph.get_nodes_by_type(NodeType.POLICY)) > 0
        return CompletenessChecker._satisfies_l2(graph) and has_policies

    @staticmethod
    def _satisfies_l4(graph: TypedGraph) -> bool:
        has_deployment = len(graph.get_nodes_by_type(NodeType.DEPLOYMENT)) > 0
        return CompletenessChecker._satisfies_l3(graph) and has_deployment

    @staticmethod
    def _satisfies_l5(graph: TypedGraph) -> bool:
        has_docs = len(graph.get_nodes_by_type(NodeType.DOCUMENTATION)) > 0
        has_tests = len(graph.get_nodes_by_type(NodeType.TEST_STRATEGY)) > 0
        return CompletenessChecker._satisfies_l4(graph) and has_docs and has_tests

    @staticmethod
    def report(graph: TypedGraph) -> dict[str, bool]:
        return {
            "has_modules": len(graph.get_nodes_by_type(NodeType.MODULE)) > 0,
            "has_entities": len(graph.get_nodes_by_type(NodeType.ENTITY)) > 0,
            "has_services": len(graph.get_nodes_by_type(NodeType.SERVICE)) > 0,
            "has_operations": len(graph.get_nodes_by_type(NodeType.OPERATION)) > 0,
            "has_workflows": len(graph.get_nodes_by_type(NodeType.WORKFLOW)) > 0,
            "has_events": len(graph.get_nodes_by_type(NodeType.EVENT)) > 0,
            "has_policies": len(graph.get_nodes_by_type(NodeType.POLICY)) > 0,
            "has_interfaces": len(graph.get_nodes_by_type(NodeType.INTERFACE)) > 0,
            "has_deployment": len(graph.get_nodes_by_type(NodeType.DEPLOYMENT)) > 0,
            "has_documentation": len(graph.get_nodes_by_type(NodeType.DOCUMENTATION)) > 0,
            "has_test_strategy": len(graph.get_nodes_by_type(NodeType.TEST_STRATEGY)) > 0,
            "completeness_level": CompletenessChecker.check(graph).name,
        }
