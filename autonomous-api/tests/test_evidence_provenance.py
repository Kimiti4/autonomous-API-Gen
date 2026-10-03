from app.engine.verification_artifacts import VerificationExecution
from app.engine.evidence_provenance import create_evidence_record, derive_verdict, verify_evidence_chain

def execution(status="passed"):
    return VerificationExecution("python:x",status,("observed_result=ok",),"target-test-runner")

def record(status="passed", predecessor=""):
    return create_evidence_record(execution(status),"python:x","x","build:abc",("assertion",),predecessor)

def test_missing_evidence_is_inconclusive():
    assert derive_verdict("x",()).verdict == "INCONCLUSIVE"

def test_failed_evidence_wins_over_pass():
    assert derive_verdict("x",(record("passed"),record("failed"))).verdict == "FAIL"

def test_blocked_evidence_is_not_pass():
    assert derive_verdict("x",(record("blocked"),)).verdict == "BLOCKED"

def test_hash_chain_is_verifiable():
    first=record()
    second=record(predecessor=first.content_hash)
    assert verify_evidence_chain((first,second))

def test_tampered_chain_is_rejected():
    first=record()
    second=record(predecessor="tampered")
    assert not verify_evidence_chain((first,second))
