import pytest
from types import SimpleNamespace
from app.engine.candidate_patch import FileChange, build_candidate_patch
from app.engine.repair_atomic_admission import validate_repair_patch_for_atomic_admission
from app.engine.transaction_atomicity import AtomicTransactionResult, TransactionDisposition

def patch():
    return build_candidate_patch("c","w","r","base",[FileChange("a.py","1","2","modify")])

def test_aborted_transaction_cannot_admit_patch():
    p=patch()
    result=AtomicTransactionResult(TransactionDisposition.ABORTED,None,SimpleNamespace(stage="x",reason="fail"),None)
    a=validate_repair_patch_for_atomic_admission(p,candidate_id="c",workspace_id="w",
        source_revision="r",base_digest="base",transaction_result=result)
    assert not a.admitted and a.reason=="transaction-not-committed"

def test_baseline_mismatch_fails_closed():
    p=patch()
    result=AtomicTransactionResult(TransactionDisposition.COMMITTED,SimpleNamespace(audit_record=object()),None,None)
    with pytest.raises(ValueError,match="candidate-patch-baseline-mismatch"):
        validate_repair_patch_for_atomic_admission(p,candidate_id="c",workspace_id="other",
            source_revision="r",base_digest="base",transaction_result=result)
