"""
Tests for Phase 26.6 Learning Observability and Operational Dashboards.
"""

from types import SimpleNamespace

from learning.observability.engine import LearningObservabilityEngine
from learning.observability.models import (
    ObservabilityPolicy,
    OperationalStatus,
)
from learning.utils import utcnow


def build_engine(
    signal_count: int = 5,
    anomaly_count: int = 1,
    kill_switch_enabled: bool = False,
) -> LearningObservabilityEngine:
    now = utcnow().isoformat()

    signals = [
        SimpleNamespace(timestamp=now)
        for _ in range(signal_count)
    ]

    learning_engine = SimpleNamespace(
        pipeline=SimpleNamespace(signals=signals),
    )

    analytics_engine = SimpleNamespace(
        anomalies={
            f"anomaly_{index}": SimpleNamespace(id=f"anomaly_{index}")
            for index in range(anomaly_count)
        },
        clusters={
            "cluster_1": SimpleNamespace(
                id="cluster_1",
                confidence=0.8,
            ),
        },
        insights={
            "insight_1": SimpleNamespace(
                id="insight_1",
                confidence=0.9,
            ),
        },
    )

    integration_engine = SimpleNamespace(
        submissions={
            "bundle_1": SimpleNamespace(submission_id="submission_1"),
        },
        processed_insight_ids=set(),
        last_bundle_id="bundle_1",
    )

    governance_engine = SimpleNamespace(
        approvals={
            "approval_1": SimpleNamespace(status="PENDING"),
        },
        kill_switch=SimpleNamespace(enabled=kill_switch_enabled),
        safety_blocker_count=0,
        last_quality_score=0.8,
    )

    knowledge_sync_engine = SimpleNamespace(
        registry=SimpleNamespace(
            synced_signal_ids={"signal_1"},
            synced_anomaly_ids=set(),
            synced_cluster_ids={"cluster_1"},
            synced_insight_ids=set(),
            synced_objectives={"security_posture"},
        ),
    )

    return LearningObservabilityEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        integration_engine=integration_engine,
        governance_engine=governance_engine,
        knowledge_sync_engine=knowledge_sync_engine,
        policy=ObservabilityPolicy(),
    )


def test_metrics_snapshot():
    engine = build_engine()

    snapshot = engine.metrics_snapshot()

    assert snapshot.signal_count == 5
    assert snapshot.recent_signal_count == 5

    assert snapshot.anomaly_count == 1
    assert snapshot.cluster_count == 1
    assert snapshot.insight_count == 1

    assert snapshot.insight_backlog == 1

    assert snapshot.submission_count == 1
    assert snapshot.pending_approval_count == 1

    assert snapshot.kill_switch_enabled is False
    assert snapshot.safety_blocker_count == 0

    assert snapshot.average_cluster_confidence == 0.8
    assert snapshot.average_insight_confidence == 0.9

    assert snapshot.quality_score == 0.8

    assert snapshot.knowledge_sync_counts["synced_signals"] == 1
    assert snapshot.knowledge_sync_counts["synced_clusters"] == 1
    assert snapshot.knowledge_sync_counts["synced_objectives"] == 1


def test_operational_health_healthy():
    engine = build_engine()

    health = engine.operational_health()

    assert health.status == OperationalStatus.HEALTHY
    assert health.reasons == []


def test_kill_switch_degrades_health():
    engine = build_engine(kill_switch_enabled=True)

    health = engine.operational_health()

    assert health.status == OperationalStatus.DEGRADED
    assert "Learning kill switch is active." in health.reasons


def test_high_anomaly_rate_degrades_health():
    engine = build_engine(signal_count=10, anomaly_count=8)

    health = engine.operational_health()

    assert health.status == OperationalStatus.CRITICAL
    assert "Anomaly rate is critically high." in health.reasons


def test_dashboard_contains_core_panels():
    engine = build_engine()

    dashboard = engine.dashboard()

    assert dashboard.title == "Continuous Learning Operational Dashboard"
    assert dashboard.status == OperationalStatus.HEALTHY

    panel_titles = {panel.title for panel in dashboard.panels}

    assert "Learning Pipeline" in panel_titles
    assert "Anomaly Correlation" in panel_titles
    assert "Learning Insights" in panel_titles
    assert "Governance" in panel_titles
    assert "Evolution Feedback" in panel_titles
    assert "Knowledge Graph Sync" in panel_titles


def test_html_dashboard_render():
    engine = build_engine()

    dashboard = engine.dashboard()

    html_output = engine.render_dashboard_html(dashboard)

    assert "<html>" in html_output
    assert "Continuous Learning Operational Dashboard" in html_output
    assert "Learning Pipeline" in html_output
