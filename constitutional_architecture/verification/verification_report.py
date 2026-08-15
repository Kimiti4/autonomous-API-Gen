from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from constitutional_architecture.verification.verification_result import (
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)


@dataclass(frozen=True)
class RepairRecommendation:
    check_id: str
    mutation_type: str
    target_isr_node_id: str
    description: str
    confidence: float = 0.0
    priority: int = 0
    estimated_fitness_impact: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationReport:
    report_id: str = ""
    isr_hash: str = ""
    compilation_result_hash: str = ""
    verifier_version: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verification_level_achieved: VerificationLevel = VerificationLevel.L0_ARCHITECTURAL
    verifier_results: tuple[VerificationResult, ...] = ()
    all_checks: tuple[VerificationCheck, ...] = ()
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    skipped_checks: int = 0
    approved_for_deployment: bool = False
    deployment_constraints: tuple[str, ...] = ()
    blocking_failures: tuple[VerificationCheck, ...] = ()
    repair_recommendations: tuple[RepairRecommendation, ...] = ()
    fitness_contribution: dict[str, float] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    verifier_durations: dict[str, float] = field(default_factory=dict)

    @property
    def has_blockers(self) -> bool:
        return len(self.blocking_failures) > 0

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed_checks / self.total_checks

    @property
    def summary(self) -> str:
        status = "APPROVED" if self.approved_for_deployment else "REJECTED"
        return (
            f"Verification {status}: "
            f"{self.passed_checks}/{self.total_checks} checks passed, "
            f"{self.failed_checks} failed, "
            f"{self.warning_checks} warnings, "
            f"level={self.verification_level_achieved.name}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "isr_hash": self.isr_hash,
            "approved_for_deployment": self.approved_for_deployment,
            "verification_level": self.verification_level_achieved.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "pass_rate": self.pass_rate,
            "blocking_failures": [
                {"check_id": c.check_id, "message": c.message, "severity": c.severity.value}
                for c in self.blocking_failures
            ],
            "repair_recommendations": [
                {
                    "check_id": r.check_id,
                    "mutation_type": r.mutation_type,
                    "target": r.target_isr_node_id,
                    "description": r.description,
                    "confidence": r.confidence,
                }
                for r in self.repair_recommendations
            ],
            "fitness_contribution": self.fitness_contribution,
            "deployment_constraints": list(self.deployment_constraints),
            "timestamp": self.timestamp.isoformat(),
        }
