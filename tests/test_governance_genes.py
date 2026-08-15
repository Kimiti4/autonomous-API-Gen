"""Governance Chromosome Family — gene value-space, mutation, crossover,
expression, and ISR projection verification."""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from constitutional_architecture.governance.governance_genes import (
    MAX_POLICY_RULES,
    MAX_QUORUM,
    MAX_STAGES,
    MIN_POLICY_RULES,
    MIN_QUORUM,
    MIN_STAGES,
    AuditMandateGene,
    GovernanceChromosome,
    QuorumGene,
    VotingRuleGene,
)
from constitutional_architecture.governance.schemas import (
    ExceptionSeverity,
    GovernanceDesignISR,
    VersioningStrategyKind,
    VotingRuleKind,
)


def assert_valid_chromosome(chromosome: GovernanceChromosome) -> None:
    assert chromosome.voting_rule.value in set(VotingRuleKind)
    assert MIN_QUORUM <= chromosome.quorum.value <= MAX_QUORUM
    assert MIN_STAGES <= chromosome.approval_stages.value <= MAX_STAGES
    assert (
        MIN_POLICY_RULES <= chromosome.policy_coverage.rule_count <= MAX_POLICY_RULES
    )
    assert chromosome.exception_policy.max_severity in set(ExceptionSeverity)
    assert chromosome.versioning_strategy.value in set(VersioningStrategyKind)


def test_sampled_chromosome_is_within_value_space():
    chromosome = GovernanceChromosome.sample(random.Random(7))
    assert_valid_chromosome(chromosome)


@given(
    seed=st.integers(min_value=0, max_value=10_000),
    steps=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=30)
def test_mutation_stays_within_value_space(seed, steps):
    rng = random.Random(seed)
    chromosome = GovernanceChromosome.sample(rng)
    for _ in range(steps):
        chromosome = chromosome.mutate(rng, mutation_rate=1.0)
        assert_valid_chromosome(chromosome)


def test_mutation_is_deterministic_given_seed():
    base = GovernanceChromosome.sample(random.Random(1))
    a = base.mutate(random.Random(42), mutation_rate=1.0)
    b = base.mutate(random.Random(42), mutation_rate=1.0)
    assert a == b


def test_crossover_genes_come_from_parents():
    parent_a = GovernanceChromosome.sample(random.Random(1))
    parent_b = GovernanceChromosome.sample(random.Random(2))
    child = parent_a.crossover(parent_b, random.Random(3))
    assert child.voting_rule in (parent_a.voting_rule, parent_b.voting_rule)
    assert child.quorum in (parent_a.quorum, parent_b.quorum)
    assert child.versioning_strategy in (
        parent_a.versioning_strategy,
        parent_b.versioning_strategy,
    )
    assert_valid_chromosome(child)


def test_voting_rule_gene_mutates_to_different_value():
    gene = VotingRuleGene(VotingRuleKind.SIMPLE_MAJORITY)
    mutated = gene.mutate(random.Random(5))
    assert mutated.value is not VotingRuleKind.SIMPLE_MAJORITY


def test_quorum_gene_mutation_stays_bounded():
    rng = random.Random(9)
    gene = QuorumGene(MIN_QUORUM)
    for _ in range(50):
        gene = gene.mutate(rng)
        assert MIN_QUORUM <= gene.value <= MAX_QUORUM


def test_bool_mandate_gene_flips():
    gene = AuditMandateGene(True)
    assert gene.mutate(random.Random(0)).value is False


def test_express_produces_valid_governance_design():
    chromosome = GovernanceChromosome.sample(random.Random(11))
    design = chromosome.express()
    # Round-trips through the ISR schema cleanly.
    assert GovernanceDesignISR.model_validate(design.model_dump()) == design
    assert design.voting_rule == chromosome.voting_rule.value
    assert design.quorum == chromosome.quorum.value


def test_project_approval_workflow_reflects_genes():
    chromosome = GovernanceChromosome.sample(random.Random(13))
    workflow = chromosome.project_approval_workflow("wf-gov")
    assert workflow.workflow_id == "wf-gov"
    assert workflow.quorum == chromosome.quorum.value
    assert len(workflow.stages) == chromosome.approval_stages.value
    assert all(stage.rule == chromosome.voting_rule.value for stage in workflow.stages)
