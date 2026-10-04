from app.engine.abort_evidence import build_abort_evidence


def test_abort_evidence_is_deterministic_and_never_admitted():
    record = build_abort_evidence(
        transaction_id="tx-1",
        source_architecture_id="src-1",
        candidate_architecture_id="cand-1",
        stage="verification",
        reason="test-failed",
        attempted_mutations=("backend-fix",),
        verification_evidence=("ev-1",),
        residuals=("repair-required",),
    )
    assert record.successor_admitted is False
    assert record.canonical_payload() == record.canonical_payload()
    assert len(record.evidence_digest()) == 64


def test_abort_evidence_requires_identity():
    import pytest

    with pytest.raises(ValueError, match="missing-transaction-id"):
        build_abort_evidence(
            transaction_id="",
            source_architecture_id="src",
            candidate_architecture_id="cand",
            stage="x",
            reason="y",
        )
