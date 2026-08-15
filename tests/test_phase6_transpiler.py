import pytest

from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, DataDomain, IntentModel, Persona,
    QualityAttribute,
)
from constitutional_architecture.core.models.isr import NodeType
from constitutional_architecture.core.pipeline.isr_transpiler import ISRTranspiler
from constitutional_architecture.validators.isr_graph_validator import (
    ISRGraphViolation, ISRGraphValidator,
)


@pytest.fixture
def transpiler() -> ISRTranspiler:
    return ISRTranspiler()


@pytest.fixture
def validator() -> ISRGraphValidator:
    return ISRGraphValidator()


@pytest.fixture
def sample_intent() -> IntentModel:
    return IntentModel(
        project_name="TestApp",
        problem_statement="Test",
        personas=[Persona(name="Admin", role="admin", primary_goals=["manage"])],
        business_archetype=BusinessArchetype.B2B_SAAS,
        core_capabilities=[Capability(name="Billing", description="Subscription management")],
        data_domains=[DataDomain(name="Finance", entities=["Invoice", "Payment"])],
    )


@pytest.fixture
def default_genome() -> ArchitectureGenome:
    return ArchitectureGenome()


class TestISRTranspiler:
    def test_returns_universal_isr(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert isr.intent_hash
        assert isr.genome_hash
        assert len(isr.nodes) > 0

    def test_domain_and_entities_materialized(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert any(n.type == NodeType.DOMAIN for n in isr.nodes.values())
        assert any(n.type == NodeType.DATA_ENTITY for n in isr.nodes.values())

    def test_services_materialized(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert any(n.type == NodeType.COMPONENT for n in isr.nodes.values())

    def test_security_policy_materialized(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert any(n.type == NodeType.SECURITY_POLICY for n in isr.nodes.values())

    def test_security_edges_cover_all_services(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        secured = {e.target_id for e in isr.edges if e.type.value == "secures"}
        for nid, n in isr.nodes.items():
            if n.type in (NodeType.SERVICE, NodeType.COMPONENT, NodeType.API_ENDPOINT):
                assert nid in secured

    def test_infrastructure_materialized(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert any(n.type == NodeType.INFRA_REQUIREMENT for n in isr.nodes.values())

    def test_frontend_view_materialized(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert any(n.type == NodeType.FRONTEND_VIEW for n in isr.nodes.values())

    def test_microservices_produce_service_nodes(self, transpiler, sample_intent):
        g = ArchitectureGenome()
        g.set_gene("app_arch", "microservices")
        isr = transpiler.transpile(sample_intent, g)
        assert any(n.type == NodeType.SERVICE for n in isr.nodes.values())

    def test_domain_owns_entities(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        owns = [(e.source_id, e.target_id) for e in isr.edges if e.type.value == "owns"]
        assert len(owns) > 0

    def test_passes_constitutional_gates(self, transpiler, validator, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        validator.validate(isr)

    def test_intent_hash_is_deterministic(self, transpiler, sample_intent, default_genome):
        isr1 = transpiler.transpile(sample_intent, default_genome)
        isr2 = transpiler.transpile(sample_intent, default_genome)
        assert isr1.intent_hash == isr2.intent_hash

    def test_no_forbidden_lexicon_in_isr(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        validator = ISRGraphValidator(forbidden_lexicon={"react", "postgres", "aws"})
        validator.validate(isr)

    def test_api_endpoints_have_protocol(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        for n in isr.nodes.values():
            if n.type == NodeType.API_ENDPOINT:
                assert "protocol" in n.semantic_attributes


class TestISRGraphValidator:
    def test_valid_isr_passes(self, transpiler, validator, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        validator.validate(isr)

    def test_missing_security_raises(self, transpiler, validator, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        isr.edges = [e for e in isr.edges if e.type.value != "secures"]
        with pytest.raises(ISRGraphViolation, match="Security by Design"):
            validator.validate(isr)

    def test_orphaned_entity_raises(self, transpiler, validator, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        isr.edges = [e for e in isr.edges if e.type.value != "owns"]
        with pytest.raises(ISRGraphViolation, match="Domain-Driven Design"):
            validator.validate(isr)

    def test_cycle_detection(self, transpiler, sample_intent, default_genome):
        isr = transpiler.transpile(sample_intent, default_genome)
        assert not isr.has_cycle()
