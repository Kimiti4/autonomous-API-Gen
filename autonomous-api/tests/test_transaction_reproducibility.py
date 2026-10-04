from dataclasses import replace

import pytest

from app.engine.transaction_evidence import _digest
from app.engine.transaction_evidence_chain import build_chain
from app.engine.transaction_reproducibility import (
    canonical_bytes,
    chain_reproducibility_digest,
    fingerprint_transaction,
    replay_equivalent,
)


def _record(transaction_id, parent=None):
    from app.engine.abort_evidence import build_abort_evidence
    from app.engine.transaction_evidence import TransactionEvidenceRecord

    abort = build_abort_evidence(
        transaction_id=transaction_id,
        source_architecture_id="source",
        candidate_architecture_id="candidate",
        stage="test",
        reason="deterministic",
        attempted_mutations=("m1",),
        verification_evidence=("e1",),
        residuals=("r1",),
    )
    record = TransactionEvidenceRecord.from_abort_record(abort, parent_digest=parent)
    return record


def test_same_transaction_replays_to_same_bytes_and_digest():
    first = _record("tx")
    second = _record("tx")
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.digest == second.digest
    assert replay_equivalent(first, second)


def test_fingerprint_is_stable_and_content_addressed():
    record = _record("tx")
    fp = fingerprint_transaction(record)
    assert fp.digest == record.digest
    assert fp.as_key().endswith(record.digest)


def test_tampering_invalidates_reproducibility():
    record = _record("tx")
    tampered = replace(record, residuals=("tampered",))
    with pytest.raises(ValueError, match="invalid-record-digest"):
        canonical_bytes(tampered)


def test_replay_mismatch_is_detected():
    first = _record("tx")
    second = _record("different-tx")
    assert not replay_equivalent(first, second)


def test_chain_reproducibility_is_order_sensitive_and_stable():
    first = _record("tx-1")
    second = _record("tx-2", first.digest)
    chain = build_chain((first, second))
    assert chain.verify()
    assert chain_reproducibility_digest(chain.records) == chain_reproducibility_digest(chain.records)
    assert chain_reproducibility_digest((second, first)) != chain_reproducibility_digest(chain.records)


def test_empty_chain_has_stable_genesis_fingerprint():
    assert chain_reproducibility_digest(()) == chain_reproducibility_digest(())
