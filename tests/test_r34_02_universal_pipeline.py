import pytest
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.security.universal_pipeline import UniversalSecurityPipeline
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_auto_invoke_and_no_bypass():
    ledger=EvolutionLedger()
    p=UniversalSecurityPipeline(ledger)
    assert p.can_bypass() is False
    r=p.run("art-123","isr-123","CERTIFIED")
    assert r.evidence_refs
    assert all(ledger.event_by_ref(ref) for ref in r.evidence_refs)
def test_bounded_never_promoted():
    ledger=EvolutionLedger()
    p=UniversalSecurityPipeline(ledger)
    r=p.run("art-123","isr-123","BOUNDED")
    assert r.promoted is False
def test_deterministic_planning():
    l1=EvolutionLedger(); l2=EvolutionLedger()
    r1=UniversalSecurityPipeline(l1).run("art-A","isr-A","CERTIFIED")
    r2=UniversalSecurityPipeline(l2).run("art-A","isr-A","CERTIFIED")
    assert r1.evidence_refs==r2.evidence_refs
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
