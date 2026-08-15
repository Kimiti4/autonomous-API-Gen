from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_events import (
    VerificationEvent,
    VerificationEventBus,
    VerificationEventType,
)
from constitutional_architecture.verification.verification_registry import VerificationRegistry
from constitutional_architecture.verification.verification_result import (
    VerificationLevel,
    VerificationResult,
)


@dataclass
class PipelineConfig:
    max_level: VerificationLevel = VerificationLevel.L3_SECURITY
    stop_on_blocker: bool = True
    stop_on_error: bool = False
    timeout_ms: float = 60000.0


class VerificationPipeline:
    def __init__(
        self,
        registry: VerificationRegistry,
        event_bus: VerificationEventBus,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self._config = config or PipelineConfig()

    def execute(self, ctx: VerificationContext) -> list[VerificationResult]:
        verifiers = self._registry.get_up_to_level(self._config.max_level)
        results: list[VerificationResult] = []
        start_time = time.perf_counter()

        for verifier in verifiers:
            elapsed = (time.perf_counter() - start_time) * 1000
            if elapsed > self._config.timeout_ms:
                break

            if not verifier.can_verify(ctx):
                continue

            self._event_bus.publish(VerificationEvent(
                event_type=VerificationEventType.VERIFIER_STARTED,
                data={"verifier": verifier.name, "level": verifier.level.value},
            ))

            result = verifier.verify(ctx)
            results.append(result)

            self._event_bus.publish(VerificationEvent(
                event_type=VerificationEventType.VERIFIER_COMPLETED,
                data={
                    "verifier": verifier.name,
                    "passed": result.all_checks_passed,
                    "checks": len(result.checks),
                    "duration_ms": result.duration_ms,
                },
            ))

            if self._config.stop_on_blocker and result.has_blockers:
                self._event_bus.publish(VerificationEvent(
                    event_type=VerificationEventType.BLOCKER_FOUND,
                    data={"verifier": verifier.name},
                ))
                break

            if self._config.stop_on_error and not result.success:
                break

        return results
