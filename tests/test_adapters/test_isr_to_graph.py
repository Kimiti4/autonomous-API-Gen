import pytest

from constitutional_architecture.engine.adapters.isr_to_graph import ISRToGraphConverter
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System


def _make_isr() -> ISR:
    return ISR(
        system=System(
            id="sys-1", name="Test",
            modules=(
                Module(
                    id="mod-1", name="Core",
                    entities=(
                        Entity(id="ent-1", name="User",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                    ),
                    services=(
                        Service(id="svc-1", name="UserService",
                                operations=(Operation(id="op-1", name="create", operation_type=OperationType.COMMAND),)),
                    ),
                ),
            ),
        ),
    )


class TestISRToGraphConverter:
    def setup_method(self):
        self.converter = ISRToGraphConverter()

    def test_convert_returns_graph(self):
        isr = _make_isr()
        graph = self.converter.convert(isr)
        assert graph is not None

    def test_system_node_created(self):
        graph = self.converter.convert(_make_isr())
        sys_nodes = graph.get_nodes_by_type(NodeType.SYSTEM)
        assert len(sys_nodes) == 1
        assert sys_nodes[0].label == "Test"

    def test_module_nodes_created(self):
        graph = self.converter.convert(_make_isr())
        mod_nodes = graph.get_nodes_by_type(NodeType.MODULE)
        assert len(mod_nodes) == 1
        assert mod_nodes[0].label == "Core"

    def test_entity_nodes_created(self):
        graph = self.converter.convert(_make_isr())
        ent_nodes = graph.get_nodes_by_type(NodeType.ENTITY)
        assert len(ent_nodes) == 1
        assert ent_nodes[0].label == "User"

    def test_service_nodes_created(self):
        graph = self.converter.convert(_make_isr())
        svc_nodes = graph.get_nodes_by_type(NodeType.SERVICE)
        assert len(svc_nodes) == 1
        assert svc_nodes[0].label == "UserService"

    def test_field_nodes_created(self):
        graph = self.converter.convert(_make_isr())
        fld_nodes = graph.get_nodes_by_type(NodeType.FIELD)
        assert len(fld_nodes) == 1
        assert fld_nodes[0].label == "id"

    def test_operation_nodes_created(self):
        graph = self.converter.convert(_make_isr())
        op_nodes = graph.get_nodes_by_type(NodeType.OPERATION)
        assert len(op_nodes) == 1
        assert op_nodes[0].label == "create"

    def test_round_trip_preserves_structure(self):
        isr = _make_isr()
        graph = self.converter.convert(isr)
        sys_nodes = graph.get_nodes_by_type(NodeType.SYSTEM)
        mod_nodes = graph.get_nodes_by_type(NodeType.MODULE)
        assert len(sys_nodes) == 1
        assert len(mod_nodes) == 1
        assert mod_nodes[0].parent_id == sys_nodes[0].id
