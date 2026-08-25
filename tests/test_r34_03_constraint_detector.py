from tiannara.application.evolution.architecture_constraint_detector import detect_constraints
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
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
