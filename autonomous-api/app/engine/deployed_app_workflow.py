"""Professional workflow contract for maintaining, enhancing, or repairing deployed apps.

This layer governs intake and deployment boundaries; it does not grant production
credentials or bypass the existing ESAP transaction/admission system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeployedWorkIntent(str, Enum):
    BUG_FIX = "bug_fix"
    MAINTAIN = "maintain"
    ENHANCE = "enhance"


@dataclass(frozen=True)
class DeploymentAccess:
    repository_access: bool
    runtime_observation_access: bool
    deployment_access: bool = False
    production_write_authorized: bool = False


@dataclass(frozen=True)
class DeploymentBaseline:
    source_revision: str
    environment_fingerprint: str
    health_evidence: tuple[str, ...]
    rollback_reference: str


@dataclass(frozen=True)
class DeployedAppWorkPlan:
    intent: DeployedWorkIntent
    target: str
    baseline: DeploymentBaseline
    access: DeploymentAccess
    required_stages: tuple[str, ...]


def plan_deployed_app_work(
    intent: DeployedWorkIntent,
    *,
    target: str,
    access: DeploymentAccess,
    baseline: DeploymentBaseline,
) -> DeployedAppWorkPlan:
    if not target:
        raise ValueError("missing-deployed-app-target")
    if not access.repository_access:
        raise ValueError("missing-repository-access")
    if not access.runtime_observation_access:
        raise ValueError("missing-runtime-observation-access")
    if not baseline.source_revision or not baseline.environment_fingerprint:
        raise ValueError("missing-deployment-baseline")
    if not baseline.health_evidence:
        raise ValueError("missing-baseline-health-evidence")
    stages = (
        "intake",
        "repository-scan",
        "impact-analysis",
        "reproduce-or-establish-baseline",
        "governed-change",
        "verification",
        "staging-or-isolated-validation",
        "deployment-readiness",
        "post-deployment-observation",
    )
    if access.production_write_authorized:
        if not access.deployment_access:
            raise ValueError("production-write-requires-deployment-access")
        stages = stages + ("human-authorized-production-deployment", "rollback-readiness-check")
    else:
        stages = stages + ("human-authorization-required-before-production-deployment",)
    return DeployedAppWorkPlan(intent, target, baseline, access, stages)
