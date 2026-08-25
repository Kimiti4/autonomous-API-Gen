from tiannara.application.resilience.recovery_state import RecoveryState
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_no_collapse():
    assert RecoveryState.BOUNDED.can_transition_to(RecoveryState.RECOVERED) is False
    assert RecoveryState.NOT_STARTED.can_transition_to(RecoveryState.RECOVERED) is False
    assert RecoveryState.DETECTED.can_transition_to(RecoveryState.RECOVERED) is False
def test_valid_transitions():
    assert RecoveryState.NOT_STARTED.can_transition_to(RecoveryState.DETECTED) is True
    assert RecoveryState.DETECTED.can_transition_to(RecoveryState.CONTAINED) is True
    assert RecoveryState.CONTAINED.can_transition_to(RecoveryState.RECOVERING) is True
    assert RecoveryState.RECOVERING.can_transition_to(RecoveryState.RECOVERED) is True
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
