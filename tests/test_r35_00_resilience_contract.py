from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.resilience.resilience_contract import build_resilience_contract, contract_body, hash_canonical, register_resilience_contract
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_hash_and_ledger():
    ledger=EvolutionLedger()
    c=build_resilience_contract()
    assert c.content_hash==hash_canonical(contract_body(c))
    ref=register_resilience_contract(c, ledger)
    assert ledger.event_by_ref(ref) is not None
def test_no_threshold_mutation():
    assert build_resilience_contract().exit_threshold==0.995
def test_bounded_never_recovered():
    c=build_resilience_contract()
    assert "BOUNDED_NEVER_RECOVERED" in c.bounded_policy
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
