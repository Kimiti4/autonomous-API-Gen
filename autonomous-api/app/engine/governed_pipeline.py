"""End-to-end governed ESAP work pipeline.

This is the executable integration boundary for the already-built capability
layers. Each stage is explicit and must produce an auditable artifact before
the next stage can run. The orchestrator never invents requirements and never
promotes advisory findings into obligations.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Callable, Mapping

from .final_closure import FinalClosureAssessment, assess_final_closure, require_final_closure
from .generation_scope import GenerationScope
from .work_capability import WorkCapabilityContract, validate_work_capability
from .work_mode_scope_validation import validate_mode_surface


class PipelineStage(str, Enum):
    REQUEST = "request"
    ISR = "isr"
    SCOPE = "scope"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    EXECUTION = "bounded_execution"
    VERIFICATION = "verification"
    EVIDENCE = "evidence"
    CERTIFICATION = "certification"
    CLOSURE = "completion_stop"


@dataclass(frozen=True)
class StageArtifact:
    stage: PipelineStage
    artifact_id: str
    digest: str
    authoritative: bool = True
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.artifact_id.strip() or len(self.digest) != 64:
            raise ValueError("pipeline-invalid-stage-artifact")


@dataclass(frozen=True)
class GovernedPipelineResult:
    work_id: str
    mode: str
    surface: str
    stages: tuple[StageArtifact, ...]
    closure: FinalClosureAssessment
    pipeline_digest: str


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _require_stage(previous: StageArtifact | None, expected: PipelineStage) -> None:
    if previous is not None and previous.stage.value != expected.value:
        raise ValueError(f"pipeline-stage-order:{previous.stage.value}:{expected.value}")


def execute_governed_pipeline(
    *,
    work_id: str,
    contract: WorkCapabilityContract,
    surface: str,
    authoritative_obligation_ids: tuple[str, ...],
    completed_obligation_ids: tuple[str, ...],
    verification_evidence_complete: bool,
    stage_runner: Callable[[PipelineStage, tuple[StageArtifact, ...]], StageArtifact],
    deployment_required: bool = False,
    deployment_ready: bool = True,
    blocking_findings: tuple[str, ...] = (),
    advisory_findings: tuple[str, ...] = (),
) -> GovernedPipelineResult:
    if not work_id.strip():
        raise ValueError("pipeline-missing-work-id")
    contract = validate_work_capability(contract)
    validate_mode_surface(contract)
    surface_scope = {
        "full_application": (GenerationScope.FULL_APPLICATION, ("frontend", "backend", "api_contract")),
        "frontend_only": (GenerationScope.FRONTEND_ONLY, ("frontend",)),
        "backend_only": (GenerationScope.BACKEND_ONLY, ("backend",)),
        "api_contract_only": (GenerationScope.API_CONTRACT_ONLY, ("api_contract",)),
    }.get(surface)
    if surface_scope is None:
        raise ValueError(f"pipeline-surface-not-authorized:{surface}")
    expected_scope, component_surfaces = surface_scope
    if contract.generation.scope is not expected_scope or not all(
        contract.mode.allows_surface(component) for component in component_surfaces
    ):
        raise ValueError(f"pipeline-surface-not-authorized:{surface}")

    stages: list[StageArtifact] = []
    previous: StageArtifact | None = None

    ordered_stages = (
        PipelineStage.REQUEST,
        PipelineStage.ISR,
        PipelineStage.SCOPE,
        PipelineStage.ARCHITECTURE,
        PipelineStage.IMPLEMENTATION,
        PipelineStage.EXECUTION,
        PipelineStage.VERIFICATION,
        PipelineStage.EVIDENCE,
        PipelineStage.CERTIFICATION,
    )
    for index, stage in enumerate(ordered_stages):
        if index:
            _require_stage(previous, ordered_stages[index - 1])
        artifact = stage_runner(stage, tuple(stages))
        if artifact.stage is not stage:
            raise ValueError(f"pipeline-stage-mismatch:{stage.value}")
        if not artifact.authoritative:
            raise ValueError(f"pipeline-stage-not-authoritative:{stage.value}")
        if previous is not None and not artifact.evidence_ids and stage in {
            PipelineStage.VERIFICATION, PipelineStage.EVIDENCE, PipelineStage.CERTIFICATION
        }:
            raise ValueError(f"pipeline-stage-missing-evidence:{stage.value}")
        stages.append(artifact)
        previous = artifact

    closure = assess_final_closure(
        work_id=work_id,
        authorized_obligation_ids=authoritative_obligation_ids,
        completed_obligation_ids=completed_obligation_ids,
        verification_evidence_complete=verification_evidence_complete,
        deployment_required=deployment_required,
        deployment_ready=deployment_ready,
        blocking_findings=blocking_findings,
        advisory_findings=advisory_findings,
    )
    require_final_closure(closure)
    closure_artifact = StageArtifact(
        PipelineStage.CLOSURE,
        f"closure:{work_id}",
        closure.digest,
        True,
        tuple(sorted(set(closure.completed_obligation_ids))),
    )
    stages.append(closure_artifact)
    pipeline_digest = _digest({
        "work_id": work_id,
        "mode": contract.mode.mode.value,
        "surface": surface,
        "stages": [s.__dict__ for s in stages],
        "closure": closure.digest,
    })
    return GovernedPipelineResult(
        work_id, contract.mode.mode.value, surface, tuple(stages), closure, pipeline_digest
    )
