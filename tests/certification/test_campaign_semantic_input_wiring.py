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


def test_campaign_runner_records_real_source_and_candidate_evidence_but_blocks_missing_mapping():
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
    assert evidence.get("passed") is False
    assert any("explicit_mapping is missing" in finding for finding in evidence.get("findings", ()))
    assert trial.verdict == "NOT_CERTIFIED"
