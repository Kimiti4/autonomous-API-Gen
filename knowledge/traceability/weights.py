"""
Impact propagation profiles.

These profiles define how relation types propagate impact.

This is an explicit, replaceable rule set. Production systems may override
these profiles through governed configuration.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PropagationDirection(str, Enum):
    """Direction in which a relation propagates impact."""

    FORWARD = "forward"
    REVERSE = "reverse"
    BOTH = "both"


class ImpactRelationProfile(BaseModel):
    """Impact behavior for a relation type."""

    relation_type: str
    direction: PropagationDirection
    weight: float = Field(ge=0.0, le=1.0)
    reason: str


DEFAULT_IMPACT_PROFILES: dict[str, ImpactRelationProfile] = {
    "DEPENDS_ON": ImpactRelationProfile(
        relation_type="DEPENDS_ON",
        direction=PropagationDirection.REVERSE,
        weight=0.90,
        reason="A dependent entity is impacted when its dependency changes.",
    ),
    "CONSUMES": ImpactRelationProfile(
        relation_type="CONSUMES",
        direction=PropagationDirection.REVERSE,
        weight=0.80,
        reason="Consumers are impacted when consumed events or interfaces change.",
    ),
    "USES": ImpactRelationProfile(
        relation_type="USES",
        direction=PropagationDirection.REVERSE,
        weight=0.75,
        reason="Users of a data model, service, or interface are impacted when it changes.",
    ),
    "PRODUCES": ImpactRelationProfile(
        relation_type="PRODUCES",
        direction=PropagationDirection.FORWARD,
        weight=0.70,
        reason="Changes to a producer may impact produced artifacts or events.",
    ),
    "EXPOSES": ImpactRelationProfile(
        relation_type="EXPOSES",
        direction=PropagationDirection.FORWARD,
        weight=0.65,
        reason="Changes to a service may impact exposed APIs or interfaces.",
    ),
    "CONTAINS": ImpactRelationProfile(
        relation_type="CONTAINS",
        direction=PropagationDirection.BOTH,
        weight=0.60,
        reason="Contained and containing entities may mutually impact one another.",
    ),
    "DERIVES_FROM": ImpactRelationProfile(
        relation_type="DERIVES_FROM",
        direction=PropagationDirection.REVERSE,
        weight=0.85,
        reason="Derived entities are impacted when the source artifact changes.",
    ),
    "SATISFIES": ImpactRelationProfile(
        relation_type="SATISFIES",
        direction=PropagationDirection.REVERSE,
        weight=0.80,
        reason="Implementing entities are impacted when requirements change.",
    ),
    "IMPLEMENTS": ImpactRelationProfile(
        relation_type="IMPLEMENTS",
        direction=PropagationDirection.REVERSE,
        weight=0.80,
        reason="Implementations are impacted when capabilities or requirements change.",
    ),
    "DEPLOYED_AS": ImpactRelationProfile(
        relation_type="DEPLOYED_AS",
        direction=PropagationDirection.FORWARD,
        weight=0.85,
        reason="Artifact changes may impact deployments.",
    ),
    "MONITORED_BY": ImpactRelationProfile(
        relation_type="MONITORED_BY",
        direction=PropagationDirection.BOTH,
        weight=0.30,
        reason="Monitoring relationships are weak impact signals.",
    ),
    "CAUSED_BY": ImpactRelationProfile(
        relation_type="CAUSED_BY",
        direction=PropagationDirection.REVERSE,
        weight=0.90,
        reason="Incidents or observations may be impacted by their causes.",
    ),
    "IMPACTS": ImpactRelationProfile(
        relation_type="IMPACTS",
        direction=PropagationDirection.FORWARD,
        weight=0.85,
        reason="Explicit impact relation.",
    ),
    "AFFECTED_BY": ImpactRelationProfile(
        relation_type="AFFECTED_BY",
        direction=PropagationDirection.REVERSE,
        weight=0.85,
        reason="Entities affected by another entity propagate impact backward.",
    ),
}


FALLBACK_IMPACT_PROFILE = ImpactRelationProfile(
    relation_type="RELATED_TO",
    direction=PropagationDirection.BOTH,
    weight=0.10,
    reason="Generic relation with weak impact signal.",
)


def get_impact_profile(
    relation_type: str,
    profiles: Optional[dict[str, ImpactRelationProfile]] = None,
) -> ImpactRelationProfile:
    """Return the impact profile for a relation type."""

    active_profiles = profiles or DEFAULT_IMPACT_PROFILES

    return active_profiles.get(relation_type, FALLBACK_IMPACT_PROFILE)
