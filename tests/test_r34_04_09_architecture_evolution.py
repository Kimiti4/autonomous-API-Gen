from tiannara.application.evolution.architecture_transformer import propose_transformation
from tiannara.application.evolution.architecture_hypothesis import generate_hypothesis
from tiannara.application.evolution.architecture_migration import compile_migration
from tiannara.application.evolution.architecture_semantic_gate import is_semantically_preserved
from tiannara.application.evolution.architecture_evolution_campaign import campaign_scenarios
from tiannara.application.evolution.architecture_evolution_gate import evaluate, Gate
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_transformer_isr_carrier():
    t=propose_transformation("throughput_violation", {"service:api": ["fact"]})
    assert t.is_valid()
    assert t.hash()==propose_transformation("throughput_violation", {"service:api": ["fact"]}).hash()
def test_hypothesis_falsifiable():
    h=generate_hypothesis("latency_violation")
    assert h.is_falsifiable()
    assert h.migration_required
def test_migration_has_rollback():
    t=propose_transformation("throughput_violation", {})
    h=generate_hypothesis("throughput_violation")
    m=compile_migration(t,h)
    assert m.has_rollback()
def test_semantic_preservation():
    assert is_semantically_preserved("intent A","intent A", True) is True
    assert is_semantically_preserved("intent A","intent B", True) is False
def test_campaign_scenarios():
    s=campaign_scenarios()
    assert 100 in s and 100_000_000 in s and "spike" in s
def test_gate_eight():
    evidence={g.value: True for g in Gate}
    ok,_=evaluate(evidence)
    assert ok
    evidence[Gate.SEMANTIC_PRESERVED.value]=False
    ok, blocked=evaluate(evidence)
    assert not ok and blocked==Gate.SEMANTIC_PRESERVED
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
