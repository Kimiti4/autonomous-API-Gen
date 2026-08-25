from tiannara.application.resilience.failure_taxonomy import REGISTRY, ALL_FAILURES, content_hash, is_known
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
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
