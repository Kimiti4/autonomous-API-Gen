from tiannara.application.resilience.recovery_state import RecoveryState
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
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
