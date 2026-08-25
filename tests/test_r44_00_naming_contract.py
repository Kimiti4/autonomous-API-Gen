from tiannara.application.identity.naming_contract import NAMING_CONTRACT, build_naming_contract, contract_body, register_naming_contract
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_hash_ledger():
    ledger=EvolutionLedger()
    c=build_naming_contract()
    assert c.content_hash==canonical_hash(contract_body(c))
    assert c.thresholds_frozen
    ref=register_naming_contract(c, ledger)
    assert ledger.event_by_ref(ref) is not None
def test_dimensions():
    assert len(NAMING_CONTRACT.dimensions)==10
    assert "semantic_fit" in NAMING_CONTRACT.dimensions
    assert len(NAMING_CONTRACT.forbidden)==5
def test_no_mutation():
    c=NAMING_CONTRACT
    assert c.thresholds_frozen
    # generation != certification
    assert c.dimensions != c.forbidden
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
