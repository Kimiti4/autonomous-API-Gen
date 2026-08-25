"""33.4 Attack Definition Contract -- WHAT not HOW."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash

@dataclass(frozen=True)
class AttackTarget:
    surface_id: str
    surface_type: str
    artifact_ref: str

@dataclass(frozen=True)
class AttackDefinition:
    attack_id: str
    target: AttackTarget
    applicability: str
    preconditions: tuple[str, ...]
    safe_envelope: tuple[str, ...]
    expected_boundary: str
    expected_evidence: tuple[str, ...]
    criticality: str
    detection_expectation: str

    def __post_init__(self):
        if not self.attack_id or not self.target.surface_id:
            raise ValueError("incomplete attack definition")
        if not self.safe_envelope:
            raise ValueError("safe envelope required")

    def identity(self) -> str:
        return canonical_hash({"attack_id": self.attack_id, "target": self.target.surface_id, "criticality": self.criticality})
