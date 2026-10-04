from dataclasses import replace

import pytest

from app.engine.abort_evidence import build_abort_evidence
from app.engine.transaction_evidence import TransactionEvidenceRecord
from app.engine.transaction_evidence_chain import (
    GENESIS_PARENT_DIGEST,
    TransactionChainError,
    TransactionEvidenceChain,
    build_chain,
    verify_transaction_evidence_chain,
)


def _record(transaction_id: str, parent_digest: str | None = None):
    abort = build_abort_evidence(
        transaction_id=transaction_id,
        source_architecture_id="src",
        candidate_architecture_id=f"cand-{transaction_id}",
        stage="verification",
        reason="failed-test",
        attempted_mutations=("m1",),
        verification_evidence=("ev1",),
        residuals=("r1",),
    )
    record = TransactionEvidenceRecord.from_abort_record(abort)
    return replace(record, parent_digest=parent_digest, digest="")
    

def _sealed(record):
    from app.engine.transaction_evidence import _digest
    payload = record.canonical_payload()
    return replace(record, digest=_digest(payload))


def test_genesis_chain_requires_null_parent():
    first = _sealed(_record("tx-1", GENESIS_PARENT_DIGEST))
    chain = build_chain((first,))
    assert chain.verify()
    assert chain.tip_digest == first.digest


def test_append_links_to_previous_digest():
    first = _sealed(_record("tx-1"))
    chain = TransactionEvidenceChain().append(first)
    second = _sealed(_record("tx-2", first.digest))
    chain = chain.append(second)
    assert chain.verify()
    assert chain.tip_digest == second.digest


def test_wrong_parent_fails_closed():
    first = _sealed(_record("tx-1"))
    chain = TransactionEvidenceChain().append(first)
    second = _sealed(_record("tx-2", "wrong"))
    with pytest.raises(TransactionChainError, match="parent-digest-mismatch"):
        chain.append(second)


def test_tampering_is_detected():
    first = _sealed(_record("tx-1"))
    chain = TransactionEvidenceChain().append(first)
    tampered = replace(first, transaction_id="tampered")
    assert not verify_transaction_evidence_chain((tampered,))


def test_reordering_is_detected():
    first = _sealed(_record("tx-1"))
    second = _sealed(_record("tx-2", first.digest))
    assert not verify_transaction_evidence_chain((second, first))


def test_duplicate_digest_fails_closed():
    first = _sealed(_record("tx-1"))
    chain = TransactionEvidenceChain().append(first)
    with pytest.raises(TransactionChainError, match="duplicate-record-digest"):
        chain.append(first)


def test_abort_and_committed_records_share_chain_contract():
    first = _sealed(_record("tx-abort"))
    second = _sealed(_record("tx-after-abort", first.digest))
    assert verify_transaction_evidence_chain((first, second))
