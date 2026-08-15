"""End-to-end tests: adapters + mutations + registry integration."""

import pytest

from constitutional_architecture.engine.adapters.isr_to_graph import ISRToGraphConverter
from constitutional_architecture.engine.adapters.graph_to_isr import GraphToISRConverter
from constitutional_architecture.engine.adapters.eir_applier import EIRApplier
from constitutional_architecture.engine.mutations.registry import get_default_registry
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System


def _seed_isr() -> ISR:
    return ISR(
        system=System(
            id="sys-e2e", name="E2EShop",
            modules=(
                Module(
                    id="mod-core", name="Core",
                    entities=(
                        Entity(id="ent-user", name="User",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                    ),
                    services=(
                        Service(id="svc-auth", name="AuthService",
                                operations=(Operation(id="op-login", name="login", operation_type=OperationType.COMMAND),)),
                    ),
                ),
            ),
        ),
    )


class TestEndToEnd:
    def test_isr_to_graph_round_trip(self):
        isr = _seed_isr()
        conv = ISRToGraphConverter()
        graph = conv.convert(isr)
        assert graph is not None

        back = GraphToISRConverter()
        result = back.convert(graph, isr)
        assert result.version == isr.version + 1
        assert len(result.system.modules) == 1

    def test_default_registry_has_all_operators(self):
        reg = get_default_registry()
        expected = {
            "structural_split_module",
            "structural_merge_services",
            "structural_extract_interface",
            "performance_add_cache",
            "behavioural_introduce_event_bus",
            "security_replace_auth_strategy",
        }
        assert set(reg.identifiers) == expected

    def test_split_module_via_registry(self):
        reg = get_default_registry()
        isr = _seed_isr()
        result = reg.apply("structural_split_module", isr, "mod:mod-core",
                           {"new_module_name": "Split", "extract_entities": ["User"]})
        assert len(result.system.modules) == 2

    def test_extract_interface_via_registry(self):
        reg = get_default_registry()
        isr = _seed_isr()
        result = reg.apply("structural_extract_interface", isr, "svc:svc-auth",
                           {"name": "AuthAPI"})
        mod = result.system.modules[0]
        iface_ids = [i.id for i in mod.interfaces]
        assert len(iface_ids) >= 1

    def test_eir_applier_returns_isr(self):
        from constitutional_architecture.isr.eir.model import EIR, Transformation
        from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass

        isr = _seed_isr()
        t = Transformation(
            id="t-1", transformation_type="structural_add_entity",
            category=MutationCategory.STRUCTURAL, mutation_class=MutationClass.ADDITIVE,
            target_node_id="mod:mod-core",
            parameters={"entity_name": "NewEntity", "entity_id": "ent-new"},
            description="Add test entity",
        )
        eir = EIR(id="eir-1", source_isr_hash=isr.content_hash, transformations=(t,))
        applier = EIRApplier()
        result = applier.apply(isr, eir)
        assert isinstance(result, ISR)
        assert result.version == isr.version + 1

    def test_mutation_operators_produce_valid_isr(self):
        reg = get_default_registry()
        isr = _seed_isr()
        ops_and_targets = {
            "structural_split_module": ("mod:mod-core", {"extract_entities": ["User"]}),
            "structural_extract_interface": ("svc:svc-auth", {"name": "AuthAPI"}),
            "performance_add_cache": ("ent:ent-user", {}),
            "behavioural_introduce_event_bus": ("svc:svc-auth", {}),
        }
        for op_id, (target, params) in ops_and_targets.items():
            result = reg.apply(op_id, isr, target, params)
            assert isinstance(result, ISR)
            assert result.version == isr.version + 1, f"{op_id} did not increment version"
