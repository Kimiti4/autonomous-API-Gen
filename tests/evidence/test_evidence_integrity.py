"""R2.8.9 -- Evidence integrity tests."""
import pytest

from tiannara.evidence import (
    Anchor,
    EvidenceChain,
    EvidenceChainBuilder,
    ViolationClass,
    verify_chain,
)


def _build():
    b = EvidenceChainBuilder(epoch=1)
    b.append("mutation", {"id": "m1", "seed": 7})
    b.append("execution", {"ok": True, "tests": 3})
    b.append("measurement", {"score": 1.0, "detected": True})
    return b.build()


def test_valid_chain_verifies():
    chain = _build()
    result = verify_chain(chain)
    assert result.valid
    assert result.violations == ()


def test_empty_chain_verifies():
    chain = EvidenceChain(())
    result = verify_chain(chain)
    assert result.valid
    assert result.head_hash == "0" * 64


def test_modification_detected():
    chain = _build()
    ev = chain.events[1]
    tampered = ev.__class__(
        ev.event_type, ev.sequence, ev.epoch,
        {"ok": False, "tests": 3},  # payload changed but content_hash not recomputed
        ev.content_hash, ev.prev_chain_hash, ev.chain_hash,
    )
    events = list(chain.events)
    events[1] = tampered
    result = verify_chain(EvidenceChain(tuple(events)))
    assert not result.valid
    assert any(v.cls == ViolationClass.MODIFICATION for v in result.violations)


def test_deletion_detected():
    chain = _build()
    events = [chain.events[0], chain.events[2]]
    result = verify_chain(EvidenceChain(tuple(events)))
    assert not result.valid
    assert any(v.cls == ViolationClass.DELETION for v in result.violations)


def test_duplication_detected():
    chain = _build()
    events = [chain.events[0], chain.events[1], chain.events[1], chain.events[2]]
    result = verify_chain(EvidenceChain(tuple(events)))
    assert not result.valid
    assert any(v.cls == ViolationClass.DUPLICATION for v in result.violations)


def test_reordering_detected():
    chain = _build()
    events = [chain.events[0], chain.events[2], chain.events[1]]
    result = verify_chain(EvidenceChain(tuple(events)))
    assert not result.valid
    assert any(v.cls == ViolationClass.REORDERING for v in result.violations)


def test_stale_evidence_detected():
    chain = _build()
    result = verify_chain(chain, latest_epoch=2)
    assert not result.valid
    assert any(v.cls == ViolationClass.STALE for v in result.violations)


def test_anchor_catches_middle_delete_reforge():
    chain = _build()
    anchor = Anchor.of(1, chain)
    events = [chain.events[0], chain.events[2]]
    result = verify_chain(EvidenceChain(tuple(events)), anchor=anchor)
    assert not result.valid


def test_anchor_passes_for_unchanged_chain():
    chain = _build()
    anchor = Anchor.of(1, chain)
    result = verify_chain(chain, anchor=anchor)
    assert result.valid


def test_chain_hash_changes_on_any_edit():
    b1 = EvidenceChainBuilder(epoch=1)
    b1.append("event", {"a": 1})
    c1 = b1.build()

    b2 = EvidenceChainBuilder(epoch=1)
    b2.append("event", {"a": 2})
    c2 = b2.build()

    assert c1.head_hash() != c2.head_hash()
