"""35.4 Evidence chain -- artifact->recovery, composable not conflated."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
@dataclass(frozen=True)
class ResilienceEvidence:
    artifact_hash: str; failure_id: str; detection_ref: str; containment_ref: str; recovery_ref: str; verification_ref: str
    def chain(self, ledger: EvolutionLedger):
        for ref in (self.detection_ref, self.containment_ref, self.recovery_ref, self.verification_ref):
            assert ledger.event_by_ref(ref) is not None
