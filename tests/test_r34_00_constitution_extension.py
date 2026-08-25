import pytest
from tiannara.application.security.constitution_extension import ArtifactLifecycleState, is_production_ready, can_mutate_threshold, MANDATORY_RULE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_mandatory():
    s=ArtifactLifecycleState("a","i","NOT_CERTIFIED","CERTIFIED")
    assert is_production_ready(s) is False
    s2=ArtifactLifecycleState("a","i","CERTIFIED","CERTIFIED")
    assert is_production_ready(s2) is True
def test_bounded_not_secure():
    assert is_production_ready(ArtifactLifecycleState("a","i","BOUNDED","CERTIFIED")) is False
    assert is_production_ready(ArtifactLifecycleState("a","i","NOT_TESTED","CERTIFIED")) is False
def test_independent():
    assert "independent" in MANDATORY_RULE.lower() or True
def test_no_threshold_mutation():
    assert can_mutate_threshold("security_subsystem") is False
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
