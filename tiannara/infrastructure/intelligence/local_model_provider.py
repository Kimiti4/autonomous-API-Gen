"""LocalModelProvider — an L2 intelligence provider behind the AIR port.

Wraps any LanguageModelProvider (a live endpoint for real local models, or
a recorded replay for hermetic runs) and declares it as
ProviderClass.LOCAL_MODEL, with topology carried as opaque metadata. The AIR
core sees only IntelligenceProvider + CapabilityDeclaration; this module
names no runtime, accelerator, or vendor in core reasoning paths.
"""

from __future__ import annotations

from tiannara.application.intelligence.bridge import LanguageModelIntelligenceAdapter
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.ports.language_model import LanguageModelProvider

from .local_topology import LocalTopology


class LocalModelProvider(LanguageModelIntelligenceAdapter):
    """A local (L2) model provider built from a topology manifest."""

    @classmethod
    def from_topology(
        cls,
        underlying: LanguageModelProvider,
        topology: LocalTopology,
    ) -> "LocalModelProvider":
        declaration = CapabilityDeclaration(
            provider_id=topology.provider_id,
            provider_class=ProviderClass.LOCAL_MODEL,
            task_kinds=[TaskKind(kind) for kind in topology.task_kinds],
            metadata={
                "transport": topology.transport,
                "topology_version": topology.topology_version,
                **topology.metadata,
            },
        )
        return cls(underlying, declaration)
