"""
ASE-OS CKB Archetype Registry.

Real backend for the ArchetypeSynthesizer's `register_archetype` contract:
a persistent registry of fleet-discovered archetypes with empirical weights.
Newly minted archetypes are tagged EXPERIMENTAL until proven.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from constitutional_architecture.core.models.intent import QualityAttribute


class ArchetypeRegistry:
    """Registry of architectural archetypes discovered by macro-evolution."""

    def __init__(self) -> None:
        self.registered: Dict[str, Dict[str, Any]] = {}
        self._adrs: List[str] = []

    def register_archetype(self, name: str, base_genes: Dict[str, Any],
                           empirical_weights: Dict[Any, float]) -> None:
        self.registered[name] = {
            "genes": dict(base_genes),
            "weights": {
                a.value if isinstance(a, QualityAttribute) else str(a): w
                for a, w in empirical_weights.items()
            },
            "status": "EXPERIMENTAL",
        }

    def record_adr(self, adr: str) -> None:
        self._adrs.append(adr)

    def get_archetype(self, name: str) -> Optional[Dict[str, Any]]:
        return self.registered.get(name)

    def is_experimental(self, name: str) -> bool:
        entry = self.registered.get(name)
        return entry is not None and entry.get("status") == "EXPERIMENTAL"

    @property
    def archetypes(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.registered)

    @property
    def adrs(self) -> List[str]:
        return list(self._adrs)
