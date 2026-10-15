import os

import pytest

import certification.campaign.runner as runner_module
from certification.campaign.plan_builder import build_artifacts_for
from certification.campaign.runner import CampaignRunner
from certification.corpus.corpus import default_corpus
from compiler.composition import build_backend_registry


def test_trial_workspace_is_removed_when_conformance_raises(monkeypatch, tmp_path):
    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    backend = build_backend_registry().get("python-fastapi")
    created = []
    real_mkdtemp = runner_module.tempfile.mkdtemp

    def tracked_mkdtemp(*args, **kwargs):
        path = real_mkdtemp(*args, dir=str(tmp_path), **kwargs)
        created.append(path)
        return path

    def fail_conformance(plan, repo):
        raise RuntimeError("injected conformance failure")

    monkeypatch.setattr(runner_module.tempfile, "mkdtemp", tracked_mkdtemp)
    monkeypatch.setattr(backend, "conformance", fail_conformance)

    with pytest.raises(RuntimeError, match="injected conformance failure"):
        CampaignRunner().run_trial(
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

    assert len(created) == 1
    assert not os.path.exists(created[0]), "trial workspace leaked after failure"


def test_container_is_destroyed_when_deploy_health_gate_fails():
    from certification.core.trial import TrialStage
    from certification.stages.execution_mode import ExecutionMode, StageExecution

    class Builder:
        def build(self, repo_dir, tag):
            return StageExecution(
                stage=TrialStage.BUILD, mode=ExecutionMode.REAL_DOCKER, passed=True,
                duration_s=0.01, logs_hash="build-log", image_digest="sha256:image",
            )

    class Tester:
        def run_tests(self, image, spec, repo_dir="", tag=""):
            return StageExecution(
                stage=TrialStage.TEST, mode=ExecutionMode.REAL_DOCKER, passed=True,
                duration_s=0.01, logs_hash="test-log",
            )

    class Deployer:
        def deploy(self, tag, port):
            return StageExecution(
                stage=TrialStage.DEPLOY, mode=ExecutionMode.REAL_DOCKER, passed=False,
                duration_s=0.01, logs_hash="deploy-log", container_id="container-created-before-health-failure",
                detail="health acceptance failed after container creation",
            )

    class Prober:
        def probe(self, port, container_id):
            assert container_id == "container-created-before-health-failure"
            return StageExecution(
                stage=TrialStage.RUNTIME, mode=ExecutionMode.REAL_DOCKER, passed=False,
                duration_s=0.01, logs_hash="probe-log", container_id=container_id,
            )

    class Destroyer:
        def __init__(self):
            self.destroyed = []

        def destroy(self, container_id):
            self.destroyed.append(container_id)
            return StageExecution(
                stage=TrialStage.DESTROY, mode=ExecutionMode.REAL_DOCKER, passed=True,
                duration_s=0.01, logs_hash="destroy-log", container_id=container_id,
            )

    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    backend = build_backend_registry().get("python-fastapi")
    destroyer = Destroyer()
    trial = CampaignRunner(
        builder=Builder(), tester=Tester(), deployer=Deployer(),
        prober=Prober(), destroyer=destroyer,
    ).run_trial(
        intent=workload.intent,
        category=workload.category.value,
        novelty_class="template",
        plan=artifacts.plan,
        revision_id=artifacts.revision.revision_id,
        backend=backend,
        requirement_graph_hash=artifacts.requirement_graph_hash,
        genome_hash=artifacts.genome_hash,
    )

    stages = {item.stage: item.passed for item in trial.stages}
    assert stages[TrialStage.DEPLOY] is False
    assert stages[TrialStage.DESTROY] is True
    assert destroyer.destroyed == ["container-created-before-health-failure"]
    assert trial.verdict == "NOT_CERTIFIED"
