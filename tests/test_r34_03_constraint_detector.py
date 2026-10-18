from tiannara.application.evolution.architecture_constraint_detector import detect_constraints
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_detects_from_observation():
    assert "throughput_violation" in detect_constraints({"throughput": 50, "required_throughput": 100})
    assert "latency_violation" in detect_constraints({"latency": 300, "required_latency": 200})
    assert detect_constraints({"throughput": 200, "latency": 50, "availability": 0.999})==()
def test_not_hardcoded_mapping():
    # Same workload, different observation -> different detection, not 1M->microservices
    assert detect_constraints({"throughput": 10})!=detect_constraints({"throughput": 1000})
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
