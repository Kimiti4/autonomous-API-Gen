"""36.0 Enterprise Contract -- frozen, hash-bound."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

DIMENSIONS = ("identity","authorization","privacy","auditability","compliance","cryptography","key_management","backup","disaster_recovery","zero_trust","multi_tenancy","regionalization","cost","governance")

@dataclass(frozen=True)
class EnterpriseContract:
    contract_id: str; dimensions: tuple[str,...]; content_hash: str

def contract_body(c): return {"contract_id": c.contract_id, "dimensions": list(c.dimensions)}
def build_enterprise_contract(contract_id="enterprise-contract-001"):
    tmp = EnterpriseContract(contract_id, DIMENSIONS, "")
    h = canonical_hash(contract_body(tmp))
    return EnterpriseContract(contract_id, DIMENSIONS, h)

ENTERPRISE_CONTRACT = build_enterprise_contract()

def register_enterprise_contract(c: EnterpriseContract, ledger: EvolutionLedger):
    body = contract_body(c)
    assert c.content_hash == canonical_hash(body)
    ev = EvolutionEvent(event_id=f"enterprise-contract-{c.contract_id}", evolution_id=c.contract_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=c.contract_id, payload={"enterprise_contract": body, "content_hash": c.content_hash})
    return ledger.append_event(ev, evolution_id=c.contract_id)
