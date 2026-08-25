"""Phase36 frozen Production Readiness campaign."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.certification.production_readiness import ProductionReadinessGate
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash

@dataclass(frozen=True)
class Phase36Contract:
    contract_id: str
    content_hash: str

def build_phase36_contract():
    body = {"contract_id": "phase36-production-readiness-001", "required_dimensions": ["compiler","engineering","security","resilience"]}
    h = canonical_hash(body)
    return Phase36Contract("phase36-production-readiness-001", h)

PHASE36_CONTRACT = build_phase36_contract()

def run_phase36_campaign(evidence_map: dict, ledger: EvolutionLedger):
    gate = ProductionReadinessGate(ledger)
    result = gate.evaluate(evidence_map)
    return result
