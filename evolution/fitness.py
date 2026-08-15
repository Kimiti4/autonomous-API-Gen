"""
Multi-objective fitness evaluation.
"""

from __future__ import annotations

from .models import (
    CandidateArchitecture,
    FitnessEvaluation,
    SimulationResult,
    VerificationReport,
)
from .models import utcnow
from .utils import deterministic_id


class FitnessEvaluator:
    """Evaluates candidate architectures using multiple objectives."""

    def evaluate(
        self,
        candidate: CandidateArchitecture,
        simulation: SimulationResult,
        verification: VerificationReport,
    ) -> FitnessEvaluation:
        isr = candidate.isr

        complexity = float(simulation.metrics.get("complexity", 0))

        simplicity = max(0.0, 1.0 - (complexity / 50.0))

        domains = isr.get("domains", []) or []
        services = isr.get("services", []) or []

        has_domain_structure = bool(domains or services)

        modularity = 1.0 if has_domain_structure else 0.0

        security_readiness = 1.0 if isr.get("security") else 0.0
        observability_readiness = 1.0 if isr.get("observability") else 0.0
        deployment_readiness = 1.0 if isr.get("deployment") else 0.0
        testability = 1.0 if isr.get("testing") else 0.0
        compatibility = 1.0 if verification.valid else 0.0

        objectives = {
            "simplicity": round(simplicity, 4),
            "modularity": round(modularity, 4),
            "security_readiness": round(security_readiness, 4),
            "observability_readiness": round(observability_readiness, 4),
            "deployment_readiness": round(deployment_readiness, 4),
            "testability": round(testability, 4),
            "compatibility": round(compatibility, 4),
        }

        constraints = {
            "simulation_passed": simulation.status == "PASSED",
            "verification_valid": verification.valid,
            "complexity_within_limit": complexity <= 100.0,
        }

        notes: list[str] = []

        for objective_name, objective_value in objectives.items():
            if objective_value < 0.2:
                notes.append(
                    f"Objective below threshold: {objective_name}"
                )

        passed = (
            all(constraints.values())
            and all(value >= 0.2 for value in objectives.values())
        )

        fitness_id = deterministic_id(
            "fitness",
            {
                "candidate_id": candidate.id,
                "objectives": objectives,
                "constraints": constraints,
            },
        )

        return FitnessEvaluation(
            id=fitness_id,
            candidate_id=candidate.id,
            objectives=objectives,
            constraints=constraints,
            passed=passed,
            notes=notes,
            created_at=utcnow().isoformat(),
        )
