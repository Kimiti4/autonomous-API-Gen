from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType


class PromotionEnvironment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class PromotionConfig:
    require_verification: bool = True
    require_approval: bool = False
    auto_promote: bool = False
    allowed_jumps: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class PromotionManager:
    def __init__(self, config: PromotionConfig | None = None) -> None:
        self._config = config or PromotionConfig()
        self._promotions: list[dict[str, Any]] = []
        self._promotion_order = [
            PromotionEnvironment.DEVELOPMENT,
            PromotionEnvironment.STAGING,
            PromotionEnvironment.PRODUCTION,
        ]

    def promote(
        self,
        artifact_version: str,
        from_env: PromotionEnvironment,
        to_env: PromotionEnvironment,
    ) -> bool:
        from_idx = self._promotion_order.index(from_env)
        to_idx = self._promotion_order.index(to_env)

        jump = to_idx - from_idx
        if jump > self._config.allowed_jumps:
            return False

        if self._config.require_approval and to_env == PromotionEnvironment.PRODUCTION:
            DeploymentEvent.emit(
                DeploymentEventType.PROMOTION_BLOCKED,
                {"from": from_env.value, "to": to_env.value, "reason": "awaiting_approval"},
            )
            return False

        self._promotions.append({
            "version": artifact_version,
            "from": from_env.value,
            "to": to_env.value,
        })

        DeploymentEvent.emit(
            DeploymentEventType.PROMOTION_COMPLETED,
            {"from": from_env.value, "to": to_env.value, "version": artifact_version},
        )
        return True

    def get_promotion_history(self) -> list[dict[str, Any]]:
        return list(self._promotions)
