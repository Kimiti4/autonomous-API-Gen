from tiannara.application.evolution.architecture_evolution_contract import ARCHITECTURE_EVOLUTION_CONTRACT, EvolutionState, build_architecture_evolution_contract, contract_body, register_architecture_contract
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_hash_and_ledger():
    ledger=EvolutionLedger()
    c=build_architecture_evolution_contract()
    assert c.content_hash==canonical_hash(contract_body(c))
    ref=register_architecture_contract(c, ledger)
    assert ledger.event_by_ref(ref) is not None
    assert ledger.verify_event_chain()
def test_bounded_not_adopted():
    assert EvolutionState.BOUNDED != EvolutionState.ADOPTED
    assert EvolutionState.BOUNDED.value != EvolutionState.ADOPTED.value
def test_contract_declares_dimensions():
    c=ARCHITECTURE_EVOLUTION_CONTRACT
    assert c.architecture_dimensions and c.scalability_dimensions and c.semantic_preservation_requirements
    assert c.content_hash
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
