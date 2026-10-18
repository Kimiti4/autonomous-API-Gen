from tiannara.application.chaos.chaos_contract import CHAOS_CONTRACT, build_chaos_contract, contract_body, register_chaos_contract
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_hash_and_ledger():
    ledger=EvolutionLedger()
    c=build_chaos_contract()
    assert c.content_hash==canonical_hash(contract_body(c))
    ref=register_chaos_contract(c, ledger)
    assert ledger.event_by_ref(ref) is not None
def test_defines_classes():
    c=CHAOS_CONTRACT
    assert "container_death" in c.failure_classes
    assert c.recovery_deadline_ms>0
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
