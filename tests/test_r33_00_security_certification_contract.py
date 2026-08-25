import ast, inspect
import pytest
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.security.security_certification_contract import (
    SECURITY_CONTRACT, build_security_contract, contract_body, hash_canonical, register_security_contract,
)
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"

def test_contract_hash_and_ledger():
    ledger = EvolutionLedger()
    c = build_security_contract()
    assert c.content_hash == hash_canonical(contract_body(c))
    ref = register_security_contract(c, ledger)
    assert ledger.event_by_ref(ref) is not None

def test_no_composite_score():
    assert not hasattr(SECURITY_CONTRACT, "composite_score")

def test_bounded_cannot_certify():
    assert "BOUNDED_NEVER_CERTIFIED" in SECURITY_CONTRACT.bounded_policy

def test_critical_missed_blocks():
    assert "remote_code_execution" in SECURITY_CONTRACT.critical_vulnerability_classes

def test_runner_does_not_mutate_contract():
    # Runner must not have threshold mutation surface
    from tiannara.application.security import security_certification_contract as m
    tree = ast.parse(inspect.getsource(m))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "mutate_threshold" not in fn

def test_matrix_unchanged():
    h = CampaignReadinessHarness()
    assert h.matrix_summary() == (12, 18, 0, 0)
    assert h.recipe_isr_hash() == RECIPE_HASH
