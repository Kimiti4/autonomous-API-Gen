"""
Knowledge Graph recommendation engine.

The Knowledge Graph may generate recommendations, but it must not execute
them.

Actionable recommendations must be submitted to the Governance Kernel.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .audit import AuditEmitter, AuditEvent
from .errors import KnowledgeGraphError
from .governance import GovernanceClient, GovernanceEvaluationRequest, GovernanceDecision
from .ids import deterministic_id
from .models import utcnow


class KnowledgeRecommendation(BaseModel):
    """A recommendation generated from Knowledge Graph evidence."""

    id: str
    recommendation_type: str
    title: str
    description: str
    evidence_refs: list[str] = Field(default_factory=list)
    source_entity_ids: list[str] = Field(default_factory=list)
    suggested_action: str
    risk_level: str = "MEDIUM"
    governance_status: str = "DRAFT"
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class RecommendationEngine:
    """
    Generates and submits Knowledge Graph recommendations.

    This engine does not execute actions.
    """

    def __init__(
        self,
        governance_client: GovernanceClient,
        audit_emitter: AuditEmitter,
    ) -> None:
        self._governance_client = governance_client
        self._audit_emitter = audit_emitter

    def draft_recommendation(
        self,
        actor_id: str,
        recommendation_type: str,
        title: str,
        description: str,
        suggested_action: str,
        evidence_refs: list[str],
        source_entity_ids: list[str],
        risk_level: str = "MEDIUM",
    ) -> KnowledgeRecommendation:
        recommendation_id = deterministic_id(
            "recommendation",
            {
                "recommendation_type": recommendation_type,
                "title": title,
                "description": description,
                "suggested_action": suggested_action,
                "evidence_refs": sorted(evidence_refs),
                "source_entity_ids": sorted(source_entity_ids),
            },
        )

        recommendation = KnowledgeRecommendation(
            id=recommendation_id,
            recommendation_type=recommendation_type,
            title=title,
            description=description,
            evidence_refs=evidence_refs,
            source_entity_ids=source_entity_ids,
            suggested_action=suggested_action,
            risk_level=risk_level,
        )

        self._audit_emitter.emit(
            AuditEvent(
                event_type="RECOMMENDATION_DRAFTED",
                actor_id=actor_id,
                subject_type="RECOMMENDATION",
                subject_id=recommendation.id,
                action="DRAFT",
                payload=recommendation.model_dump(mode="json"),
            )
        )

        return recommendation

    def submit_to_governance(
        self,
        recommendation: KnowledgeRecommendation,
        actor_id: str,
        actor_roles: list[str] | None = None,
    ) -> GovernanceDecision:
        request = GovernanceEvaluationRequest(
            subject_type="RECOMMENDATION",
            subject_id=recommendation.id,
            action="SUBMIT_RECOMMENDATION",
            actor={
                "actor_type": "HUMAN",
                "actor_id": actor_id,
                "roles": actor_roles or [],
                "delegated_authority": [],
            },
            context={
                "recommendation_type": recommendation.recommendation_type,
                "risk_level": recommendation.risk_level,
                "suggested_action": recommendation.suggested_action,
            },
            evidence_refs=recommendation.evidence_refs,
        )

        decision = self._governance_client.evaluate(request)

        self._audit_emitter.emit(
            AuditEvent(
                event_type="RECOMMENDATION_SUBMITTED",
                actor_id=actor_id,
                subject_type="RECOMMENDATION",
                subject_id=recommendation.id,
                action="SUBMIT_TO_GOVERNANCE",
                payload={
                    "recommendation": recommendation.model_dump(mode="json"),
                    "decision": decision.model_dump(mode="json"),
                },
            )
        )

        if decision.decision == "DENY":
            raise KnowledgeGraphError(
                f"Recommendation submission denied: {decision.reason}"
            )

        return decision
