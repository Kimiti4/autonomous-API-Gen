import pytest

from app.engine.abort_evidence import build_abort_evidence
from app.engine.transaction_evidence import TransactionEvidenceRecord
from app.engine.transaction_evidence_chain import build_chain
from app.engine.transaction_recovery import (
    RecoveryDisposition,
    checkpoint_from_evidence,
    resume_from_checkpoint,
    validate_checkpoint,
)


def record(transaction_id, parent=None):
    abort = build_abort_evidence(
        transaction_id=transaction_id,
        source_architecture_id="source",
        candidate_architecture_id="candidate",
        stage="checkpoint",
        reason="safe-boundary",
    )
    return TransactionEvidenceRecord.from_abort_record(abort, parent_digest=parent)


def test_valid_tip_checkpoint_can_resume():
    first = record("tx-1")
    second = record("tx-2", first.digest)
    chain = build_chain((first, second))
    checkpoint = checkpoint_from_evidence(second, stage="verification", resumable=True)
    result = resume_from_checkpoint(checkpoint, chain, lambda: "resumed")
    assert result.value == "resumed"
    assert result.disposition is RecoveryDisposition.RESUMABLE


def test_non_tip_checkpoint_is_rejected():
    first = record("tx-1")
    second = record("tx-2", first.digest)
    chain = build_chain((first, second))
    checkpoint = checkpoint_from_evidence(first, stage="verification", resumable=True)
    result = resume_from_checkpoint(checkpoint, chain, lambda: pytest.fail("must not run"))
    assert result.disposition is RecoveryDisposition.TERMINAL
    assert result.reason == "checkpoint-invalid-or-not-chain-tip"


def test_tampered_chain_blocks_resume():
    first = record("tx-1")
    second = record("tx-2", first.digest)
    chain = build_chain((first, second))
    tampered = second.__class__(
        **{**second.__dict__, "residuals": ("tampered",)}
    )
    checkpoint = checkpoint_from_evidence(second, stage="verification", resumable=True)
    # Build a deliberately invalid chain without using append validation.
    from app.engine.transaction_evidence_chain import TransactionEvidenceChain
    invalid = TransactionEvidenceChain((first, tampered))
    result = resume_from_checkpoint(checkpoint, invalid, lambda: pytest.fail("must not run"))
    assert result.disposition is RecoveryDisposition.TERMINAL


def test_terminal_checkpoint_never_resumes():
    first = record("tx-1")
    chain = build_chain((first,))
    checkpoint = checkpoint_from_evidence(first, stage="audit", resumable=False)
    result = resume_from_checkpoint(checkpoint, chain, lambda: pytest.fail("must not run"))
    assert result.disposition is RecoveryDisposition.TERMINAL
    assert result.reason == "checkpoint-not-resumable"


def test_failed_resume_remains_resumable():
    first = record("tx-1")
    chain = build_chain((first,))
    checkpoint = checkpoint_from_evidence(first, stage="verification", resumable=True)
    result = resume_from_checkpoint(
        checkpoint, chain, lambda: (_ for _ in ()).throw(RuntimeError("transient"))
    )
    assert result.disposition is RecoveryDisposition.RESUMABLE
    assert result.value is None
    assert "transient" in result.reason


def test_invalid_checkpoint_evidence_is_rejected():
    first = record("tx-1")
    tampered = first.__class__(**{**first.__dict__, "digest": "bad"})
    with pytest.raises(ValueError, match="invalid-record-digest"):
        checkpoint_from_evidence(tampered, stage="verification", resumable=True)
