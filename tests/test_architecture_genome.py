import pytest

from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome, CategoricalGene,
    ContinuousGene, DataArchitecture, DeploymentTopology,
    IntegrationArchitecture, ObservabilityStrategy, SecurityArchitecture,
    StateManagement,
)
from constitutional_architecture.core.ckb.patterns import CKBPatterns
from constitutional_architecture.core.models.intent import BusinessArchetype, QualityAttribute


class TestArchitectureGenome:
    def test_default_genome_has_all_genes(self):
        g = ArchitectureGenome()
        assert len(g.categorical_genes) == 14
        assert len(g.continuous_genes) == 7
        assert g.get_gene("app_arch") == ApplicationArchitecture.MODULAR_MONOLITH

    def test_set_and_get_gene(self):
        g = ArchitectureGenome()
        g.set_gene("app_arch", ApplicationArchitecture.MICROSERVICES)
        assert g.get_gene("app_arch") == ApplicationArchitecture.MICROSERVICES

    def test_set_continuous_gene(self):
        g = ArchitectureGenome()
        g.set_gene("consistency_level", 0.5)
        assert g.get_gene("consistency_level") == 0.5

    def test_clone_is_independent(self):
        g = ArchitectureGenome()
        g.set_gene("app_arch", ApplicationArchitecture.MICROSERVICES)
        c = g.clone()
        c.set_gene("app_arch", ApplicationArchitecture.MONOLITHIC)
        assert g.get_gene("app_arch") == ApplicationArchitecture.MICROSERVICES
        assert c.get_gene("app_arch") == ApplicationArchitecture.MONOLITHIC

    def test_mutate_changes_some_genes(self):
        g = ArchitectureGenome()
        old = g.serialize()
        mutations = g.mutate(rate=0.5)
        new = g.serialize()
        total_changes = sum(
            1 for k in old["categorical"]
            if old["categorical"][k]["value"] != new["categorical"][k]["value"]
        )
        total_changes += sum(
            1 for k in old["continuous"]
            if old["continuous"][k]["value"] != new["continuous"][k]["value"]
        )
        assert mutations == total_changes
        assert mutations >= 0

    def test_serialize_returns_all_genes(self):
        g = ArchitectureGenome()
        s = g.serialize()
        assert "categorical" in s
        assert "continuous" in s
        assert len(s["categorical"]) == 14
        assert len(s["continuous"]) == 7

    def test_get_invalid_gene_returns_none(self):
        g = ArchitectureGenome()
        assert g.get_gene("nonexistent") is None

    def test_set_invalid_gene_does_nothing(self):
        g = ArchitectureGenome()
        g.set_gene("nonexistent", "value")
        assert g.get_gene("nonexistent") is None

    def test_categorical_gene_allowed_values(self):
        cat = CategoricalGene("test", "Test", ApplicationArchitecture.MONOLITHIC,
                              tuple(ApplicationArchitecture))
        assert ApplicationArchitecture.MICROSERVICES in cat.allowed_values

    def test_continuous_gene_bounds(self):
        con = ContinuousGene("test", "Test", 0.5, 0.0, 1.0)
        con.mutate(rate=0.0)
        assert con.value == 0.5


class TestCKBPatterns:
    def test_get_base_genome_b2b(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.B2B_SAAS)
        assert isinstance(g, ArchitectureGenome)

    def test_get_base_genome_marketplace(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.MARKETPLACE)
        assert g.get_gene("app_arch") == ApplicationArchitecture.EVENT_DRIVEN

    def test_get_base_genome_ecommerce(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.E_COMMERCE)
        assert g.get_gene("api_design") == APIDesign.REST

    def test_get_base_genome_data_platform(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.DATA_PLATFORM)
        assert g.get_gene("data_arch") == DataArchitecture.DATA_LAKE

    def test_get_base_genome_fintech(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.FINTECH)
        assert g.get_gene("security_arch") == SecurityArchitecture.ZERO_TRUST

    def test_get_base_genome_healthcare(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.HEALTHCARE)
        assert g.get_gene("security_arch") == SecurityArchitecture.ZERO_TRUST

    def test_get_base_genome_iot(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.IOT_SYSTEM)
        assert g.get_gene("deployment_topology") == DeploymentTopology.EDGE

    def test_get_base_genome_unknown_falls_back(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome("unknown")
        assert g is not None

    def test_apply_quality_modifiers_scalability(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.B2B_SAAS)
        mods = ckb.apply_quality_modifiers(g, {QualityAttribute.SCALABILITY: 0.8})
        assert mods > 0
        assert g.get_gene("app_arch") == ApplicationArchitecture.MICROSERVICES

    def test_apply_quality_modifiers_security(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.B2B_SAAS)
        ckb.apply_quality_modifiers(g, {QualityAttribute.SECURITY: 0.9})
        assert g.get_gene("security_arch") == SecurityArchitecture.ZERO_TRUST

    def test_apply_quality_modifiers_low_priority_no_change(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.B2B_SAAS)
        old = g.get_gene("app_arch")
        ckb.apply_quality_modifiers(g, {QualityAttribute.SCALABILITY: 0.3})
        assert g.get_gene("app_arch") == old

    def test_get_quality_profile(self):
        ckb = CKBPatterns()
        profile = ckb.get_quality_profile(BusinessArchetype.B2B_SAAS)
        assert "maintainability" in profile
        assert profile["security"] == 0.8

    def test_get_conflicting_patterns(self):
        ckb = CKBPatterns()
        conflicts = ckb.get_conflicting_patterns(BusinessArchetype.MARKETPLACE)
        assert "monolithic" in conflicts

    def test_resolve_archetype_profile(self):
        ckb = CKBPatterns()
        profile = ckb.resolve_archetype_profile(BusinessArchetype.B2B_SAAS)
        assert profile.archetype == BusinessArchetype.B2B_SAAS
        assert isinstance(profile.genome, ArchitectureGenome)

    def test_all_archetypes_have_profiles(self):
        ckb = CKBPatterns()
        for arch in BusinessArchetype:
            g = ckb.get_base_genome(arch)
            assert isinstance(g, ArchitectureGenome)

    def test_quality_modifiers_all_attributes(self):
        ckb = CKBPatterns()
        g = ckb.get_base_genome(BusinessArchetype.B2B_SAAS)
        for qa in QualityAttribute:
            ckb.apply_quality_modifiers(g, {qa: 0.9})
        assert g.get_gene("app_arch") is not None

    def test_continuous_gene_mutation(self):
        g = ArchitectureGenome()
        old_val = g.get_gene("consistency_level")
        g.continuous_genes["consistency_level"].mutate(1.0)
        assert g.get_gene("consistency_level") != old_val

    def test_categorical_gene_mutation(self):
        g = ArchitectureGenome()
        old_val = g.get_gene("app_arch")
        g.categorical_genes["app_arch"].mutate(1.0)
        assert g.get_gene("app_arch") != old_val
