from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Optional


@unique
class DeploymentStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    PACKAGING = "packaging"
    CONTAINERIZING = "containerizing"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    HEALTH_CHECK = "health_check"
    RUNNING = "running"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value

    @property
    def is_terminal(self) -> bool:
        return self in {
            DeploymentStatus.RUNNING,
            DeploymentStatus.ROLLED_BACK,
            DeploymentStatus.FAILED,
            DeploymentStatus.CANCELLED,
        }

    @property
    def is_successful(self) -> bool:
        return self == DeploymentStatus.RUNNING


@unique
class RolloutStrategy(str, Enum):
    IMMEDIATE = "immediate"
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RollbackPlan:
    deployment_id: str
    previous_version: str = ""
    rollback_strategy: str = "restore_previous"
    estimated_rollback_seconds: float = 30.0
    max_rollback_seconds: float = 120.0
    requires_recompilation: bool = False
    rollback_artifacts_cached: bool = True
    verified: bool = False
    verification_timestamp: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        return (
            self.verified
            and not self.requires_recompilation
            and self.rollback_artifacts_cached
        )


@dataclass(frozen=True)
class DeploymentArtifact:
    artifact_type: str
    name: str
    location: str
    checksum: str = ""
    size_bytes: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthCheckResult:
    endpoint: str
    status: str
    response_time_ms: float = 0.0
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class DeploymentResult:
    deployment_id: str = ""
    isr_hash: str = ""
    verification_report_id: str = ""
    compilation_result_hash: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    environment: str = ""
    target: str = ""
    rollout_strategy: RolloutStrategy = RolloutStrategy.IMMEDIATE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    build_artifacts: tuple[DeploymentArtifact, ...] = ()
    container_images: tuple[DeploymentArtifact, ...] = ()
    infrastructure_artifacts: tuple[DeploymentArtifact, ...] = ()
    rollback_plan: Optional[RollbackPlan] = None
    rollback_executed: bool = False
    rollback_reason: str = ""
    health_checks: tuple[HealthCheckResult, ...] = ()
    is_healthy: bool = False
    version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    events: tuple[dict[str, Any], ...] = ()

    @property
    def is_successful(self) -> bool:
        return self.status.is_successful and self.is_healthy

    @property
    def has_rollback_plan(self) -> bool:
        return self.rollback_plan is not None and self.rollback_plan.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "isr_hash": self.isr_hash,
            "status": self.status.value,
            "environment": self.environment,
            "target": self.target,
            "duration_seconds": self.duration_seconds,
            "is_healthy": self.is_healthy,
            "has_rollback_plan": self.has_rollback_plan,
            "version": self.version,
        }
