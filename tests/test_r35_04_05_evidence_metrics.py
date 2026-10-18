from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent, EventType
from tiannara.application.resilience.evidence_chain import ResilienceEvidence
from tiannara.application.resilience.metrics import ResilienceMetrics
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_chain_composable():
    ledger=EvolutionLedger()
    refs=[]
    for i in range(4):
        ev=EvolutionEvent(event_id=f"ev-{i}", evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"i":i})
        refs.append(ledger.append_event(ev, evolution_id="test"))
    evd=ResilienceEvidence("art","fail",refs[0],refs[1],refs[2],refs[3])
    evd.chain(ledger)
def test_no_composite():
    m=ResilienceMetrics(10,8,7,6,1,1, 0.5,0.6,0.7)
    assert m.has_composite() is False
    assert m.conserved
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
