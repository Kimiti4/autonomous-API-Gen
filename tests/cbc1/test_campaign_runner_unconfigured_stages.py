from certification.campaign.runner import _unconfigured_stage
from certification.core.trial import TrialStage, compose_verdict


def test_unconfigured_execution_stages_fail_closed():
    for stage in (
        TrialStage.BUILD,
        TrialStage.TEST,
        TrialStage.DEPLOY,
        TrialStage.RUNTIME,
        TrialStage.DESTROY,
    ):
        passed, detail = _unconfigured_stage(stage)
        assert passed is False
        assert "not_configured" in detail
        assert stage.value in detail


def test_unconfigured_stage_cannot_certify_trial():
    stages = {stage: True for stage in (
        TrialStage.STRUCTURAL,
        TrialStage.SEMANTIC,
        TrialStage.BUILD,
        TrialStage.TEST,
        TrialStage.DEPLOY,
        TrialStage.RUNTIME,
        TrialStage.DESTROY,
        TrialStage.VERIFY,
    )}
    stages[TrialStage.DEPLOY] = _unconfigured_stage(TrialStage.DEPLOY)[0]
    assert compose_verdict(stages, evidence_present=True) == "NOT_CERTIFIED"


def test_real_build_is_skipped_when_structural_semantic_prerequisites_fail(monkeypatch):
    from types import SimpleNamespace

    from certification.campaign.plan_builder import build_artifacts_for
    from certification.campaign.runner import CampaignRunner
    from certification.corpus.corpus import default_corpus
    from certification.core.trial import TrialStage
    from compiler.composition import build_backend_registry

    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    backend = build_backend_registry().get("python-fastapi")

    class Builder:
        def __init__(self):
            self.calls = []

        def build(self, repo_dir, tag):
            self.calls.append((repo_dir, tag))
            raise AssertionError("build must not run for a non-conformant candidate")

    monkeypatch.setattr(
        backend,
        "conformance",
        lambda plan, repo: SimpleNamespace(passed=False, missing=("required operation",)),
    )
    builder = Builder()
    trial = CampaignRunner(builder=builder).run_trial(
        intent=workload.intent,
        category=workload.category.value,
        novelty_class="template",
        plan=artifacts.plan,
        revision_id=artifacts.revision.revision_id,
        backend=backend,
        requirement_graph_hash=artifacts.requirement_graph_hash,
        genome_hash=artifacts.genome_hash,
        workload=workload,
        artifacts=artifacts,
    )

    stages = {stage.stage: stage for stage in trial.stages}
    assert builder.calls == []
    assert stages[TrialStage.STRUCTURAL].passed is False
    assert stages[TrialStage.SEMANTIC].passed is False
    assert stages[TrialStage.BUILD].passed is False
    assert "skipped" in stages[TrialStage.BUILD].detail
    assert "prerequisite" in stages[TrialStage.BUILD].detail
    assert trial.verdict == "NOT_CERTIFIED"
