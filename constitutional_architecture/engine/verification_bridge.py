"""
Verification Bridge — Connects compiled artifacts to Verification Engine
and feeds fitness signals back to the Evolution Engine.

Constitutional constraint:
- The verification engine NEVER imports from engine.*
- The bridge is the ONLY module that connects verification → engine
- Verification results are converted to FitnessVector for evolution
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.engine.evolution_engine import EvolutionEngine
from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.isr_adapter import evaluate_fitness
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.verification.verification_context import ArtifactReference
from constitutional_architecture.verification.verification_engine import VerificationEngine
from constitutional_architecture.verification.verification_result import VerificationLevel, VerificationResult


def verify_compilation(
    isr: ISR,
    generated_files: list[str] | None = None,
    verification_level: VerificationLevel = VerificationLevel.L2_BEHAVIOURAL,
) -> VerificationResult:
    """
    Run the Verification Engine against the ISR to produce a report.

    The Verification Engine checks structural validity, security policies,
    deployment readiness, and other constitutional constraints.
    """
    engine = VerificationEngine(minimum_level=verification_level)

    artifacts: tuple[ArtifactReference, ...] = ()
    if generated_files:
        artifacts = tuple(
            ArtifactReference(path=fp, artifact_type="generated_source")
            for fp in generated_files
        )

    result = engine.verify(isr, artifacts=artifacts)
    return result


def verification_to_fitness(
    verification_result: VerificationResult,
    static_fitness: FitnessVector | None = None,
) -> FitnessVector:
    """
    Convert a VerificationResult into a FitnessVector for the evolution engine.

    Maps verification pass/fail and report metrics to fitness dimensions.
    """
    values: dict[str, float] = {}

    if static_fitness is not None:
        values.update(static_fitness.values)

    values["verification_passed"] = 1.0 if verification_result.passed else 0.0
    values["verification_level"] = min(
        1.0, float(verification_result.level.value[1]) / 5.0
        if hasattr(verification_result.level, "value")
        and verification_result.level.value
        else 0.5
    )

    report = verification_result.report
    if report:
        total = report.verifiers_run or 1
        passed = report.verifiers_passed or 0
        values["verification_coverage"] = passed / total
        values["issues_found"] = max(0.0, 1.0 - (report.issues_count or 0) * 0.1)
    else:
        values["verification_coverage"] = 1.0 if verification_result.passed else 0.0
        values["issues_found"] = 1.0

    return FitnessVector(values=values)


def feed_fitness_to_engine(
    engine: EvolutionEngine,
    fitness: FitnessVector,
) -> None:
    """
    Feed external fitness signals into the evolution engine's memory
    for adaptive mutation weighting in subsequent generations.
    """
    for dim in fitness.dimensions:
        score = fitness.get(dim)
        engine._memory.record_fitness_feedback(dim, score)
