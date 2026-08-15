from typing import Any

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.isr_adapter import evaluate_fitness
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.verification.verification_context import ArtifactReference
from constitutional_architecture.verification.verification_engine import VerificationEngine
from constitutional_architecture.verification.verification_report import VerificationReport
from constitutional_architecture.verification.verification_result import VerificationLevel, VerificationResult


class VerificationBridge:
    def __init__(self, minimum_level: VerificationLevel = VerificationLevel.L2_BEHAVIOURAL) -> None:
        self._minimum_level = minimum_level
        self._engine = VerificationEngine()

    def verify(
        self,
        isr: ISR,
        generated_files: list[str] | None = None,
    ) -> VerificationReport:
        artifacts: tuple[ArtifactReference, ...] = ()
        if generated_files:
            artifacts = tuple(
                ArtifactReference(path=fp, artifact_type="generated_source")
                for fp in generated_files
            )
        return self._engine.verify(isr, artifacts=list(artifacts))

    def to_fitness(
        self,
        report: VerificationReport,
        static_fitness: FitnessVector | None = None,
    ) -> FitnessVector:
        values: dict[str, float] = {}
        if static_fitness is not None:
            values.update(static_fitness.values)
        values["verification_passed"] = 1.0 if report.approved_for_deployment else 0.0
        values["verification_level"] = min(1.0, float(report.verification_level_achieved) / 5.0)
        total = report.total_checks or 1
        passed = report.passed_checks or 0
        values["verification_coverage"] = passed / total
        values["issues_found"] = max(0.0, 1.0 - report.failed_checks * 0.1)
        return FitnessVector(values=values)
