"""Tests for Platform Mutation strategies."""

from constitutional_architecture.meta.platform_genome import (
    GenomeParameter,
    ParameterCategory,
    ParameterType,
    PlatformGenome,
    create_default_genome,
)
from constitutional_architecture.meta.platform_mutation import PlatformMutator


class TestPlatformMutator:
    def test_mutate_random_returns_new_genome(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        new_genome, mutation = mutator.mutate_random(genome)
        assert new_genome.version == genome.version + 1
        assert new_genome.parent_hash == genome.content_hash
        assert mutation is not None

    def test_mutate_guided_returns_new_genome(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        gradient = {"evo.mutation_rate": 0.5}
        new_genome, mutation = mutator.mutate_guided(genome, gradient)
        assert new_genome.version == genome.version + 1
        assert mutation is not None

    def test_mutate_adaptive_returns_new_genome(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        new_genome, mutation = mutator.mutate_adaptive(genome)
        assert new_genome.version == genome.version + 1
        assert mutation is not None

    def test_all_strategies_produce_different_genomes(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        genomes = set()
        for strategy in ["random", "guided", "adaptive"]:
            if strategy == "guided":
                ng, _ = mutator.mutate_guided(genome, {"evo.mutation_rate": 0.5})
            elif strategy == "adaptive":
                ng, _ = mutator.mutate_adaptive(genome)
            else:
                ng, _ = mutator.mutate_random(genome)
            genomes.add(ng.content_hash)
        assert len(genomes) == 3

    def test_mutation_changes_parameter_value(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        new_genome, mutation = mutator.mutate_random(genome)
        old_param = genome.get_parameter(mutation.parameter_id)
        new_param = new_genome.get_parameter(mutation.parameter_id)
        assert old_param.value != new_param.value

    def test_mutation_reasoning_not_empty(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        _, mutation = mutator.mutate_random(genome)
        assert mutation.reasoning != ""

    def test_success_rates_keyed_by_parameter_id(self):
        mutator = PlatformMutator()
        genome = create_default_genome()
        _, mutation = mutator.mutate_random(genome)
        mutator.record_outcome(mutation.id, success=True)
        rates = mutator.success_rates
        assert mutation.parameter_id in rates
        assert rates[mutation.parameter_id] > 0.5
