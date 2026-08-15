"""Tests for the architectural type system."""

import pytest

from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.types.type_system import ArchitecturalTypeSystem
from constitutional_architecture.isr.types.type_rules import INVALID_COMBINATIONS, VALID_COMBINATIONS


class TestArchitecturalTypeSystem:
    def setup_method(self):
        self.type_system = ArchitecturalTypeSystem()

    def test_valid_service_depends_on_service(self):
        assert self.type_system.is_valid_connection(
            NodeType.SERVICE, EdgeType.DEPENDS_ON, NodeType.SERVICE
        )

    def test_valid_module_owns_entity(self):
        assert self.type_system.is_valid_connection(
            NodeType.MODULE, EdgeType.OWNS, NodeType.ENTITY
        )

    def test_valid_service_emits_event(self):
        assert self.type_system.is_valid_connection(
            NodeType.SERVICE, EdgeType.EMITS, NodeType.EVENT
        )

    def test_valid_interface_secured_by_policy(self):
        assert self.type_system.is_valid_connection(
            NodeType.INTERFACE, EdgeType.SECURED_BY, NodeType.POLICY
        )

    def test_invalid_entity_depends_on_service(self):
        assert not self.type_system.is_valid_connection(
            NodeType.ENTITY, EdgeType.DEPENDS_ON, NodeType.SERVICE
        )

    def test_invalid_event_emits_service(self):
        assert not self.type_system.is_valid_connection(
            NodeType.EVENT, EdgeType.EMITS, NodeType.SERVICE
        )

    def test_all_documented_valid_combinations(self):
        for source, edge, target, desc in VALID_COMBINATIONS:
            assert self.type_system.is_valid_connection(source, edge, target), (
                f"Expected valid: {source} --{edge}--> {target} ({desc})"
            )

    def test_all_documented_invalid_combinations(self):
        for source, edge, target, desc in INVALID_COMBINATIONS:
            assert not self.type_system.is_valid_connection(source, edge, target), (
                f"Expected invalid: {source} --{edge}--> {target} ({desc})"
            )

    def test_check_connection_returns_violation(self):
        violation = self.type_system.check_connection(
            source_id="entity-1",
            source_type=NodeType.ENTITY,
            edge_type=EdgeType.DEPENDS_ON,
            target_id="service-1",
            target_type=NodeType.SERVICE,
        )
        assert violation is not None
        assert "Invalid edge" in violation.message

    def test_check_connection_returns_none_for_valid(self):
        violation = self.type_system.check_connection(
            source_id="service-1",
            source_type=NodeType.SERVICE,
            edge_type=EdgeType.DEPENDS_ON,
            target_id="service-2",
            target_type=NodeType.SERVICE,
        )
        assert violation is None
