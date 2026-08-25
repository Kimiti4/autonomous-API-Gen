from tiannara.application.security.supply_chain import Dependency, verify_integrity, is_arbitrary, lockfile_hash
from tiannara.application.security.secret_security import scan_secrets
from tiannara.application.security.data_security import is_sql_injection, is_exposure
from tiannara.application.security.container_security import is_filesystem_escape, is_network_exposure
from tiannara.application.resilience.chaos_stateful import ChaosState
from tiannara.application.security.dast_campaign import run_dast
from tiannara.application.evolution.ledger import EvolutionLedger
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_supply_chain():
    dep=Dependency("pkg","1.0","abc","pypi")
    assert verify_integrity(dep, {"pkg":"abc"}) is True
    assert is_arbitrary(dep, {"pkg"}) is False
    assert lockfile_hash({"pkg":"abc"})==lockfile_hash({"pkg":"abc"})
def test_secret_surface_must_be_exercised():
    assert scan_secrets("AKIA1234567890ABCDEF", False)==(False, ())
    assert scan_secrets("AKIA1234567890ABCDEF", True)[0] is True
def test_data_injection():
    assert is_sql_injection("' OR 1=1 --") is True
    assert is_exposure({"tenant":"a"}, "b") is True
def test_container():
    assert is_filesystem_escape("../host/etc") is True
    assert is_network_exposure(22, {80,443}) is True
def test_chaos_stateful_replay():
    s=ChaosState()
    s.step("a"); s.step("b")
    assert s.replay()==("a","b")
    assert s.under_pressure(1) is True
def test_dast_thousands_ledger():
    ledger=EvolutionLedger()
    arts=[f"art-{i}" for i in range(10)]
    atks=[f"attack-{i}" for i in range(100)]
    res=run_dast(arts, atks, ledger, seed=1)
    assert len(res)==1000
    assert all(ledger.event_by_ref(r.ledger_ref) for r in res)
    assert ledger.verify_event_chain() is True
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
