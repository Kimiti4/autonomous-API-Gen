from app.engine.invariant_contracts import *

def contract():
    return InvariantContract("security",(
        Invariant("AUTHZ","security","authorization remains enforced",("sec-test",)),
        Invariant("AUDIT","security","security events remain auditable",("audit-test",)),
    ))

def test_contract_requires_evidence():
    validate_contract(contract())

def test_contract_evaluates_observations():
    r=evaluate_contract(contract(),{"AUTHZ":True,"AUDIT":True})
    assert contract_passes(r)

def test_failed_invariant_blocks_contract():
    r=evaluate_contract(contract(),{"AUTHZ":True,"AUDIT":False})
    assert not contract_passes(r)
    try:
        require_contract_pass(r)
    except ValueError as e:
        assert str(e)=="invariant-contract-failed:AUDIT"
        return
    assert False

def test_missing_observation_is_not_assumed_pass():
    try:
        evaluate_contract(contract(),{"AUTHZ":True})
    except ValueError as e:
        assert str(e)=="invariant-observation-missing"
        return
    assert False

def test_wrong_domain_invariant_rejected():
    c=InvariantContract("frontend",(Invariant("AUTHZ","security","x",("e",)),))
    try:
        validate_contract(c)
    except ValueError as e:
        assert str(e)=="invariant-domain-mismatch"
        return
    assert False
