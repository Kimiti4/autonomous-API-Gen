"""Governance Chromosome Family — the variation half of the governance
evolutionary loop.

Defines the Governance chromosome family as independent, genome-agnostic genes
that express into governance ISR (``GovernanceDesignISR``). Until these genes
differ across candidates, the merged governance vector is Pareto-neutral
(telemetry only); these genes supply the variation that option-(d) fitness
selects among.

Constitutional alignment:
  * Genes encode governance ARCHITECTURAL DECISIONS, not implementation detail.
  * Expression flows through the ISR: genes -> GovernanceDesignISR. The
    evolution engine consumes that ISR, never gene internals.
  * Genes evolve independently (own value space, mutation, crossover).
  * Deliberately genome-agnostic: no subclassing of or registration into any
    specific genome implementation. The genome-integration seam is an explicit
    ADAPTATION POINT (bottom) so no contract is fabricated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from uuid import uuid4

from constitutional_architecture.governance.schemas import (
    ApprovalStageISR,
    ApprovalWorkflowISR,
    ExceptionSeverity,
    GovernanceDesignISR,
    VersioningStrategyKind,
    VotingRuleKind,
)

MIN_QUORUM = 1
MAX_QUORUM = 5
MIN_STAGES = 1
MAX_STAGES = 4
MIN_POLICY_RULES = 0
MAX_POLICY_RULES = 20


def _mutate_enum(current, values, rng: random.Random):
    alternatives = [v for v in values if v is not current]
    if not alternatives:
        return current
    return rng.choice(alternatives)


def _step_bounded_int(value: int, lo: int, hi: int, rng: random.Random) -> int:
    """Random-walk one step within [lo, hi]; reflects at the bounds."""
    if lo == hi:
        return value
    candidate = value + rng.choice((-1, 1))
    if candidate < lo:
        candidate = value + 1
    elif candidate > hi:
        candidate = value - 1
    return max(lo, min(hi, candidate))


@dataclass(frozen=True)
class VotingRuleGene:
    value: VotingRuleKind

    @classmethod
    def sample(cls, rng: random.Random) -> "VotingRuleGene":
        return cls(rng.choice(list(VotingRuleKind)))

    def mutate(self, rng: random.Random) -> "VotingRuleGene":
        return VotingRuleGene(_mutate_enum(self.value, list(VotingRuleKind), rng))


@dataclass(frozen=True)
class QuorumGene:
    value: int

    @classmethod
    def sample(cls, rng: random.Random) -> "QuorumGene":
        return cls(rng.randint(MIN_QUORUM, MAX_QUORUM))

    def mutate(self, rng: random.Random) -> "QuorumGene":
        return QuorumGene(_step_bounded_int(self.value, MIN_QUORUM, MAX_QUORUM, rng))


@dataclass(frozen=True)
class ApprovalStagesGene:
    value: int

    @classmethod
    def sample(cls, rng: random.Random) -> "ApprovalStagesGene":
        return cls(rng.randint(MIN_STAGES, MAX_STAGES))

    def mutate(self, rng: random.Random) -> "ApprovalStagesGene":
        return ApprovalStagesGene(
            _step_bounded_int(self.value, MIN_STAGES, MAX_STAGES, rng)
        )


@dataclass(frozen=True)
class PolicyCoverageGene:
    rule_count: int
    fail_closed: bool

    @classmethod
    def sample(cls, rng: random.Random) -> "PolicyCoverageGene":
        return cls(
            rng.randint(MIN_POLICY_RULES, MAX_POLICY_RULES),
            rng.choice([True, False]),
        )

    def mutate(self, rng: random.Random) -> "PolicyCoverageGene":
        rule_count = (
            _step_bounded_int(self.rule_count, MIN_POLICY_RULES, MAX_POLICY_RULES, rng)
            if rng.random() < 0.5
            else self.rule_count
        )
        fail_closed = (
            (not self.fail_closed) if rng.random() < 0.5 else self.fail_closed
        )
        return PolicyCoverageGene(rule_count, fail_closed)


@dataclass(frozen=True)
class ExceptionPolicyGene:
    max_severity: ExceptionSeverity
    review_required: bool

    @classmethod
    def sample(cls, rng: random.Random) -> "ExceptionPolicyGene":
        return cls(rng.choice(list(ExceptionSeverity)), rng.choice([True, False]))

    def mutate(self, rng: random.Random) -> "ExceptionPolicyGene":
        max_severity = (
            _mutate_enum(self.max_severity, list(ExceptionSeverity), rng)
            if rng.random() < 0.5
            else self.max_severity
        )
        review_required = (
            (not self.review_required) if rng.random() < 0.5 else self.review_required
        )
        return ExceptionPolicyGene(max_severity, review_required)


@dataclass(frozen=True)
class AuditMandateGene:
    value: bool

    @classmethod
    def sample(cls, rng: random.Random) -> "AuditMandateGene":
        return cls(rng.choice([True, False]))

    def mutate(self, rng: random.Random) -> "AuditMandateGene":
        return AuditMandateGene(not self.value)


@dataclass(frozen=True)
class ComplianceMandateGene:
    value: bool

    @classmethod
    def sample(cls, rng: random.Random) -> "ComplianceMandateGene":
        return cls(rng.choice([True, False]))

    def mutate(self, rng: random.Random) -> "ComplianceMandateGene":
        return ComplianceMandateGene(not self.value)


@dataclass(frozen=True)
class VersioningStrategyGene:
    value: VersioningStrategyKind

    @classmethod
    def sample(cls, rng: random.Random) -> "VersioningStrategyGene":
        return cls(rng.choice(list(VersioningStrategyKind)))

    def mutate(self, rng: random.Random) -> "VersioningStrategyGene":
        return VersioningStrategyGene(
            _mutate_enum(self.value, list(VersioningStrategyKind), rng)
        )


@dataclass(frozen=True)
class GovernanceChromosome:
    """The Governance chromosome family representative: a bundle of independent
    governance genes plus expression into governance ISR."""

    voting_rule: VotingRuleGene
    quorum: QuorumGene
    approval_stages: ApprovalStagesGene
    policy_coverage: PolicyCoverageGene
    exception_policy: ExceptionPolicyGene
    audit_mandate: AuditMandateGene
    compliance_mandate: ComplianceMandateGene
    versioning_strategy: VersioningStrategyGene

    @classmethod
    def sample(cls, rng: random.Random) -> "GovernanceChromosome":
        return cls(
            voting_rule=VotingRuleGene.sample(rng),
            quorum=QuorumGene.sample(rng),
            approval_stages=ApprovalStagesGene.sample(rng),
            policy_coverage=PolicyCoverageGene.sample(rng),
            exception_policy=ExceptionPolicyGene.sample(rng),
            audit_mandate=AuditMandateGene.sample(rng),
            compliance_mandate=ComplianceMandateGene.sample(rng),
            versioning_strategy=VersioningStrategyGene.sample(rng),
        )

    def mutate(
        self, rng: random.Random, mutation_rate: float = 0.2
    ) -> "GovernanceChromosome":
        """Mutate each gene independently with probability ``mutation_rate``."""

        def maybe(gene):
            return gene.mutate(rng) if rng.random() < mutation_rate else gene

        return GovernanceChromosome(
            voting_rule=maybe(self.voting_rule),
            quorum=maybe(self.quorum),
            approval_stages=maybe(self.approval_stages),
            policy_coverage=maybe(self.policy_coverage),
            exception_policy=maybe(self.exception_policy),
            audit_mandate=maybe(self.audit_mandate),
            compliance_mandate=maybe(self.compliance_mandate),
            versioning_strategy=maybe(self.versioning_strategy),
        )

    def crossover(
        self, other: "GovernanceChromosome", rng: random.Random
    ) -> "GovernanceChromosome":
        """Independent per-gene uniform crossover."""

        def pick(a, b):
            return a if rng.random() < 0.5 else b

        return GovernanceChromosome(
            voting_rule=pick(self.voting_rule, other.voting_rule),
            quorum=pick(self.quorum, other.quorum),
            approval_stages=pick(self.approval_stages, other.approval_stages),
            policy_coverage=pick(self.policy_coverage, other.policy_coverage),
            exception_policy=pick(self.exception_policy, other.exception_policy),
            audit_mandate=pick(self.audit_mandate, other.audit_mandate),
            compliance_mandate=pick(self.compliance_mandate, other.compliance_mandate),
            versioning_strategy=pick(self.versioning_strategy, other.versioning_strategy),
        )

    def express(self) -> GovernanceDesignISR:
        """Genes -> governance ISR. The evolution engine consumes this ISR."""
        return GovernanceDesignISR(
            design_id=f"gd-{uuid4().hex}",
            voting_rule=self.voting_rule.value,
            quorum=self.quorum.value,
            approval_stage_count=self.approval_stages.value,
            policy_rule_count=self.policy_coverage.rule_count,
            fail_closed_default=self.policy_coverage.fail_closed,
            exception_max_severity=self.exception_policy.max_severity,
            exception_review_required=self.exception_policy.review_required,
            audit_chaining_required=self.audit_mandate.value,
            compliance_evaluation_required=self.compliance_mandate.value,
            versioning_strategy=self.versioning_strategy.value,
        )

    def project_approval_workflow(self, workflow_id: str) -> ApprovalWorkflowISR:
        """Compile the amendment-process genes into a concrete governance ISR
        artifact (real content, fully determined by the genes). Policy-rule
        bodies are requirement-derived and intentionally not fabricated here."""
        stages = [
            ApprovalStageISR(
                stage_id=f"stage-{i}", approvers=[], rule=self.voting_rule.value
            )
            for i in range(self.approval_stages.value)
        ]
        return ApprovalWorkflowISR(
            workflow_id=workflow_id,
            purpose="Governance amendment ratification",
            stages=stages,
            quorum=self.quorum.value,
        )


# ===========================================================================
# ADAPTATION POINT - genome integration (do not fabricate):
#   1. Chromosome-family registry: how the genome registers the Governance
#      family and instantiates GovernanceChromosome.sample per candidate.
#   2. Gene base class / mutation / crossover contract: if the genome defines
#      a base Gene with required methods, wrap these genes (thin adapter); the
#      value-space and mutation semantics above transfer unchanged.
#   3. Candidate model: how a candidate carries/expresses its
#      GovernanceDesignISR so the fitness bridge can consume it per candidate.
# Paste the genome contract to finalise this seam in one edit.
# ===========================================================================
