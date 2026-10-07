import pytest

from app.engine.final_closure import ClosureStatus
from app.engine.generation_scope import GenerationScope
from app.engine.governed_pipeline import (
    PipelineStage, StageArtifact, execute_governed_pipeline,
)
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode


def contract():
    return WorkCapabilityContract.create(
        ProjectScope.create_new(),
        WorkMode.GENERATE,
        GenerationScope.FULL_APPLICATION,
    )


def runner(stage, prior):
    return StageArtifact(
        stage=stage,
        artifact_id=f"{stage.value}-1",
        digest="a" * 64,
        evidence_ids=(f"{stage.value}-evidence",) if stage in {
            PipelineStage.VERIFICATION, PipelineStage.EVIDENCE, PipelineStage.CERTIFICATION
        } else (),
    )


def test_full_pipeline_reaches_closure():
    result = execute_governed_pipeline(
        work_id="work-1",
        contract=contract(),
        surface="full_application",
        authoritative_obligation_ids=("req-1", "req-2"),
        completed_obligation_ids=("req-1", "req-2"),
        verification_evidence_complete=True,
        stage_runner=runner,
    )
    assert result.closure.status is ClosureStatus.READY_TO_STOP
    assert result.stages[-1].stage is PipelineStage.CLOSURE
    assert len(result.pipeline_digest) == 64


def test_pipeline_rejects_unauthorized_surface():
    with pytest.raises(ValueError, match="pipeline-surface-not-authorized"):
        execute_governed_pipeline(
            work_id="work-2",
            contract=contract(),
            surface="backend_only",
            authoritative_obligation_ids=("req-1",),
            completed_obligation_ids=("req-1",),
            verification_evidence_complete=True,
            stage_runner=runner,
        )


def test_pipeline_cannot_stop_with_missing_obligation():
    with pytest.raises(ValueError, match="closure-not-ready-to-stop"):
        execute_governed_pipeline(
            work_id="work-3",
            contract=contract(),
            surface="full_application",
            authoritative_obligation_ids=("req-1", "req-2"),
            completed_obligation_ids=("req-1",),
            verification_evidence_complete=True,
            stage_runner=runner,
        )


def test_pipeline_cannot_skip_stage():
    def bad_runner(stage, prior):
        wrong = PipelineStage.CERTIFICATION if stage is PipelineStage.IMPLEMENTATION else stage
        return StageArtifact(wrong, "bad", "b" * 64)
    with pytest.raises(ValueError, match="pipeline-stage-mismatch"):
        execute_governed_pipeline(
            work_id="work-4",
            contract=contract(),
            surface="full_application",
            authoritative_obligation_ids=("req-1",),
            completed_obligation_ids=("req-1",),
            verification_evidence_complete=True,
            stage_runner=bad_runner,
        )
