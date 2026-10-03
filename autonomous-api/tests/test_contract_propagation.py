from app.engine.contract_propagation import *

def contract(kind="breaking"):
    return ContractLink("api.wallet.v2","backend.wallet","frontend.wallet-client",kind,"")

def test_breaking_contract_propagates_to_both_sides():
    r=propagate_contract_change(contract())
    impacts={(f.artifact_id,f.impact) for f in r.findings}
    assert ("backend.wallet","review") in impacts
    assert ("frontend.wallet-client","migration-required") in impacts

def test_unknown_compatibility_remains_uncertain():
    r=propagate_contract_change(contract("unknown"))
    assert requires_compatibility_gate(r)
    assert any(f.impact=="uncertainty" for f in r.findings)

def test_nonbreaking_contract_still_requires_review():
    r=propagate_contract_change(contract("compatible"))
    assert not requires_compatibility_gate(r)
    assert len(r.findings)==2

def test_only_changed_contracts_propagate():
    r=affected_by_contracts((contract(),ContractLink(
        "api.other","a","b","compatible")),("api.wallet.v2",))
    assert all(f.contract_id=="api.wallet.v2" for f in r.findings)
