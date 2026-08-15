"""Tests for PlatformGenome."""

from constitutional_architecture.meta.platform_genome import (
    GenomeParameter,
    ParameterCategory,
    ParameterType,
    PlatformGenome,
    create_default_genome,
)


class TestGenomeParameter:
    def test_creation(self):
        p = GenomeParameter("test.param", "Test Param", ParameterCategory.COMPILER,
                            ParameterType.INT, 5, mutation_rate=0.1)
        assert p.id == "test.param"
        assert p.name == "Test Param"
        assert p.value == 5
        assert p.mutation_rate == 0.1
        assert p.category == ParameterCategory.COMPILER
        assert p.locked is False

    def test_lock(self):
        p = GenomeParameter("test.param", "Test Param", ParameterCategory.COMPILER,
                            ParameterType.INT, 5, mutation_rate=0.1, locked=True)
        assert p.locked is True


class TestPlatformGenome:
    def test_creation(self):
        g = PlatformGenome(version=1)
        assert g.version == 1
        assert g.parent_hash is None
        assert g.genome_id is not None

    def test_with_parameter(self):
        g = PlatformGenome(version=1)
        p = GenomeParameter("t1", "t1", ParameterCategory.EVOLUTION,
                            ParameterType.INT, 1, mutation_rate=0.1)
        g.parameters["t1"] = p
        assert g.get_parameter("t1") == p

    def test_get_mutable_parameters(self):
        g = PlatformGenome(version=1)
        p1 = GenomeParameter("t1", "t1", ParameterCategory.EVOLUTION,
                             ParameterType.FLOAT, 0.5, mutation_rate=0.1)
        p2 = GenomeParameter("t2", "t2", ParameterCategory.COMPILER,
                             ParameterType.INT, 2, mutation_rate=0.1, locked=True)
        g.parameters["t1"] = p1
        g.parameters["t2"] = p2
        mutable = g.get_mutable_parameters()
        assert len(mutable) == 1
        assert mutable[0].id == "t1"

    def test_content_hash_property(self):
        g = PlatformGenome(version=1)
        assert g.content_hash is not None


class TestCreateDefaultGenome:
    def test_contains_expected_categories(self):
        g = create_default_genome()
        assert g.version == 1
        assert len(g.get_mutable_parameters()) > 0
        params = {p.name for p in g.parameters.values()}
        assert "Mutation Rate" in params
        assert "Max Concurrent Evolutions" in params
        assert "Max Verification Level" in params

    def test_content_hash_stable(self):
        g1 = create_default_genome()
        g2 = create_default_genome()
        assert g1.content_hash == g2.content_hash
