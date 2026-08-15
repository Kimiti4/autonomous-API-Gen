"""
Tests for governance integration behavior.
"""

from knowledge.audit import LoggingAuditEmitter
from knowledge.governance import GovernanceDecision
from knowledge.recommendation import RecommendationEngine


class StubGovernanceClient:
    def __init__(self, decision: str) -> None:
        self._decision = decision

    def evaluate(self, request):
        return GovernanceDecision(
            decision=self._decision,
            reason="stub decision",
        )


def test_recommendation_submission_allowed() -> None:
    engine = RecommendationEngine(
        governance_client=StubGovernanceClient("ALLOW"),
        audit_emitter=LoggingAuditEmitter(),
    )

    recommendation = engine.draft_recommendation(
        actor_id="tester",
        recommendation_type="ARCHITECTURE_IMPROVEMENT",
        title="Add billing retry policy",
        description="Evidence suggests transient billing failures.",
        suggested_action="Create governed evolution proposal.",
        evidence_refs=["evidence:incident:1"],
        source_entity_ids=["entity_1"],
    )

    decision = engine.submit_to_governance(
        recommendation=recommendation,
        actor_id="tester",
        actor_roles=["knowledge_writer"],
    )

    assert decision.decision == "ALLOW"


def test_recommendation_submission_denied() -> None:
    engine = RecommendationEngine(
        governance_client=StubGovernanceClient("DENY"),
        audit_emitter=LoggingAuditEmitter(),
    )

    recommendation = engine.draft_recommendation(
        actor_id="tester",
        recommendation_type="ARCHITECTURE_IMPROVEMENT",
        title="Denied recommendation",
        description="This should be denied.",
        suggested_action="Do something governed.",
        evidence_refs=[],
        source_entity_ids=[],
    )

    try:
        engine.submit_to_governance(
            recommendation=recommendation,
            actor_id="tester",
        )
        assert False, "Expected denial"
    except Exception as exc:
        assert "denied" in str(exc).lower()
