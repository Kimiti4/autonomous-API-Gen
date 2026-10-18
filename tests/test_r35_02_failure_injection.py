from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.resilience.failure_injection import FailureKind, inject_failure
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_injects_environment_not_verdict():
    ledger=EvolutionLedger()
    env={"env_id": "env-test-1"}
    inj=inject_failure(env, FailureKind.PROCESS_CRASH, ledger)
    assert env["failed_kind"]=="process_crash"
    assert ledger.event_by_ref(inj.evidence_ref) is not None
    assert inj.failure_id.startswith("failure-")
def test_deterministic():
    l1=EvolutionLedger(); l2=EvolutionLedger()
    e1={"env_id":"env-A"}; e2={"env_id":"env-A"}
    assert inject_failure(e1, FailureKind.DB_UNAVAILABLE, l1).failure_id==inject_failure(e2, FailureKind.DB_UNAVAILABLE, l2).failure_id
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
