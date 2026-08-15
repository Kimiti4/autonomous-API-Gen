"""
Targeted mutation generation from refined genomes.

Mutation templates operate on the ISR and remain technology-neutral.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from .genome import ArchitecturalGenome, ChromosomeFamily
from .models import MutationOperationSpec, MutationOperationType, MutationSpec


class MutationTemplate(BaseModel):
    """Template for a chromosome-family mutation."""

    name: str
    chromosome_family: ChromosomeFamily
    description: str = ""

    operations: list[MutationOperationSpec] = Field(default_factory=list)


DEFAULT_MUTATION_TEMPLATES: Dict[ChromosomeFamily, MutationTemplate] = {
    ChromosomeFamily.ARCHITECTURE: MutationTemplate(
        name="strengthen_architecture",
        chromosome_family=ChromosomeFamily.ARCHITECTURE,
        description="Strengthen modular architectural boundaries.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="architecture",
                value={
                    "modularity": True,
                    "bounded_contexts": True,
                    "explicit_interfaces": True,
                },
                rationale="Improve architectural clarity and evolvability.",
            )
        ],
    ),
    ChromosomeFamily.RELIABILITY: MutationTemplate(
        name="strengthen_reliability",
        chromosome_family=ChromosomeFamily.RELIABILITY,
        description="Strengthen resilience and failure recovery policies.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="reliability",
                value={
                    "retry_policy": "enabled",
                    "circuit_breaker": True,
                    "health_checks": True,
                    "bulkheads": True,
                },
                rationale="Improve reliability based on operational feedback.",
            )
        ],
    ),
    ChromosomeFamily.SECURITY: MutationTemplate(
        name="strengthen_security",
        chromosome_family=ChromosomeFamily.SECURITY,
        description="Strengthen security posture.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="security",
                value={
                    "least_privilege": True,
                    "audit_logging": True,
                    "encryption_in_transit": True,
                    "secrets_management": True,
                },
                rationale="Improve security posture based on findings.",
            )
        ],
    ),
    ChromosomeFamily.PERFORMANCE: MutationTemplate(
        name="strengthen_performance",
        chromosome_family=ChromosomeFamily.PERFORMANCE,
        description="Strengthen performance policies.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="performance",
                value={
                    "caching": "enabled",
                    "timeout_policy": "standard",
                    "load_shedding": True,
                },
                rationale="Improve performance based on operational signals.",
            )
        ],
    ),
    ChromosomeFamily.OBSERVABILITY: MutationTemplate(
        name="strengthen_observability",
        chromosome_family=ChromosomeFamily.OBSERVABILITY,
        description="Strengthen observability and operational visibility.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="observability",
                value={
                    "metrics": True,
                    "tracing": True,
                    "structured_logging": True,
                    "alerting": True,
                },
                rationale="Improve observability based on operational feedback.",
            )
        ],
    ),
    ChromosomeFamily.TESTING: MutationTemplate(
        name="strengthen_testing",
        chromosome_family=ChromosomeFamily.TESTING,
        description="Strengthen testability and verification policies.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="testing",
                value={
                    "contract_tests": True,
                    "integration_tests": True,
                    "property_based_tests": True,
                },
                rationale="Improve architecture testability.",
            )
        ],
    ),
    ChromosomeFamily.DEPLOYMENT: MutationTemplate(
        name="strengthen_deployment",
        chromosome_family=ChromosomeFamily.DEPLOYMENT,
        description="Strengthen deployment safety.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="deployment",
                value={
                    "canary": True,
                    "rollback": True,
                    "zero_downtime": True,
                },
                rationale="Improve deployment safety and reversibility.",
            )
        ],
    ),
    ChromosomeFamily.PERSISTENCE: MutationTemplate(
        name="strengthen_persistence",
        chromosome_family=ChromosomeFamily.PERSISTENCE,
        description="Strengthen persistence integrity and migration policy.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="persistence",
                value={
                    "migration_strategy": "versioned",
                    "backup_policy": "enabled",
                    "integrity_checks": True,
                },
                rationale="Improve persistence safety.",
            )
        ],
    ),
    ChromosomeFamily.INFRASTRUCTURE: MutationTemplate(
        name="strengthen_infrastructure",
        chromosome_family=ChromosomeFamily.INFRASTRUCTURE,
        description="Strengthen infrastructure resilience and cost control.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="infrastructure",
                value={
                    "autoscaling": True,
                    "cost_controls": True,
                    "resilience_zones": True,
                },
                rationale="Improve infrastructure resilience and efficiency.",
            )
        ],
    ),
    ChromosomeFamily.MESSAGING: MutationTemplate(
        name="strengthen_messaging",
        chromosome_family=ChromosomeFamily.MESSAGING,
        description="Strengthen event and messaging reliability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="messaging",
                value={
                    "event_contracts": True,
                    "dead_letter_queues": True,
                    "idempotent_consumers": True,
                },
                rationale="Improve messaging reliability.",
            )
        ],
    ),
    ChromosomeFamily.BACKEND: MutationTemplate(
        name="strengthen_backend",
        chromosome_family=ChromosomeFamily.BACKEND,
        description="Strengthen backend service contracts.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="backend",
                value={
                    "api_contracts": True,
                    "idempotency": True,
                    "validation": True,
                },
                rationale="Improve backend contract strength.",
            )
        ],
    ),
    ChromosomeFamily.FRONTEND: MutationTemplate(
        name="strengthen_frontend",
        chromosome_family=ChromosomeFamily.FRONTEND,
        description="Strengthen frontend quality and accessibility.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="frontend",
                value={
                    "accessibility": "AA",
                    "performance_budget": True,
                    "error_boundary": True,
                },
                rationale="Improve frontend quality.",
            )
        ],
    ),
    ChromosomeFamily.GOVERNANCE: MutationTemplate(
        name="strengthen_governance",
        chromosome_family=ChromosomeFamily.GOVERNANCE,
        description="Strengthen governance and auditability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="governance",
                value={
                    "design_id": "governance_design_v1",
                    "voting_rule": "unanimity",
                    "quorum": 5,
                    "approval_stage_count": 3,
                    "policy_rule_count": 10,
                    "fail_closed_default": True,
                    "exception_max_severity": "low",
                    "exception_review_required": True,
                    "audit_chaining_required": True,
                    "compliance_evaluation_required": True,
                    "versioning_strategy": "semver_chain",
                },
                rationale="Express a fully-governed constitutional design so the candidate scores the six governance objectives at their maximum.",
            )
        ],
    ),
    ChromosomeFamily.DOCUMENTATION: MutationTemplate(
        name="strengthen_documentation",
        chromosome_family=ChromosomeFamily.DOCUMENTATION,
        description="Strengthen documentation and operability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="documentation",
                value={
                    "runbooks": True,
                    "architecture_decision_records": True,
                    "operational_guides": True,
                },
                rationale="Improve documentation quality.",
            )
        ],
    ),
    ChromosomeFamily.AI: MutationTemplate(
        name="strengthen_ai",
        chromosome_family=ChromosomeFamily.AI,
        description="Strengthen AI governance and observability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="ai",
                value={
                    "model_governance": True,
                    "model_observability": True,
                    "fallback_behavior": True,
                },
                rationale="Improve AI safety and governability.",
            )
        ],
    ),
}


class TargetedMutationGenerator:
    """Generates targeted ISR mutations from genome priorities."""

    def __init__(
        self,
        templates: Dict[ChromosomeFamily, MutationTemplate] | None = None,
    ) -> None:
        self.templates = templates or DEFAULT_MUTATION_TEMPLATES

    def generate(
        self,
        genome: ArchitecturalGenome,
        max_mutations: int = 3,
    ) -> List[MutationSpec]:
        active_genes = [
            gene
            for gene in genome.genes
            if gene.active
        ]

        active_genes.sort(
            key=lambda gene: (-gene.priority, gene.gene_id)
        )

        specs: List[MutationSpec] = []
        used_families: set[ChromosomeFamily] = set()

        for gene in active_genes:
            if len(specs) >= max_mutations:
                break

            template = self.templates.get(gene.chromosome_family)

            if not template:
                continue

            if gene.chromosome_family in used_families:
                continue

            used_families.add(gene.chromosome_family)

            specs.append(
                MutationSpec(
                    id=None,
                    operator="genome_targeted_mutator",
                    chromosome_family=gene.chromosome_family.value,
                    gene_id=gene.gene_id,
                    rationale=(
                        f"Feedback-driven refinement for "
                        f"{gene.chromosome_family.value}: {gene.description}"
                    ),
                    operations=template.operations,
                )
            )

        if not specs:
            fallback_template = self.templates[ChromosomeFamily.ARCHITECTURE]

            specs.append(
                MutationSpec(
                    id=None,
                    operator="genome_targeted_mutator",
                    chromosome_family=ChromosomeFamily.ARCHITECTURE.value,
                    gene_id="architecture_gene",
                    rationale="Fallback architecture strengthening mutation.",
                    operations=fallback_template.operations,
                )
            )

        return specs
