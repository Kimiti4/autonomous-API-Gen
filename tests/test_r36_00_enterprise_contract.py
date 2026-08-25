from tiannara.application.enterprise.enterprise_contract import ENTERPRISE_CONTRACT, build_enterprise_contract, contract_body, register_enterprise_contract
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_hash_ledger():
    ledger=EvolutionLedger()
    c=build_enterprise_contract()
    assert c.content_hash==canonical_hash(contract_body(c))
    assert ledger.event_by_ref(register_enterprise_contract(c, ledger)) is not None
def test_dimensions():
    assert "identity" in ENTERPRISE_CONTRACT.dimensions
    assert "multi_tenancy" in ENTERPRISE_CONTRACT.dimensions
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
