"""ProviderRegistry — capability-indexed, deterministic, fail-fast."""

from __future__ import annotations

from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceTask,
    LocalityLevel,
)
from tiannara.domain.ports.intelligence import IntelligenceProvider


class RegistryError(ValueError):
    pass


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, IntelligenceProvider] = {}

    def register(self, provider: IntelligenceProvider) -> None:
        declaration = provider.declaration
        if declaration.provider_id in self._providers:
            raise RegistryError(
                f"duplicate provider id: {declaration.provider_id}"
            )
        self._providers[declaration.provider_id] = provider

    def providers(self) -> list[IntelligenceProvider]:
        return [self._providers[key] for key in sorted(self._providers)]

    def matches(
        self, task: IntelligenceTask, max_locality: LocalityLevel
    ) -> list[IntelligenceProvider]:
        """Capability-matched providers within the locality ceiling,
        in deterministic (locality, provider_id) order."""
        ceiling = max_locality
        if task.privacy_class.value == "local_only":
            ceiling = min(ceiling, LocalityLevel.L2_LOCAL_MODEL)
        matched = []
        for provider in self._providers.values():
            declaration = provider.declaration
            if declaration.locality > ceiling:
                continue
            if task.task_kind not in declaration.task_kinds:
                continue
            if (
                declaration.output_schema_ids
                and task.output_schema_id not in declaration.output_schema_ids
            ):
                continue
            matched.append(provider)
        return sorted(
            matched,
            key=lambda p: (p.declaration.locality.value, p.declaration.provider_id),
        )
