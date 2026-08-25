"""33.3 Attack Taxonomy -- immutable, versioned."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tiannara.domain.services.canonical import canonical_hash


class Criticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class AttackDefinition:
    attack_id: str
    family: str
    technique: str
    version: str
    applicability: str
    target_surface_types: tuple[str, ...]
    criticality: Criticality
    required_capabilities: tuple[str, ...]
    required_evidence: tuple[str, ...]
    safe_constraints: tuple[str, ...]
    expected_observations: tuple[str, ...]

    def canonical_hash(self) -> str:
        return canonical_hash({
            "attack_id": self.attack_id,
            "family": self.family,
            "technique": self.technique,
            "version": self.version,
            "criticality": self.criticality.value,
        })
