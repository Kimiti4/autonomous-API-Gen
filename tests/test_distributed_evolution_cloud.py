"""
Tests for Phase 29 — Distributed Evolution Cloud.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from distributed_evolution.api import enable_distributed_evolution
from distributed_evolution.engine import DistributedEvolutionCloudEngine
from distributed_evolution.models import CampaignStatus, JobStatus


def build_engine() -> DistributedEvolutionCloudEngine:
    engine = DistributedEvolutionCloudEngine(
        cluster_policy_version="constitution.v1",
    )

    engine.autoscale_threshold = 100

    return engine


def register_node(engine: DistributedEvolutionCloudEngine, node_id: str):
    engine.register_node(
        node_id=node_id,
        region="us-east-1",
        capabilities=[],
        cpu_capacity=4,
        memory_mb_capacity=4096,
        policy_version="constitution.v1",
        public_key_ref=f"key:{node_id}",
    )


def test_campaign_completes_with_artifacts():
    engine = build_engine()

    register_node(engine, "node_a")

    campaign = engine.submit_campaign(
        name="campaign_1",
        objective="Evolve billing architecture candidates.",
        candidate_count=2,
        target_backends=["fastapi"],
    )

    completed = engine.run_campaign(campaign.campaign_id)

    assert completed.status == CampaignStatus.COMPLETED

    jobs = engine._campaign_jobs(campaign.campaign_id)

    assert len(jobs) == 4

    assert all(job.status == JobStatus.COMPLETED for job in jobs)

    metrics = engine.metrics()

    assert metrics.completed_jobs == 4
    assert metrics.artifacts_count == 4
    assert engine.verify_audit_chain() is True


def test_unattested_node_is_not_scheduled():
    engine = build_engine()

    engine.register_node(
        node_id="node_bad",
        region="us-east-1",
        capabilities=[],
        cpu_capacity=4,
        memory_mb_capacity=4096,
        policy_version="wrong-policy",
        public_key_ref="key:node_bad",
    )

    campaign = engine.submit_campaign(
        name="campaign_bad_node",
        objective="Should not schedule on unattested node.",
        candidate_count=1,
    )

    scheduled = engine.schedule_campaign(campaign.campaign_id)

    assert scheduled == []

    assert campaign.status == CampaignStatus.PENDING


def test_node_failure_recovery():
    engine = build_engine()

    register_node(engine, "node_a")

    campaign = engine.submit_campaign(
        name="campaign_failure",
        objective="Recover from node failure.",
        candidate_count=2,
    )

    engine.schedule_campaign(campaign.campaign_id)

    recovered_jobs = engine.fail_node("node_a")

    assert len(recovered_jobs) > 0

    register_node(engine, "node_b")

    completed = engine.run_campaign(campaign.campaign_id)

    assert completed.status == CampaignStatus.COMPLETED

    jobs = engine._campaign_jobs(campaign.campaign_id)

    assert all(job.status == JobStatus.COMPLETED for job in jobs)

    assert engine.verify_audit_chain() is True


def test_autoscaling_adds_nodes():
    engine = DistributedEvolutionCloudEngine(
        cluster_policy_version="constitution.v1",
    )

    engine.autoscale_threshold = 2

    campaign = engine.submit_campaign(
        name="campaign_autoscale",
        objective="Autoscale when queue is large.",
        candidate_count=4,
    )

    completed = engine.run_campaign(campaign.campaign_id)

    assert completed.status == CampaignStatus.COMPLETED

    assert len(engine.resource_manager.nodes) >= 1


def test_artifact_integrity():
    engine = build_engine()

    register_node(engine, "node_a")

    campaign = engine.submit_campaign(
        name="campaign_artifacts",
        objective="Produce verifiable artifacts.",
        candidate_count=1,
    )

    engine.run_campaign(campaign.campaign_id)

    artifacts = engine.artifacts.list_artifacts()

    assert len(artifacts) == 2

    for artifact in artifacts:
        assert engine.verify_artifact(artifact.content_hash) is True

    assert engine.verify_artifact("missing_hash") is False


def test_api_campaign_lifecycle():
    app = FastAPI()

    enable_distributed_evolution(app)

    client = TestClient(app)

    register_response = client.post(
        "/v1/distributed-evolution/nodes",
        json={
            "node_id": "node_api",
            "region": "us-east-1",
            "capabilities": [],
            "cpu_capacity": 4,
            "memory_mb_capacity": 4096,
            "policy_version": "constitution.v1",
            "public_key_ref": "key:node_api",
        },
    )

    assert register_response.status_code == 201

    campaign_response = client.post(
        "/v1/distributed-evolution/campaigns",
        json={
            "name": "api_campaign",
            "objective": "Run API campaign.",
            "candidate_count": 1,
            "target_backends": [],
        },
    )

    assert campaign_response.status_code == 201

    campaign_id = campaign_response.json()["campaign_id"]

    run_response = client.post(
        f"/v1/distributed-evolution/campaigns/{campaign_id}/run"
    )

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "COMPLETED"

    metrics_response = client.get("/v1/distributed-evolution/metrics")

    assert metrics_response.status_code == 200
    assert metrics_response.json()["completed_jobs"] == 2

    audit_response = client.post("/v1/distributed-evolution/audit/verify")

    assert audit_response.status_code == 200
    assert audit_response.json()["valid"] is True
