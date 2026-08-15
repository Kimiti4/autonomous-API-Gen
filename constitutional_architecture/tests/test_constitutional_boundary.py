"""Tests for Constitutional Boundary - locked parameters cannot be mutated."""

from constitutional_architecture.meta.platform_genome import (
    GenomeParameter, ParameterCategory, ParameterType, PlatformGenome,
)
from constitutional_architecture.meta.platform_mutation import PlatformMutator


class TestConstitutionalBoundary:
    def test_cannot_mutate_locked_parameter(self):
        mutator = PlatformMutator()
        genome = PlatformGenome(version=1)
        locked_param = GenomeParameter(
            id="constitution.max_depth", name="Max Depth",
            category=ParameterCategory.EVOLUTION, param_type=ParameterType.INT,
            value=10, locked=True,
        )
        genome.parameters["constitution.max_depth"] = locked_param

        p = GenomeParameter(
            id="evolution.rate", name="Mutation Rate",
            category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
            value=0.1, mutation_rate=0.1,
        )
        genome.parameters["evolution.rate"] = p

        for _ in range(20):
            new_genome, mutation = mutator.mutate_random(genome)
            assert mutation.parameter_id != "constitution.max_depth", (
                f"Locked parameter was mutated (to {mutation.new_value})"
            )
