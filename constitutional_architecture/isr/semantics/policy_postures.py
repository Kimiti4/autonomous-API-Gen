"""First-class policy postures projected from typed SystemModel semantics."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InfrastructurePosture:
    topology: str
    stateful: bool
    scaling_unit: str
    availability: str

    def __post_init__(self) -> None:
        if self.topology not in {"single_service", "modular_monolith", "distributed_services", "event_driven", "hybrid"}:
            raise ValueError("unsupported infrastructure topology")
        if self.scaling_unit not in {"service", "instance", "partition"}:
            raise ValueError("unsupported scaling unit")
        if self.availability not in {"single_zone", "multi_zone", "multi_region"}:
            raise ValueError("unsupported availability posture")
        if not isinstance(self.stateful, bool):
            raise ValueError("stateful must be boolean")


@dataclass(frozen=True)
class DeploymentPosture:
    rollout_strategy: str
    environment_names: tuple[str, ...]
    scaling_policy: str
    zero_downtime_required: bool

    def __post_init__(self) -> None:
        if self.rollout_strategy not in {"all_at_once", "rolling", "blue_green", "canary"}:
            raise ValueError("unsupported rollout strategy")
        if any(not name.strip() for name in self.environment_names):
            raise ValueError("deployment environments must be explicit and non-empty")
        if self.scaling_policy not in {"static", "reactive", "predictive"}:
            raise ValueError("unsupported scaling policy")
        if not isinstance(self.zero_downtime_required, bool):
            raise ValueError("zero_downtime_required must be boolean")


@dataclass(frozen=True)
class TestingPosture:
    required_levels: tuple[str, ...]
    coverage_posture: str
    performance_required: bool
    security_required: bool

    def __post_init__(self) -> None:
        allowed_levels = {
            "unit", "integration", "end_to_end", "property_based",
            "performance", "security", "mutation",
        }
        if set(self.required_levels) - allowed_levels:
            raise ValueError("testing posture has missing or unsupported test levels")
        if self.coverage_posture not in {"none", "reported", "enforced"}:
            raise ValueError("unsupported coverage posture")
        if not isinstance(self.performance_required, bool) or not isinstance(self.security_required, bool):
            raise ValueError("testing requirements must be boolean")


@dataclass(frozen=True)
class DocumentationPosture:
    required_artifacts: tuple[str, ...]
    adr_required: bool

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.required_artifacts):
            raise ValueError("documentation artifacts must be explicit and non-empty")
        if not isinstance(self.adr_required, bool):
            raise ValueError("adr_required must be boolean")


@dataclass(frozen=True)
class OperationalSLO:
    name: str
    metric: str
    target: str

    def __post_init__(self) -> None:


@dataclass(frozen=True)
class OperationalPosture:
    service_level_objectives: tuple[OperationalSLO, ...]
    observability_requirements: tuple[str, ...]
    backup_posture: str
    disaster_recovery_posture: str
    incident_response_required: bool

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.observability_requirements):
            raise ValueError("observability requirements cannot be blank")
        if not isinstance(self.incident_response_required, bool):
            raise ValueError("incident_response_required must be boolean")
