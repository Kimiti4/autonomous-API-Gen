import pytest

from constitutional_architecture.engine.mutations.split_module import SplitModuleMutation
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.system import System


@pytest.fixture
def multi_entity_isr() -> ISR:
    return ISR(
        system=System(
            id="sys-test", name="TestSystem",
            modules=(
                Module(
                    id="mod-main", name="Main",
                    entities=(
                        Entity(id="ent-a", name="Alpha",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                        Entity(id="ent-b", name="Beta",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                        Entity(id="ent-c", name="Gamma",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                    ),
                ),
            ),
        ),
    )


class TestSplitModuleMutation:
    def test_identifier_and_description(self):
        m = SplitModuleMutation()
        assert m.identifier == "structural_split_module"
        assert isinstance(m.description, str)
        assert len(m.description) > 0

    def test_split_creates_new_module(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:mod-main", {"new_module_name": "Split", "extract_entities": ["Alpha"]})
        assert len(result.system.modules) == 2

    def test_original_module_kept_remaining_entities(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:mod-main", {"new_module_name": "Split", "extract_entities": ["Alpha"]})
        original = next(mod for mod in result.system.modules if mod.id == "mod-main")
        assert any(e.name == "Beta" for e in original.entities)
        assert any(e.name == "Gamma" for e in original.entities)

    def test_new_module_has_moved_entities(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:mod-main", {"new_module_name": "Split", "extract_entities": ["Alpha"]})
        new_mod = next(mod for mod in result.system.modules if mod.name == "Split")
        assert any(e.name == "Alpha" for e in new_mod.entities)

    def test_no_change_when_target_missing(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:nonexistent")
        assert len(result.system.modules) == 1

    def test_version_incremented(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:mod-main", {"extract_entities": ["Alpha"]})
        assert result.version == multi_entity_isr.version + 1

    def test_provenance_recorded(self, multi_entity_isr):
        m = SplitModuleMutation()
        result = m.apply(multi_entity_isr, "mod:mod-main", {"extract_entities": ["Alpha"]})
        assert result.provenance.parent_hash == multi_entity_isr.content_hash
        assert "split" in result.provenance.mutation_description.lower()
