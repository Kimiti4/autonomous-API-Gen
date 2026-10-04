from app.engine.abort_evidence import build_abort_evidence
from app.engine.transaction_evidence import TransactionEvidenceRecord


def test_abort_record_uses_common_transaction_evidence_schema():
    abort = build_abort_evidence(
        transaction_id="tx-common",
        source_architecture_id="src",
        candidate_architecture_id="cand",
        stage="verification",
        reason="failed-test",
        attempted_mutations=("m1",),
        verification_evidence=("ev1",),
        residuals=("r1",),
    )
    evidence = TransactionEvidenceRecord.from_abort_record(abort)
    assert evidence.schema_version == "esap.transaction-evidence.v2"
    assert evidence.admission["admitted"] is False
    assert evidence.rejection["status"] == "ABORTED"
    assert evidence.verify_digest()
