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
