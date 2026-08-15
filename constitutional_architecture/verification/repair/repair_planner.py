from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass
from constitutional_architecture.verification.verification_report import RepairRecommendation
from constitutional_architecture.verification.verification_result import VerificationCheck


@dataclass(frozen=True)
class RepairPlan:
    eir: EIR
    recommendations: tuple[RepairRecommendation, ...] = ()
    estimated_fitness_impact: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    description: str = ""


REPAIR_MAPPING: dict[str, tuple[str, MutationCategory, MutationClass, str]] = {
    "ARCH-002": ("extract_interface", MutationCategory.STRUCTURAL, MutationClass.STRUCTURAL,
                 "Break cyclic dependency via interface extraction"),
    "SEC-001": ("add_auth_policy", MutationCategory.SECURITY, MutationClass.ADDITIVE,
                "Add authentication policy"),
    "SEC-003": ("add_security_binding", MutationCategory.SECURITY, MutationClass.ADDITIVE,
                "Bind security policy to unsecured interface"),
    "DEPLOY-001": ("add_deployment", MutationCategory.OPERATIONAL, MutationClass.ADDITIVE,
                   "Add deployment configuration"),
    "ARCH-005": ("add_interface", MutationCategory.STRUCTURAL, MutationClass.ADDITIVE,
                 "Add interface to module"),
}


class RepairPlanner:
    def plan_repairs(
        self,
        failed_checks: list[VerificationCheck],
        isr_hash: str,
        generation: int = 0,
    ) -> Optional[RepairPlan]:
        recommendations: list[RepairRecommendation] = []
        transformations: list[Transformation] = []

        for check in failed_checks:
            if check.check_id in REPAIR_MAPPING:
                mutation_type, category, mclass, description = REPAIR_MAPPING[check.check_id]
                recommendations.append(RepairRecommendation(
                    check_id=check.check_id,
                    mutation_type=mutation_type,
                    target_isr_node_id=check.isr_node_id,
                    description=description,
                    confidence=check.repair_confidence or 0.7,
                    priority=0 if check.severity.value == "blocker" else 1,
                ))
                transformations.append(Transformation(
                    id=f"repair-{check.check_id}",
                    transformation_type=mutation_type,
                    category=category,
                    mutation_class=mclass,
                    target_node_id=check.isr_node_id,
                    description=description,
                    reversible=True,
                    rationale=f"Repair for verification failure: {check.message}",
                    confidence=check.repair_confidence or 0.7,
                ))

        if not transformations:
            return None

        eir = EIR(
            id=f"repair-eir-{isr_hash[:12]}",
            source_isr_hash=isr_hash,
            transformations=tuple(transformations),
            proposed_by="repair_planner",
            generation=generation,
        )

        avg_confidence = sum(r.confidence for r in recommendations) / len(recommendations)

        return RepairPlan(
            eir=eir,
            recommendations=tuple(recommendations),
            confidence=avg_confidence,
            description=f"Repair plan for {len(recommendations)} verification failure(s)",
        )
