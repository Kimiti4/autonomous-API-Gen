import pytest
from app.engine.contract_synchronization import ContractSyncDecision,evaluate_contract_synchronization,require_contract_synchronization
from app.engine.contract_propagation import ContractLink

def c():
 return ContractLink("C-1","producer","consumer","api","compatible")
def test_both_sides_need_fresh_evidence():
 d=evaluate_contract_synchronization(c(),{"producer":{"passed":True,"evidence_ids":("E1",)},"consumer":{"passed":True,"evidence_ids":("E2",)}})
 assert d.passed
def test_missing_side_blocks_certification():
 d=evaluate_contract_synchronization(c(),{"producer":{"passed":True,"evidence_ids":("E1",)}})
 assert not d.passed and d.missing_artifacts==("consumer",)
 with pytest.raises(ValueError): require_contract_synchronization(d)
def test_unknown_compatibility_is_not_safe():
 d=evaluate_contract_synchronization(ContractLink("C","p","c","api","unknown"),{"p":{"passed":True,"evidence_ids":("E",)},"c":{"passed":True,"evidence_ids":("E2",)}})
 assert not d.passed
