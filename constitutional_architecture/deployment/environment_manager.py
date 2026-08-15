from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import Optional

from constitutional_architecture.verification.verification_result import VerificationLevel


@unique
class EnvironmentTier(IntEnum):
    DEVELOPMENT = 0
    SANDBOX = 1
    STAGING = 2
    PRODUCTION = 3

    def __str__(self) -> str:
        return self.name

    @property
    def required_verification_level(self) -> VerificationLevel:
        mapping = {
            EnvironmentTier.DEVELOPMENT: VerificationLevel.L1_STATIC,
            EnvironmentTier.SANDBOX: VerificationLevel.L4_PERFORMANCE,
            EnvironmentTier.STAGING: VerificationLevel.L5_OPERATIONAL,
            EnvironmentTier.PRODUCTION: VerificationLevel.L5_OPERATIONAL,
        }
        return mapping[self]

    @property
    def description(self) -> str:
        descriptions = {
            EnvironmentTier.DEVELOPMENT: "Local development environment",
            EnvironmentTier.SANDBOX: "Isolated sandbox for performance testing",
            EnvironmentTier.STAGING: "Pre-production staging environment",
            EnvironmentTier.PRODUCTION: "Live production environment",
        }
        return descriptions[self]

    @property
    def requires_rollback_plan(self) -> bool:
        return self >= EnvironmentTier.STAGING

    @property
    def requires_health_check(self) -> bool:
        return self >= EnvironmentTier.SANDBOX


@dataclass(frozen=True)
class EnvironmentConfig:
    tier: EnvironmentTier
    name: str = ""
    endpoint: str = ""
    credentials_ref: str = ""
    max_instances: int = 1
    auto_scaling: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


class EnvironmentManager:
    def __init__(self) -> None:
        self._environments: dict[EnvironmentTier, EnvironmentConfig] = {}
        self._deployment_history: dict[str, list[EnvironmentTier]] = {}

    def register_environment(self, config: EnvironmentConfig) -> None:
        self._environments[config.tier] = config

    def get_environment(self, tier: EnvironmentTier) -> Optional[EnvironmentConfig]:
        return self._environments.get(tier)

    def can_promote(
        self,
        deployment_id: str,
        from_tier: EnvironmentTier,
        to_tier: EnvironmentTier,
        verification_level_achieved: VerificationLevel,
    ) -> tuple[bool, str]:
        if to_tier.value != from_tier.value + 1:
            return False, f"Cannot skip environments: {from_tier.name} -> {to_tier.name}"

        required = to_tier.required_verification_level
        if verification_level_achieved < required:
            return False, (
                f"Verification level {verification_level_achieved.name} "
                f"below required {required.name} for {to_tier.name}"
            )

        return True, f"Promotion {from_tier.name} -> {to_tier.name} allowed"

    def record_promotion(self, deployment_id: str, tier: EnvironmentTier) -> None:
        self._deployment_history.setdefault(deployment_id, []).append(tier)

    def get_current_tier(self, deployment_id: str) -> Optional[EnvironmentTier]:
        history = self._deployment_history.get(deployment_id, [])
        if not history:
            return None
        return history[-1]

    @property
    def registered_environments(self) -> list[EnvironmentTier]:
        return sorted(self._environments.keys())
