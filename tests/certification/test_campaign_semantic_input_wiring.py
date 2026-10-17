"""Campaign A wiring tests for real source-bound semantic verifier inputs."""
from certification.campaign.plan_builder import build_artifacts_for
from certification.corpus.corpus import default_corpus
from certification.campaign.runner import CampaignRunner
from compiler.composition import build_backend_registry
from app.engine.source_bound_full_stack import source_snapshot_from_plan_artifacts


def test_campaign_plan_artifacts_produce_canonical_source_snapshot():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = source_snapshot_from_plan_artifacts(artifacts)

    assert snapshot["schema"] == "source-bound-plan-snapshot/1"
    assert snapshot["source_refs"]
    assert snapshot["requirement_graph"]
    assert snapshot["revision"]
    assert snapshot["plan"]


def test_campaign_runner_verifies_complete_mapping_but_never_certifies_without_docker_stages():
    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    backend = build_backend_registry().get("python-fastapi")

    trial = CampaignRunner().run_trial(
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

    evidence = trial.semantic_correspondence
    assert evidence.get("source_hash"), "real Campaign A source snapshot was not bound"
    assert evidence.get("candidate_hash") == trial.repo_hash
    # The corpus declares its architecture, so the runner publishes the
    # explicit mapping and every source-bound verification axis passes
    # against the real generated candidate with zero findings.
    assert evidence.get("mapping_hash"), "complete mapping was not published"
    assert evidence.get("passed") is True, evidence.get("findings")
    assert evidence.get("findings") == []

    stages = {stage.stage.value: stage for stage in trial.stages}
    assert stages["structural"].passed
    assert stages["semantic"].passed
    assert stages["verify"].passed
    # This wiring harness supplies no real build/deploy stage adapters
    # (RealDockerStages provides them in Campaign A CI), so the trial must
    # still refuse to certify — evidence wiring alone never vacuously passes.
    assert not stages["build"].passed
    assert trial.verdict == "NOT_CERTIFIED"
