"""33.5 Security Evidence -- ISR->Surface->Attack->Execution->Observation->Finding->Cert."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class SecuritySurfaceEvidence:
    isr_hash: str; artifact_hash: str; surface_id: str; evidence_id: str
    def identity(self): return canonical_hash(self.evidence_id)
@dataclass(frozen=True)
class AttackExecutionEvidence:
    attack_id: str; artifact_hash: str; execution_id: str; state: str
@dataclass(frozen=True)
class SecurityObservation:
    execution_id: str; observation_id: str; detected: bool; ledger_ref: str
@dataclass(frozen=True)
class SecurityFinding:
    observation_id: str; finding_id: str; severity: str; ledger_ref: str
@dataclass(frozen=True)
class ContainmentEvidence:
    finding_id: str; contained: bool; ledger_ref: str
@dataclass(frozen=True)
class RecoveryEvidence:
    finding_id: str; recovered: bool; ledger_ref: str
