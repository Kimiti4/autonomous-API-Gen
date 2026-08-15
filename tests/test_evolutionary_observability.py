"""
Tests for Phase 21.8 evolutionary observability, analytics, and auditing.
"""

from types import SimpleNamespace

from evolution.analytics import CampaignAnalyticsEngine
from evolution.governance_safety import EvolutionEvidence
from evolution.observability import (
    EvolutionEventType,
    EvolutionObservabilityBus,
)
from evolution.promotion import (
    PromotionControlEngine,
    StaticGovernanceGateway,
)
from evolution.promotion_audit import (
    AuditedPromotionEngine,
    PromotionAuditTrail,
)


def passing_evidence() -> EvolutionEvidence:
    return EvolutionEvidence(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        isr_content_hash="sha256:candidate",
        simulation_status="PASSED",
        verification_valid=True,
        fitness_passed=True,
        objectives={
            "simplicity": 0.8,
        },
        constraints={
            "simulation_passed": True,
        },
        compiler_passed=True,
        feedback_passed=True,
        critical_incident=False,
        critical_security_finding=False,
        pareto_selected=True,
        complexity=10.0,
        public_api_removed=False,
        breaking_changes_allowed=False,
        rollback_plan={
            "steps": [
                "Restore parent ISR.",
            ],
        },
    )


def test_observability_chain_and_metrics():
    bus = EvolutionObservabilityBus()

    bus.emit(
        EvolutionEventType.CAMPAIGN_CREATED,
        actor_id="tester",
        campaign_id="campaign_1",
        payload={
            "name": "Billing reliability campaign",
        },
    )

    bus.emit(
        EvolutionEventType.GENERATION_COMPLETED,
        actor_id="tester",
        campaign_id="campaign_1",
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        payload={
            "generation_index": 1,
        },
    )

    verification = bus.verify_chain()

    assert verification.valid is True
    assert verification.event_count == 2

    metrics = bus.metrics()

    assert metrics.total_events == 2
    assert metrics.campaign_count == 1
    assert metrics.events_by_type["CAMPAIGN_CREATED"] == 1
    assert metrics.events_by_type["GENERATION_COMPLETED"] == 1


def test_observability_chain_detects_tampering():
    bus = EvolutionObservabilityBus()

    bus.emit(
        EvolutionEventType.GENERATION_COMPLETED,
        actor_id="tester",
        campaign_id="campaign_1",
        proposal_id="proposal_1",
    )

    bus.emit(
        EvolutionEventType.PARETO_SELECTED,
        actor_id="tester",
        campaign_id="campaign_1",
        proposal_id="proposal_1",
        candidate_id="candidate_1",
    )

    bus.store.events[0].payload["tampered"] = True

    verification = bus.verify_chain()

    assert verification.valid is False
    assert verification.first_invalid_event_id == bus.store.events[0].id


def test_campaign_analytics_report():
    summaries = [
        SimpleNamespace(
            campaign_id="campaign_1",
            generation_index=1,
            proposal_id="proposal_1",
            genome_id="genome_1",
            selected_candidate_id="candidate_1",
            status="EVALUATED",
            objectives={
                "simplicity": 0.5,
                "modularity": 0.6,
            },
            constraints={},
            elite_count=1,
            created_at="2026-08-01T00:00:00Z",
        ),
        SimpleNamespace(
            campaign_id="campaign_1",
            generation_index=2,
            proposal_id="proposal_2",
            genome_id="genome_2",
            selected_candidate_id="candidate_2",
            status="APPROVED",
            objectives={
                "simplicity": 0.7,
                "modularity": 0.65,
            },
            constraints={},
            elite_count=2,
            created_at="2026-08-01T01:00:00Z",
        ),
    ]

    class FakeMemory:
        def list_generation_summaries(self, campaign_id):
            return summaries

        def list_elites(self, campaign_id):
            return [
                SimpleNamespace(candidate_id="candidate_1"),
                SimpleNamespace(candidate_id="candidate_2"),
            ]

        def get_trend(self, campaign_id):
            return None

    engine = CampaignAnalyticsEngine(memory=FakeMemory())

    report = engine.campaign_report("campaign_1")

    assert report.generation_count == 2
    assert report.feasible_generation_count == 2
    assert report.elite_count == 2

    assert report.objective_trends["simplicity"] == [0.5, 0.7]
    assert report.objective_trends["modularity"] == [0.6, 0.65]

    assert report.objective_deltas["simplicity"] == 0.2
    assert report.objective_deltas["modularity"] == 0.05

    assert report.objectives_improved == 2
    assert report.objectives_regressed == 0

    trend = engine.objective_trend("campaign_1", "simplicity")

    assert trend.points[0].value == 0.5
    assert trend.points[1].value == 0.7


def test_campaign_analytics_stagnation_detection():
    summaries = [
        SimpleNamespace(
            campaign_id="campaign_1",
            generation_index=1,
            proposal_id="proposal_1",
            genome_id="genome_1",
            selected_candidate_id="candidate_1",
            status="EVALUATED",
            objectives={"simplicity": 0.5},
            constraints={},
            elite_count=1,
            created_at="2026-08-01T00:00:00Z",
        ),
        SimpleNamespace(
            campaign_id="campaign_1",
            generation_index=2,
            proposal_id="proposal_2",
            genome_id="genome_2",
            selected_candidate_id="candidate_2",
            status="EVALUATED",
            objectives={"simplicity": 0.5},
            constraints={},
            elite_count=2,
            created_at="2026-08-01T01:00:00Z",
        ),
    ]

    class FakeMemory:
        def list_generation_summaries(self, campaign_id):
            return summaries

        def list_elites(self, campaign_id):
            return []

        def get_trend(self, campaign_id):
            return None

    engine = CampaignAnalyticsEngine(memory=FakeMemory())

    report = engine.campaign_report("campaign_1")

    assert report.stagnation_detected is True


def test_promotion_audit_trail_and_verification():
    inner_engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="ALLOW",
            reason="Allowed.",
        ),
    )

    audit_trail = PromotionAuditTrail()

    audited_engine = AuditedPromotionEngine(
        inner=inner_engine,
        audit_trail=audit_trail,
    )

    request = audited_engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    promoted = audited_engine.promote(request.id, "tester")

    assert promoted.status.value == "PROMOTED"

    rolled_back = audited_engine.rollback(
        request.id,
        "tester",
        "Test rollback.",
    )

    assert rolled_back.status.value == "ROLLED_BACK"

    events = audit_trail.list_events(request.id)

    assert len(events) >= 3

    verification = audit_trail.verify(request.id)

    assert verification.valid is True

    events[0].details["tampered"] = True

    tampered_verification = audit_trail.verify(request.id)

    assert tampered_verification.valid is False


def test_observability_metrics_count_promotion_events():
    bus = EvolutionObservabilityBus()

    for _ in range(3):
        bus.emit(
            EvolutionEventType.PROMOTION_PROMOTED,
            actor_id="tester",
            proposal_id="proposal_1",
            candidate_id="candidate_1",
        )

    bus.emit(
        EvolutionEventType.PROMOTION_ROLLED_BACK,
        actor_id="tester",
        proposal_id="proposal_1",
        candidate_id="candidate_1",
    )

    metrics = bus.metrics()

    assert metrics.promoted_count == 3
    assert metrics.rolled_back_count == 1
