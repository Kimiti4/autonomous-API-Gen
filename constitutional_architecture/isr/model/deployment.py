"""
ISR Deployment Model — infrastructure, scaling, networking, and monitoring.
Technology-neutral: no Kubernetes manifests, no Terraform configs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional


@unique
class ScalingStrategy(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    AUTO = "auto"
    NONE = "none"


@unique
class EnvironmentTier(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class ScalingConfig:
    strategy: ScalingStrategy = ScalingStrategy.AUTO
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0


@dataclass(frozen=True)
class NetworkingConfig:
    expose_publicly: bool = False
    internal_dns: str = ""
    tls_required: bool = True
    allowed_origins: tuple[str, ...] = ()
    port: int = 8080


@dataclass(frozen=True)
class MonitoringConfig:
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    structured_logging: bool = True
    alert_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class StorageConfig:
    persistent_storage_required: bool = False
    storage_size_gb: Optional[int] = None
    backup_enabled: bool = True
    encryption_at_rest: bool = True


@dataclass(frozen=True)
class SecretsConfig:
    secrets: tuple[str, ...] = ()
    rotation_policy_days: int = 90
    encryption_in_transit: bool = True


@dataclass(frozen=True)
class Deployment:
    id: str
    name: str
    description: str = ""
    environment: EnvironmentTier = EnvironmentTier.PRODUCTION
    scaling: ScalingConfig = field(default_factory=ScalingConfig)
    networking: NetworkingConfig = field(default_factory=NetworkingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    secrets: SecretsConfig = field(default_factory=SecretsConfig)
    metadata: dict[str, str] = field(default_factory=dict)