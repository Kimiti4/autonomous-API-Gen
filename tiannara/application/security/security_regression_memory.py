"""33.12 Regression -- append-only."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
@dataclass(frozen=True)
class RegressionRecord: finding_id: str; attack_id: str; artifact_hash: str; pattern: str
class RegressionMemory:
    def __init__(self, ledger: EvolutionLedger): self._ledger=ledger
    def add(self, rec: RegressionRecord):
        ev=EvolutionEvent(event_id=f"regression-{rec.finding_id}", evolution_id=rec.finding_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=rec.finding_id, payload={"record": rec.__dict__})
        return self._ledger.append_event(ev, evolution_id=rec.finding_id)
    def contains(self, finding_id): return self._ledger.event_by_ref(f"regression-{finding_id}") is not None
