from tiannara.application.evolution.architecture_fitness import measure_fitness
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_independently_observable():
    obs={"throughput": 100, "latency": 50, "availability": 0.99}
    f=measure_fitness(obs)
    assert f.throughput==100 and f.latency==50
    assert not f.has_composite()
    assert len(f.dimensions())==9
def test_no_composite_score():
    f=measure_fitness({"throughput": 1})
    assert not hasattr(f, "composite") and not hasattr(f, "score")
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
