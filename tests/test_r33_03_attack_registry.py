import pytest
from tiannara.application.security.attack_registry import AttackRegistry
from tiannara.application.security.attack_taxonomy import AttackDefinition, Criticality
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_duplicate_rejected():
    a = AttackDefinition("dup", "sql_injection", "union", "1.0.0", "db", ("DB_INTERFACE",), Criticality.CRITICAL, (), (), (), ())
    with pytest.raises(ValueError):
        AttackRegistry((a,a))
def test_unknown_rejected():
    r = AttackRegistry()
    with pytest.raises(KeyError):
        r.get("unknown-attack-999")
def test_versioned():
    r = AttackRegistry()
    for a in r.all():
        assert a.version
def test_immutable():
    r = AttackRegistry()
    h1 = r.content_hash()
    h2 = r.content_hash()
    assert h1 == h2
def test_criticality_frozen():
    r = AttackRegistry()
    for a in r.all():
        assert a.criticality in Criticality
def test_matrix_unchanged():
    h = CampaignReadinessHarness()
    assert h.matrix_summary() == (12, 18, 0, 0)
    assert h.recipe_isr_hash() == RECIPE_HASH
