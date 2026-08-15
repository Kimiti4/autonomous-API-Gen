"""Autonomy certification.

Makes `external_api_key_required == False` a runtime-provable fact derived
from the provider registry and the routing policy — not a fixture
assumption. Under a keyless/offline policy the locality ceiling is below
L3, so external dependence is structurally impossible. When the ceiling
permits L3, we check whether every required task still has a non-external
provider.

The first measured audit sets the status thresholds (provisional until
ratified); this module produces the ratios, not the final status.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tiannara.domain.models.intelligence import LocalityLevel, TaskKind

from .registry import ProviderRegistry
from .router import RoutingPolicy


class AutonomyCertification(BaseModel):
    external_api_key_required: bool
    policy_name: str
    max_locality: LocalityLevel
    per_task_coverage: dict[str, bool] = Field(default_factory=dict)
    detail: list[str] = Field(default_factory=list)


def certify_no_external_dependency(
    registry: ProviderRegistry,
    policy: RoutingPolicy,
    required_task_kinds: list[TaskKind],
) -> AutonomyCertification:
    l3 = LocalityLevel.L3_EXTERNAL_MODEL
    per_task: dict[str, bool] = {}
    detail: list[str] = []
    for kind in required_task_kinds:
        providers = [
            p for p in registry.providers() if kind in p.declaration.task_kinds
        ]
        non_external = [p for p in providers if p.declaration.locality < l3]
        per_task[kind.value] = len(non_external) > 0
        if not non_external:
            detail.append(f"task '{kind.value}' has no non-external provider")

    if policy.max_locality < l3:
        external_required = False
        detail.append(
            f"policy '{policy.name}' caps locality at {policy.max_locality.name}; "
            "external intelligence is structurally unreachable"
        )
    else:
        external_required = not all(per_task.values())

    return AutonomyCertification(
        external_api_key_required=external_required,
        policy_name=policy.name,
        max_locality=policy.max_locality,
        per_task_coverage=per_task,
        detail=detail,
    )
