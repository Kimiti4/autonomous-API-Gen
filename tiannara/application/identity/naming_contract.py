"""44.0 Naming Contract -- frozen, 10 dims, hash-bound."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

CONTRACT_ID = "phase44-naming-contract-001"
VERSION = "1.0.0"
DIMENSIONS = (
    "semantic_fit","memorability","pronounceability","distinctiveness","architectural_fit",
    "audience_fit","international_usability","collision_safety","repository_safety","brand_safety",
)
FORBIDDEN = (
    "misleading_identity","confusing_collision","reserved_identifier","credential_leakage","technology_coupling",
)

@dataclass(frozen=True)
class NamingContract:
    contract_id: str; version: str; dimensions: tuple[str,...]; forbidden: tuple[str,...]; thresholds_frozen: bool; content_hash: str

def contract_body(c): return {"contract_id": c.contract_id, "version": c.version, "dimensions": list(c.dimensions), "forbidden": list(c.forbidden), "thresholds_frozen": c.thresholds_frozen}
def build_naming_contract():
    tmp = NamingContract(CONTRACT_ID, VERSION, DIMENSIONS, FORBIDDEN, True, "")
    h = canonical_hash(contract_body(tmp))
    return NamingContract(CONTRACT_ID, VERSION, DIMENSIONS, FORBIDDEN, True, h)
NAMING_CONTRACT = build_naming_contract()
def register_naming_contract(c: NamingContract, ledger: EvolutionLedger):
    body = contract_body(c)
    assert c.content_hash == canonical_hash(body)
    assert c.thresholds_frozen
    ev = EvolutionEvent(event_id=f"naming-contract-{c.contract_id}", evolution_id=c.contract_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=c.contract_id, payload={"naming_contract": body, "content_hash": c.content_hash})
    return ledger.append_event(ev, evolution_id=c.contract_id)
