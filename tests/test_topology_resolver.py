import pytest

from constitutional_architecture.core.ckb.patterns import CKBPatterns
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona, QualityAttribute,
)
from constitutional_architecture.core.pipeline.topology_resolver import (
    ProductTopologyResolver,
)


@pytest.fixture
def sample_intent():
    return IntentModel(
        project_name="TestPlatform",
        problem_statement="Build a scalable platform",
        personas=[Persona(name="Admin", role="admin", primary_goals=["manage"])],
        business_archetype=BusinessArchetype.B2B_SAAS,
        core_capabilities=[Capability(name="Auth", description="Login", priority=0.9)],
        quality_priorities={attr: 0.5 for attr in QualityAttribute},
    )


class TestTopologyResolver:
    def test_resolve_architectural_profile(self, sample_intent):
        resolver = ProductTopologyResolver()
        arch_genome, quality_scores = resolver.resolve_architectural_profile(sample_intent)
        assert isinstance(arch_genome, ArchitectureGenome)
        assert isinstance(quality_scores, dict)
        assert len(quality_scores) > 0

    def test_resolve_architectural_profile_marketplace(self):
        intent = IntentModel(
            project_name="Market",
            problem_statement="Marketplace app",
            personas=[Persona(name="User", role="user", primary_goals=["shop"])],
            business_archetype=BusinessArchetype.MARKETPLACE,
            core_capabilities=[Capability(name="Catalog", description="Browse")],
            quality_priorities={attr: 0.5 for attr in QualityAttribute},
        )
        resolver = ProductTopologyResolver()
        arch_genome, _ = resolver.resolve_architectural_profile(intent)
        assert arch_genome.get_gene("api_design").value == "graphql"

    def test_resolve_full_topology(self, sample_intent):
        resolver = ProductTopologyResolver()
        result = resolver.resolve(sample_intent)
        assert result.architecture_genome is not None
        assert result.frontend_genome is not None
        assert result.archetype == BusinessArchetype.B2B_SAAS
        assert result.requirements_graph is not None

    def test_topology_includes_quality_profile(self, sample_intent):
        resolver = ProductTopologyResolver()
        result = resolver.resolve(sample_intent)
        assert len(result.quality_profile) > 0

    def test_topology_with_patterns(self, sample_intent):
        resolver = ProductTopologyResolver()
        result = resolver.resolve(sample_intent)
        assert result.pattern_modifiers_applied >= 0

    def test_topology_with_quality_priorities(self):
        intent = IntentModel(
            project_name="SecureApp",
            problem_statement="Security-first app",
            personas=[Persona(name="Admin", role="admin", primary_goals=["secure"])],
            business_archetype=BusinessArchetype.FINTECH,
            core_capabilities=[Capability(name="Payments", description="Pay")],
            quality_priorities={QualityAttribute.SECURITY: 0.9, QualityAttribute.PERFORMANCE: 0.6},
        )
        resolver = ProductTopologyResolver()
        arch_genome, _ = resolver.resolve_architectural_profile(intent)
        assert arch_genome.get_gene("security_arch").value == "zero_trust"

    def test_custom_pattern_lib(self, sample_intent):
        patterns = CKBPatterns()
        resolver = ProductTopologyResolver(pattern_lib=patterns)
        result = resolver.resolve(sample_intent)
        assert result.architecture_genome is not None

    def test_build_requirements_graph(self, sample_intent):
        resolver = ProductTopologyResolver()
        result = resolver.resolve(sample_intent)
        graph = result.requirements_graph
        assert len(graph.nodes) > 0

    def test_graph_contains_capability_nodes(self, sample_intent):
        resolver = ProductTopologyResolver()
        result = resolver.resolve(sample_intent)
        nids = [n.id for n in result.requirements_graph.nodes.values()]
        assert any("cap:" in nid for nid in nids)

    def test_archetype_genome_map(self):
        from constitutional_architecture.core.pipeline.topology_resolver import ARCHETYPE_GENOME_MAP
        assert BusinessArchetype.B2B_SAAS in ARCHETYPE_GENOME_MAP

    def test_resolve_all_archetypes(self):
        resolver = ProductTopologyResolver()
        for arch in (BusinessArchetype.B2B_SAAS, BusinessArchetype.MARKETPLACE,
                     BusinessArchetype.E_COMMERCE, BusinessArchetype.DATA_PLATFORM,
                     BusinessArchetype.FINTECH, BusinessArchetype.HEALTHCARE):
            intent = IntentModel(
                project_name=f"Test{arch.value}",
                problem_statement="Test",
                personas=[Persona(name="User", role="user", primary_goals=["test"])],
                business_archetype=arch,
                core_capabilities=[Capability(name="Core", description="Core")],
            )
            result = resolver.resolve(intent)
            assert result.architecture_genome is not None
