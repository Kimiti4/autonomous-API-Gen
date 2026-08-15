import pytest

from constitutional_architecture.engine.adapters.graph_to_isr import GraphToISRConverter
from constitutional_architecture.engine.adapters.isr_to_graph import ISRToGraphConverter
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
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


class TestGraphToISRConverter:
    def setup_method(self):
        self.to_graph = ISRToGraphConverter()
        self.from_graph = GraphToISRConverter()

    def test_convert_back_to_isr(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert isinstance(result, ISR)
        assert result.version == isr.version + 1

    def test_preserves_system_name(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert result.system.name == "Test"

    def test_preserves_module_count(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert len(result.system.modules) == 1

    def test_preserves_entity_count(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert len(result.system.modules[0].entities) == 1

    def test_preserves_service_count(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert len(result.system.modules[0].services) == 1

    def test_preserves_field_count(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert len(result.system.modules[0].entities[0].fields) == 1

    def test_preserves_operation_count(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert len(result.system.modules[0].services[0].operations) == 1

    def test_provenance_linked(self):
        isr = _make_isr()
        graph = self.to_graph.convert(isr)
        result = self.from_graph.convert(graph, isr)
        assert result.provenance.parent_hash == isr.content_hash

    def test_raises_on_empty_graph(self):
        from constitutional_architecture.isr.graph.typed_graph import TypedGraph
        with pytest.raises(ValueError, match="no System node"):
            self.from_graph.convert(TypedGraph(), _make_isr())
