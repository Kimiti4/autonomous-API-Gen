from tiannara.application.resilience.failure_taxonomy import REGISTRY, ALL_FAILURES, content_hash, is_known
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_all_categories_present():
    cats={f.category for f in REGISTRY}
    assert {"process","resource","infrastructure","distributed","deployment","temporal"}<=cats
def test_no_unknown():
    assert is_known("process_crash")
    assert not is_known("unknown_failure_xyz")
def test_deterministic_hash():
    assert content_hash()==content_hash()
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
