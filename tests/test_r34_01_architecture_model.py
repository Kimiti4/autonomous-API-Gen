from tiannara.application.evolution.architecture_model import derive_architecture
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
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
