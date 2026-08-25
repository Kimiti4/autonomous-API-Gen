import pytest
from tiannara.application.security.security_state import AttackOutcome, RecoveryState, SecurityTestState
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"

def test_bounded_never_pass():
    assert SecurityTestState.BOUNDED.contributes_to_pass() is False
    assert SecurityTestState.NOT_TESTED.contributes_to_pass() is False
    assert SecurityTestState.PASSED.contributes_to_pass() is True
    assert SecurityTestState.NOT_APPLICABLE.contributes_to_pass() is False

def test_missed_is_failure():
    assert AttackOutcome.MISSED.is_failure() is True
    assert AttackOutcome.BLOCKED.is_failure() is False
    assert AttackOutcome.DETECTED.is_success() is True
    assert AttackOutcome.CONTAINED.is_success() is True
    assert AttackOutcome.BOUNDED.is_success() is False

def test_no_state_collapse():
    assert SecurityTestState.BOUNDED != SecurityTestState.PASSED
    assert SecurityTestState.NOT_TESTED != SecurityTestState.PASSED
    assert SecurityTestState.NOT_APPLICABLE != SecurityTestState.NOT_TESTED
    assert AttackOutcome.BLOCKED != AttackOutcome.DETECTED != AttackOutcome.CONTAINED
    assert RecoveryState.BOUNDED != RecoveryState.RECOVERED

def test_exhaustive():
    assert set(SecurityTestState) == {SecurityTestState.NOT_APPLICABLE, SecurityTestState.NOT_TESTED, SecurityTestState.BOUNDED, SecurityTestState.PASSED, SecurityTestState.FAILED}
    assert set(AttackOutcome) == {AttackOutcome.BLOCKED, AttackOutcome.DETECTED, AttackOutcome.CONTAINED, AttackOutcome.MISSED, AttackOutcome.BOUNDED}

def test_matrix_unchanged():
    h = CampaignReadinessHarness()
    assert h.matrix_summary() == (12, 18, 0, 0)
    assert h.recipe_isr_hash() == RECIPE_HASH
