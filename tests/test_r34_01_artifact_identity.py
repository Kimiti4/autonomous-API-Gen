import pytest
from tiannara.application.security.artifact_identity import ArtifactSecurityIdentity
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def base(): return ArtifactSecurityIdentity("a","i","c","d","p","camp","gen")
def test_deterministic():
    assert base().identity()==base().identity()
def test_changes():
    b=base()
    for field in ["artifact_hash","isr_hash","compiler_hash","dependency_lock_hash","security_policy_hash","security_campaign_hash","generation_hash"]:
        mutated = ArtifactSecurityIdentity(**{**b.__dict__, field: "changed"})
        assert mutated.identity()!=b.identity()
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
