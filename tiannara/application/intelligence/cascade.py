"""CascadeExecutor — the deterministic-first cascade.

Tries matched providers in (locality, provider_id) order; the first success
deflects all remaining candidates, and every deflection is recorded. This
is what makes "remove every API key" a structural property rather than a
hope: with KEYLESS_POLICY, L3 candidates never enter the candidate set.

Policy objectives other than LOCALITY_FIRST reorder the capability-matched
candidate set before execution; for LOCALITY_FIRST the order is identical to
D1, so existing behaviour is preserved.

Cascade downward is realized structurally, not by inversion: lower-locality
providers are always attempted first; a local failure under a keyless policy
becomes a deterministic CascadeExhaustedError because L3 is absent from the
candidate set (max_locality < L3), never a silent escalation.
"""

from __future__ import annotations

from tiannara.domain.models.intelligence import (
    CascadeStep,
    CascadeStepOutcome,
    IntelligenceResult,
    IntelligenceTask,
)
from tiannara.domain.models.model_call import LanguageModelError

from .registry import ProviderRegistry
from .router import RoutingObjective, RoutingPolicy, order_candidates


class CascadeExhaustedError(LanguageModelError):
    def __init__(self, task: IntelligenceTask, path: list[CascadeStep]) -> None:
        self.task = task
        self.cascade_path = path
        attempted = [
            step.provider_id
            for step in path
            if step.outcome is CascadeStepOutcome.FAILED
        ]
        super().__init__(
            f"Cascade exhausted for task '{task.task_label}' "
            f"(kind={task.task_kind.value}). Attempted: {attempted}"
        )


class CascadeExecutor:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def execute(
        self, task: IntelligenceTask, policy: RoutingPolicy
    ) -> IntelligenceResult:
        candidates = self._registry.matches(task, policy.max_locality)
        if policy.objective is not RoutingObjective.LOCALITY_FIRST:
            candidates = order_candidates(candidates, policy)
        path: list[CascadeStep] = []
        attempts = 0
        result: IntelligenceResult | None = None

        for provider in candidates:
            declaration = provider.declaration
            if attempts >= policy.max_cascade_attempts:
                path.append(
                    CascadeStep(
                        provider_id=declaration.provider_id,
                        provider_class=declaration.provider_class,
                        locality=declaration.locality,
                        outcome=CascadeStepOutcome.DEFLECTED,
                        detail="cascade attempt budget reached",
                    )
                )
                continue
            if result is not None:
                path.append(
                    CascadeStep(
                        provider_id=declaration.provider_id,
                        provider_class=declaration.provider_class,
                        locality=declaration.locality,
                        outcome=CascadeStepOutcome.DEFLECTED,
                        detail="served by lower locality",
                    )
                )
                continue
            attempts += 1
            try:
                result = provider.complete(task)
                path.append(
                    CascadeStep(
                        provider_id=declaration.provider_id,
                        provider_class=declaration.provider_class,
                        locality=declaration.locality,
                        outcome=CascadeStepOutcome.EXECUTED,
                    )
                )
            except LanguageModelError as exc:
                path.append(
                    CascadeStep(
                        provider_id=declaration.provider_id,
                        provider_class=declaration.provider_class,
                        locality=declaration.locality,
                        outcome=CascadeStepOutcome.FAILED,
                        detail=str(exc)[:200],
                    )
                )

        if result is None:
            raise CascadeExhaustedError(task, path)
        result.policy_name = policy.name
        result.cascade_path = path
        return result
