"""
Reference pipeline stage adapters.

These adapters are deterministic reference implementations. Production
deployments should replace them with adapters wrapping the real phase engines:

- Requirements engine
- ISR construction engine
- Evolution engine
- Verification engine
- Universal compiler
- Deployment controller
- Monitoring platform
- Continuous learning infrastructure
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from .models import (
    CrossOrganizationContract,
    PipelineStageName,
    StageResult,
    StageStatus,
    canonical_json,
    sha256_hex,
)


@dataclass
class StageContext:
    """Context passed to a pipeline stage adapter."""

    objective: str
    requirements: Dict[str, Any]
    artifacts: Dict[str, Dict[str, Any]]
    contract: CrossOrganizationContract


class StageAdapter(Protocol):
    """Protocol for pipeline stage adapters."""

    stage: PipelineStageName

    def execute(self, context: StageContext) -> StageResult:
        ...


def _hash_payload(payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_json(payload))


class RequirementAnalysisAdapter:
    """Analyzes requirements and produces a requirement graph artifact."""

    stage = PipelineStageName.REQUIREMENT_ANALYSIS

    def execute(self, context: StageContext) -> StageResult:
        if not context.objective:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Objective is required.",
            )

        graph_hash = _hash_payload(
            {
                "objective": context.objective,
                "requirements": context.requirements,
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "requirements_graph": graph_hash,
            },
            evidence_refs=[
                f"requirements_graph:{graph_hash}",
            ],
            metrics={
                "requirement_keys": len(context.requirements),
            },
        )


class ISRConstructionAdapter:
    """Constructs ISR from the requirement graph."""

    stage = PipelineStageName.ISR_CONSTRUCTION

    def execute(self, context: StageContext) -> StageResult:
        requirement_artifact = context.artifacts.get(
            PipelineStageName.REQUIREMENT_ANALYSIS.value,
            {},
        )

        requirements_graph = requirement_artifact.get("requirements_graph")

        if not requirements_graph:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing requirement graph artifact.",
            )

        isr_hash = _hash_payload(
            {
                "requirements_graph": requirements_graph,
                "objective": context.objective,
                "representation": "ISR.v1",
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "isr": isr_hash,
            },
            evidence_refs=[
                f"isr:{isr_hash}",
            ],
            metrics={
                "representation": "ISR.v1",
            },
        )


class EvolutionAdapter:
    """Evolves ISR candidates."""

    stage = PipelineStageName.EVOLUTION

    def execute(self, context: StageContext) -> StageResult:
        isr_artifact = context.artifacts.get(
            PipelineStageName.ISR_CONSTRUCTION.value,
            {},
        )

        isr_hash = isr_artifact.get("isr")

        if not isr_hash:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing ISR artifact.",
            )

        evolved_isr_hash = _hash_payload(
            {
                "parent_isr": isr_hash,
                "objective": context.objective,
                "evolution_strategy": "pareto_multi_objective",
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "evolved_isr": evolved_isr_hash,
            },
            evidence_refs=[
                f"evolved_isr:{evolved_isr_hash}",
            ],
            metrics={
                "candidates": 3,
                "selection": "pareto_front",
            },
        )


class VerificationAdapter:
    """Verifies evolved ISR candidates."""

    stage = PipelineStageName.VERIFICATION

    def execute(self, context: StageContext) -> StageResult:
        evolution_artifact = context.artifacts.get(
            PipelineStageName.EVOLUTION.value,
            {},
        )

        evolved_isr = evolution_artifact.get("evolved_isr")

        if not evolved_isr:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing evolved ISR artifact.",
            )

        verification_hash = _hash_payload(
            {
                "evolved_isr": evolved_isr,
                "verification_suite": [
                    "unit",
                    "integration",
                    "contract",
                    "security",
                    "performance",
                ],
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "verification_report": verification_hash,
                "passed": True,
            },
            evidence_refs=[
                f"verification_report:{verification_hash}",
            ],
            metrics={
                "tests_passed": True,
                "fitness": {
                    "maintainability": 0.85,
                    "reliability": 0.82,
                    "security": 0.88,
                    "performance": 0.80,
                    "deployability": 0.86,
                },
            },
        )


class CompilationAdapter:
    """Compiles verified ISR into production artifacts."""

    stage = PipelineStageName.COMPILATION

    def execute(self, context: StageContext) -> StageResult:
        evolution_artifact = context.artifacts.get(
            PipelineStageName.EVOLUTION.value,
            {},
        )

        verification_artifact = context.artifacts.get(
            PipelineStageName.VERIFICATION.value,
            {},
        )

        evolved_isr = evolution_artifact.get("evolved_isr")
        verification_passed = verification_artifact.get("passed", False)

        if not evolved_isr:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing evolved ISR artifact.",
            )

        if not verification_passed:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Verification did not pass.",
            )

        compiled_artifact_hash = _hash_payload(
            {
                "evolved_isr": evolved_isr,
                "compiler_backends": [
                    "reference_compiler_backend",
                ],
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "compiled_artifacts": [
                    compiled_artifact_hash,
                ],
            },
            evidence_refs=[
                f"compiled_artifact:{compiled_artifact_hash}",
            ],
            metrics={
                "backends": 1,
            },
        )


class DeploymentAdapter:
    """Deploys compiled artifacts into a governed environment."""

    stage = PipelineStageName.DEPLOYMENT

    def execute(self, context: StageContext) -> StageResult:
        compilation_artifact = context.artifacts.get(
            PipelineStageName.COMPILATION.value,
            {},
        )

        verification_artifact = context.artifacts.get(
            PipelineStageName.VERIFICATION.value,
            {},
        )

        compiled_artifacts = compilation_artifact.get("compiled_artifacts", [])
        verification_passed = verification_artifact.get("passed", False)

        if not compiled_artifacts:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing compiled artifacts.",
            )

        if not verification_passed:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Deployment blocked because verification did not pass.",
            )

        deployment_hash = _hash_payload(
            {
                "compiled_artifacts": compiled_artifacts,
                "deployment_target": "governed_staging_environment",
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "deployment_ref": deployment_hash,
            },
            evidence_refs=[
                f"deployment:{deployment_hash}",
            ],
            metrics={
                "environment": "governed_staging_environment",
            },
        )


class MonitoringAdapter:
    """Starts monitoring for the deployed system."""

    stage = PipelineStageName.MONITORING

    def execute(self, context: StageContext) -> StageResult:
        deployment_artifact = context.artifacts.get(
            PipelineStageName.DEPLOYMENT.value,
            {},
        )

        deployment_ref = deployment_artifact.get("deployment_ref")

        if not deployment_ref:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing deployment reference.",
            )

        monitoring_hash = _hash_payload(
            {
                "deployment_ref": deployment_ref,
                "monitoring_streams": [
                    "metrics",
                    "logs",
                    "traces",
                    "health",
                    "audit",
                ],
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "monitoring_stream": monitoring_hash,
            },
            evidence_refs=[
                f"monitoring_stream:{monitoring_hash}",
            ],
            metrics={
                "health": "HEALTHY",
            },
        )


class LearningAdapter:
    """Converts operational monitoring into learning and evolution feedback."""

    stage = PipelineStageName.LEARNING

    def execute(self, context: StageContext) -> StageResult:
        monitoring_artifact = context.artifacts.get(
            PipelineStageName.MONITORING.value,
            {},
        )

        monitoring_stream = monitoring_artifact.get("monitoring_stream")

        if not monitoring_stream:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error="Missing monitoring stream.",
            )

        learning_hash = _hash_payload(
            {
                "monitoring_stream": monitoring_stream,
                "learning_outputs": [
                    "fitness_update",
                    "genome_refinement_hint",
                    "evolution_proposal",
                ],
            }
        )

        evolution_proposal_hash = _hash_payload(
            {
                "learning_feedback": learning_hash,
                "proposal_type": "architecture_improvement",
            }
        )

        return StageResult(
            stage=self.stage,
            status=StageStatus.COMPLETED,
            data={
                "learning_feedback": learning_hash,
                "evolution_proposal": evolution_proposal_hash,
            },
            evidence_refs=[
                f"learning_feedback:{learning_hash}",
                f"evolution_proposal:{evolution_proposal_hash}",
            ],
            metrics={
                "feedback_signals": 1,
            },
        )


def default_stage_adapters() -> Dict[PipelineStageName, StageAdapter]:
    """Return the default reference stage adapters."""
    return {
        PipelineStageName.REQUIREMENT_ANALYSIS: RequirementAnalysisAdapter(),
        PipelineStageName.ISR_CONSTRUCTION: ISRConstructionAdapter(),
        PipelineStageName.EVOLUTION: EvolutionAdapter(),
        PipelineStageName.VERIFICATION: VerificationAdapter(),
        PipelineStageName.COMPILATION: CompilationAdapter(),
        PipelineStageName.DEPLOYMENT: DeploymentAdapter(),
        PipelineStageName.MONITORING: MonitoringAdapter(),
        PipelineStageName.LEARNING: LearningAdapter(),
    }
