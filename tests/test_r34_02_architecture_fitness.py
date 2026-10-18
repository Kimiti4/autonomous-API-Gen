from tiannara.application.evolution.architecture_fitness import measure_fitness
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
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
