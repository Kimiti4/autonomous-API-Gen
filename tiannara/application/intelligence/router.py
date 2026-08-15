"""Deterministic routing policy — policy as data, decisions auditable.

D3 extends the single locality ceiling into an explicit policy family.
Every policy is data: a name, a locality ceiling, and an ordering
objective. No conditional routing logic is scattered through AIR; the
cascade consults these values only.

The router performs no learning. A learned router would recreate the
dependency disease in a new form; it is a future audited evolution stage,
not the starting point.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.intelligence import LocalityLevel


class RoutingObjective(str, enum.Enum):
    LOCALITY_FIRST = "locality_first"   # deterministic-first (default)
    COST_MIN = "cost_min"
    LATENCY_MIN = "latency_min"
    QUALITY_MAX = "quality_max"


class RoutingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "custom"
    max_locality: LocalityLevel = LocalityLevel.L3_EXTERNAL_MODEL
    objective: RoutingObjective = RoutingObjective.LOCALITY_FIRST
    max_cascade_attempts: int = Field(default=4, ge=1)


# --- Policy family --------------------------------------------------------
# KEYLESS / OFFLINE / PRIVACY_MAX cap at L2: no external intelligence may be
# REQUIRED. They share the ceiling but differ in intent (recorded by name).
DEFAULT_POLICY = RoutingPolicy(
    name="default", max_locality=LocalityLevel.L3_EXTERNAL_MODEL
)
KEYLESS_POLICY = RoutingPolicy(
    name="keyless", max_locality=LocalityLevel.L2_LOCAL_MODEL
)
OFFLINE_POLICY = RoutingPolicy(
    name="offline", max_locality=LocalityLevel.L2_LOCAL_MODEL
)
PRIVACY_MAX_POLICY = RoutingPolicy(
    name="privacy_max", max_locality=LocalityLevel.L2_LOCAL_MODEL
)
COST_MIN_POLICY = RoutingPolicy(
    name="cost_min", max_locality=LocalityLevel.L3_EXTERNAL_MODEL,
    objective=RoutingObjective.COST_MIN,
)
LATENCY_MIN_POLICY = RoutingPolicy(
    name="latency_min", max_locality=LocalityLevel.L3_EXTERNAL_MODEL,
    objective=RoutingObjective.LATENCY_MIN,
)
QUALITY_MAX_POLICY = RoutingPolicy(
    name="quality_max", max_locality=LocalityLevel.L3_EXTERNAL_MODEL,
    objective=RoutingObjective.QUALITY_MAX,
)


def order_candidates(candidates: Any, policy: RoutingPolicy) -> list:
    """Order capability-matched candidates per the policy objective.

    LOCALITY_FIRST preserves deterministic-first order. Other objectives
    reorder by declared profile, with locality then provider id as
    deterministic tie-breakers.
    """
    if policy.objective is RoutingObjective.LOCALITY_FIRST:
        return sorted(
            candidates,
            key=lambda p: (p.declaration.locality.value, p.declaration.provider_id),
        )
    if policy.objective is RoutingObjective.COST_MIN:
        return sorted(
            candidates,
            key=lambda p: (
                p.declaration.cost_profile,
                p.declaration.locality.value,
                p.declaration.provider_id,
            ),
        )
    if policy.objective is RoutingObjective.LATENCY_MIN:
        return sorted(
            candidates,
            key=lambda p: (
                p.declaration.latency_profile,
                p.declaration.locality.value,
                p.declaration.provider_id,
            ),
        )
    return sorted(  # QUALITY_MAX: higher quality first
        candidates,
        key=lambda p: (
            -p.declaration.quality_profile,
            p.declaration.locality.value,
            p.declaration.provider_id,
        ),
    )
