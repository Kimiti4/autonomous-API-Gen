"""Tests for Phase 26.7 — Learning Pipeline Hardening and Production Certification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from learning.certification import (
    CertificationStatus,
    GateStatus,
    LearningPipelineCertificationEngine,
    LearningPipelineCertificationPolicy,
    enable_learning_pipeline_certification,
)
from learning.models import LearningInsight
from learning.observability.models import OperationalHealth, OperationalStatus


@dataclass
class FakeKillSwitch:
    enabled: bool = False


@dataclass
class FakeGovernanceEngine:
    kill_switch_enabled: bool = False
    safety_blocker_count: int = 0

    @property
    def kill_switch(self) -> FakeKillSwitch:
        return FakeKillSwitch(enabled=self.kill_switch_enabled)


@dataclass
class FakeKnowledgeRegistry:
    synced_insight_ids: set


@dataclass
class FakeKnowledgeSyncEngine:
    synced: int = 0

    @property
    def registry(self) -> FakeKnowledgeRegistry:
        return FakeKnowledgeRegistry(synced_insight_ids={f"insight_{i}" for i in range(self.synced)})


@dataclass
class FakeObservabilityEngine:
    signal_count: int = 5
    recent_signal_count: int = 3
    anomaly_count: int = 0
    pending_approval_count: int = 0
    operational_status: OperationalStatus = OperationalStatus.HEALTHY

    def metrics_snapshot(self):
        from learning.observability.models import LearningMetricsSnapshot

        return LearningMetricsSnapshot(
            signal_count=self.signal_count,
            recent_signal_count=self.recent_signal_count,
            anomaly_count=self.anomaly_count,
            pending_approval_count=self.pending_approval_count,
        )

    def operational_health(self):
        return OperationalHealth(status=self.operational_status)


@dataclass
class FakeAnalyticsEngine:
    insights: dict


def _healthy_engine(evidence_refs: Optional[List[str]] = None) -> LearningPipelineCertificationEngine:
    return LearningPipelineCertificationEngine(
        analytics_engine=FakeAnalyticsEngine(
            insights={"i1": LearningInsight(id="i1", title="t", description="d", confidence=0.85)}
        ),
        governance_engine=FakeGovernanceEngine(kill_switch_enabled=False, safety_blocker_count=0),
        observability_engine=FakeObservabilityEngine(),
        knowledge_sync_engine=FakeKnowledgeSyncEngine(synced=0),
        policy=LearningPipelineCertificationPolicy(require_human_certification=True),
    )


# ---------------------------------------------------------------------------
# Acceptance criteria
# ---------------------------------------------------------------------------


def test_certification_policy_defaults():
    policy = LearningPipelineCertificationPolicy()
    assert policy.min_signal_count == 1
    assert policy.max_anomaly_rate == 0.60
    assert policy.min_evidence_confidence == 0.50
    assert policy.require_human_certification is True
    assert policy.certification_ttl_days == 90


def test_certify_empty_pipeline_is_not_certified():
    engine = LearningPipelineCertificationEngine()
    report = engine.certify()
    assert report.status == CertificationStatus.NOT_CERTIFIED
    signal_gate = next(g for g in report.gates if g.gate == "signal_ingestion")
    assert signal_gate.status == GateStatus.FAIL
    assert any("failed" in r.lower() for r in report.reasons)


def test_full_healthy_pipeline_is_certified():
    engine = _healthy_engine(evidence_refs=["slo:latency:99p", "runbook:oncall"])
    report = engine.certify(certified_by="human", evidence_refs=["slo:latency:99p", "runbook:oncall"])
    assert report.status == CertificationStatus.CERTIFIED
    assert all(gate.status == GateStatus.PASS for gate in report.gates)
    assert report.expires_at is not None


def test_production_readiness_missing_yields_conditional():
    engine = _healthy_engine()
    report = engine.certify(certified_by="human")
    assert report.status == CertificationStatus.CONDITIONALLY_CERTIFIED
    readiness = next(g for g in report.gates if g.gate == "production_readiness")
    assert readiness.status == GateStatus.WARNING


def test_human_certification_is_enforced():
    engine = _healthy_engine(evidence_refs=["slo:latency:99p"])
    report = engine.certify(certified_by="system", evidence_refs=["slo:latency:99p"])
    assert report.status == CertificationStatus.CONDITIONALLY_CERTIFIED
    assert any("Human certification is required" in r for r in report.reasons)


def test_high_anomaly_rate_fails_certification():
    engine = LearningPipelineCertificationEngine(
        analytics_engine=FakeAnalyticsEngine(
            insights={"i1": LearningInsight(id="i1", title="t", description="d", confidence=0.85)}
        ),
        governance_engine=FakeGovernanceEngine(),
        observability_engine=FakeObservabilityEngine(
            signal_count=10, anomaly_count=9, recent_signal_count=3
        ),
        policy=LearningPipelineCertificationPolicy(),
    )
    report = engine.certify(certified_by="human", evidence_refs=["slo:ev1"])
    anomaly_gate = next(g for g in report.gates if g.gate == "anomaly_rate")
    assert anomaly_gate.status == GateStatus.FAIL
    assert report.status == CertificationStatus.NOT_CERTIFIED


def test_kill_switch_active_fails_certification():
    engine = LearningPipelineCertificationEngine(
        analytics_engine=FakeAnalyticsEngine(
            insights={"i1": LearningInsight(id="i1", title="t", description="d", confidence=0.9)}
        ),
        governance_engine=FakeGovernanceEngine(kill_switch_enabled=True),
        observability_engine=FakeObservabilityEngine(),
        policy=LearningPipelineCertificationPolicy(),
    )
    report = engine.certify(certified_by="human", evidence_refs=["slo:ev1"])
    safety_gate = next(g for g in report.gates if g.gate == "safety_controls")
    assert safety_gate.status == GateStatus.FAIL
    assert report.status == CertificationStatus.NOT_CERTIFIED


def test_certification_can_be_revoked():
    engine = _healthy_engine(evidence_refs=["slo:ev1"])
    report = engine.certify(certified_by="human", evidence_refs=["slo:ev1"])
    revoked = engine.revoke(report_id=report.id, reason="policy violation", revoked_by="human")
    assert revoked.status == CertificationStatus.REVOKED
    assert revoked.revoked_at is not None
    assert revoked.revocation_reason == "policy violation"
    assert engine.report(report.id).status == CertificationStatus.REVOKED


def test_certification_expiry_is_set_within_ttl():
    policy = LearningPipelineCertificationPolicy(certification_ttl_days=90)
    engine = _healthy_engine()
    engine.policy = policy
    report = engine.certify(certified_by="human", evidence_refs=["evidence:runbook"])
    assert report.expires_at is not None
    delta = report.expires_at - report.created_at
    assert timedelta(days=89) <= delta <= timedelta(days=90)


def test_latest_and_missing_report_raises():
    engine = LearningPipelineCertificationEngine()
    with pytest.raises(KeyError):
        engine.report("missing-id")
    assert engine.latest_report() is None


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def _certified_app():
    app = FastAPI()
    enable_learning_pipeline_certification(
        app,
        analytics_engine=FakeAnalyticsEngine(
            insights={"i1": LearningInsight(id="i1", title="t", description="d", confidence=0.9)}
        ),
        governance_engine=FakeGovernanceEngine(),
        observability_engine=FakeObservabilityEngine(),
        knowledge_sync_engine=FakeKnowledgeSyncEngine(synced=1),
    )
    return app


@pytest.fixture
def certified_app():
    return _certified_app()


def test_api_certify_latest_revoke():
    client = TestClient(_certified_app())

    response = client.post("/v1/learning/certification/certify", json={"certified_by": "human", "evidence_refs": ["slo:99p"]})
    assert response.status_code == 201
    report_id = response.json()["id"]
    assert response.json()["status"] == "CERTIFIED"

    latest = client.get("/v1/learning/certification/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == report_id

    fetched = client.get(f"/v1/learning/certification/report/{report_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "CERTIFIED"

    revoked = client.post(
        f"/v1/learning/certification/report/{report_id}/revoke",
        json={"reason": "manual review", "revoked_by": "human"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"


def _empty_app() -> FastAPI:
    app = FastAPI()
    enable_learning_pipeline_certification(app)
    return app


def test_api_latest_missing_when_none_reported():
    client = TestClient(_empty_app())
    resp = client.get("/v1/learning/certification/latest")
    assert resp.status_code == 404
    missing = client.get("/v1/learning/certification/report/none")
    assert missing.status_code == 404


def test_api_revoke_missing_report_returns_404():
    client = TestClient(_empty_app())
    response = client.post(
        "/v1/learning/certification/report/missing/revoke",
        json={"reason": "x"},
    )
    assert response.status_code == 404
