from tiannara.application.certification.phase36_campaign import PHASE36_CONTRACT, run_phase36_campaign, build_phase36_contract
from tiannara.application.certification.production_readiness import CertificationEvidence, DimensionVerdict
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent, EventType
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def _ev(dim, verdict):
    ledger=EvolutionLedger()
    # Need to create evidence refs that resolve
    ev=EvolutionEvent(event_id=f"ev-{dim}", evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"dim": dim})
    ref=ledger.append_event(ev, evolution_id="test")
    return CertificationEvidence(dim, verdict, 0, (ref,), f"h-{dim}"), ledger
def test_phase36_frozen():
    c1=build_phase36_contract()
    c2=build_phase36_contract()
    assert c1.content_hash==c2.content_hash
    assert c1.contract_id=="phase36-production-readiness-001"
def test_phase36_production_ready():
    ledger=EvolutionLedger()
    evidence={}
    for dim in ["compiler","engineering","security","resilience"]:
        ev, l = _ev(dim, DimensionVerdict.CERTIFIED)
        # Need shared ledger
        ledger.append_event(EvolutionEvent(event_id=f"ev-{dim}", evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"dim": dim}), evolution_id="test")
        evidence[dim]=CertificationEvidence(dim, DimensionVerdict.CERTIFIED, 0, (f"ev-{dim}",), f"h-{dim}")
    # Actually need refs to resolve in same ledger used by gate
    gate_ledger=EvolutionLedger()
    for dim in ["compiler","engineering","security","resilience"]:
        ev=EvolutionEvent(event_id=f"ev-{dim}", evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"dim": dim})
        gate_ledger.append_event(ev, evolution_id="test")
    evidence2={dim: CertificationEvidence(dim, DimensionVerdict.CERTIFIED, 0, (f"ev-{dim}",), f"h-{dim}") for dim in ["compiler","engineering","security","resilience"]}
    result=run_phase36_campaign(evidence2, gate_ledger)
    assert result.verdict.value=="PRODUCTION_READY"
def test_phase36_blocks_on_failure():
    ledger=EvolutionLedger()
    for dim in ["compiler","engineering","security","resilience"]:
        ev=EvolutionEvent(event_id=f"ev-{dim}", evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"dim": dim})
        ledger.append_event(ev, evolution_id="test")
    evidence={dim: CertificationEvidence(dim, DimensionVerdict.CERTIFIED, 0, (f"ev-{dim}",), f"h-{dim}") for dim in ["compiler","engineering","security","resilience"]}
    evidence["security"]=CertificationEvidence("security", DimensionVerdict.NOT_CERTIFIED, 0, ("ev-security",), "h-security")
    result=run_phase36_campaign(evidence, ledger)
    assert result.verdict.value=="NOT_PRODUCTION_READY"
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
