from tiannara.application.security.supply_chain import Dependency, verify_integrity, is_arbitrary, lockfile_hash
from tiannara.application.security.secret_security import scan_secrets
from tiannara.application.security.data_security import is_sql_injection, is_exposure
from tiannara.application.security.container_security import is_filesystem_escape, is_network_exposure
from tiannara.application.resilience.chaos_stateful import ChaosState
from tiannara.application.security.dast_campaign import run_dast
from tiannara.application.evolution.ledger import EvolutionLedger
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
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
    class Scanner:
        def __init__(self): self.calls=0
        def attack(self, artifact, attack, seed):
            self.calls += 1
            return int(attack.split("-")[1]) % 2 == 0
    scanner=Scanner()
    res=run_dast(arts, atks, ledger, seed=1, client=scanner)
    assert len(res)==1000
    assert scanner.calls==1000
    assert any(r.blocked for r in res) and any(not r.blocked for r in res)
    assert all(ledger.event_by_ref(r.ledger_ref) for r in res)
    assert ledger.verify_event_chain() is True
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
