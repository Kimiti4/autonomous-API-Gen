from tiannara.application.evolution.architecture_model import derive_architecture
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_derived_from_isr():
    isr_facts={"service:auth": ["fact1"], "capability:orders": ["fact2"]}
    arch=derive_architecture(isr_facts)
    assert arch.derived_from_isr(isr_facts)
    assert arch.content_hash()==derive_architecture(isr_facts).content_hash()
def test_not_template():
    a1=derive_architecture({"service:a": ["1"]})
    a2=derive_architecture({"service:b": ["1"]})
    assert a1.services!=a2.services
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
