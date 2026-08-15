"""R2.7.5-C/D/E/F -- authoritative event ledger: integrity, projections,
backward-compatible record chain, and replay-from-file.

Covers:
  * append_event chain-links by event_hash (cascade on tamper).
  * payload / hash tampering breaks verify_event_chain.
  * append(EvolutionRecord) / append_selection project the right event_type and
    carry the record's payload + causal hashes (record -> event projection).
  * projection equivalence: project_record(record) round-trips to the same
    event the ledger emits for append(record).
  * deterministic reconstruction: identical records -> identical event hashes.
  * replay from durable files detects tampering / deletion while leaving the
    legacy record chain intact (event chain is authoritative).
"""
from __future__ import annotations

import json

import pytest

from tiannara.application.evolution.ledger import (
    EvolutionEvent,
    EvolutionLedger,
    EvolutionRecord,
    EventType,
    project_record,
    project_selection,
)


def _rec(decision: str = "accept") -> EvolutionRecord:
    return EvolutionRecord(
        observation_hash="o1", broken_hash="b1", operator="transition_restoration",
        hypothesis="h", repaired_hash="r1", repaired_diff=(),
        validation=(("test", "pass"),), fitness_delta=1.0, decision=decision,
        repaired_artifact_hash="art1", created_at="2026-01-01",
    )


def _event(etype: EventType, payload: dict | None = None) -> EvolutionEvent:
    return EvolutionEvent(
        event_id="",
        evolution_id="e1",
        sequence=0,
        event_type=etype,
        payload=payload or {},
        observation_hash="o1",
        candidate_hash="r1",
    )


# -- authoritative event chain -------------------------------------------------

def test_append_event_chain_links_by_hash():
    ledger = EvolutionLedger()
    e1 = _event(EventType.OBSERVATION, {"t": 1})
    e2 = _event(EventType.CANDIDATE_EVALUATED, {"t": 2})
    ledger.append_event(e1)
    ledger.append_event(e2)
    events = ledger.events()
    assert len(events) == 2
    assert events[0].sequence == 0 and events[1].sequence == 1
    # parent link is the predecessor's event_hash (cascade on tamper)
    assert events[1].parent_event_id == events[0].event_hash
    assert ledger.verify_event_chain()


def test_event_hash_changes_on_payload_change():
    e = _event(EventType.GATE_EVALUATED, {"gate": "regression", "passed": True})
    h0 = e.computed_hash()
    e_tampered = e.model_copy(update={"payload": {"gate": "regression", "passed": False}})
    assert e_tampered.computed_hash() != h0
    # the stored hash no longer matches content -> not intact
    stored = e.model_copy(update={"event_hash": h0})
    assert stored.is_intact()


def test_tamper_and_deletion_break_chain_on_replay(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    ledger.append(_rec("accept"))
    ledger.append(_rec("reject"))
    ledger.append(_rec("accept"))
    assert ledger.verify_event_chain()
    events_path = tmp_path / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3

    # (1) tamper a payload in the durable file -> integrity fails on reload,
    #     while the legacy record chain (untouched) still verifies.
    tampered = json.loads(lines[0])
    tampered["payload"]["decision"] = "mutated"
    lines[0] = json.dumps(tampered)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    replay = EvolutionLedger.load(str(tmp_path))
    assert not replay.verify_event_chain()
    assert replay.verify_chain()  # records untouched

    # reset file, then (2) delete a middle event -> linkage gap -> fail.
    good = ledger.events()
    events_path.write_text(
        "\n".join(
            json.dumps({"id": ev.event_hash, **ev.model_dump(mode="json")})
            for ev in good
        ) + "\n",
        encoding="utf-8",
    )
    kept = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    del kept[1]  # drop the middle event; successor's parent link now dangles
    (tmp_path / "events.jsonl").write_text("\n".join(kept) + "\n", encoding="utf-8")
    replay2 = EvolutionLedger.load(str(tmp_path))
    assert not replay2.verify_event_chain()


def test_cascade_linkage_by_hash():
    """A tampered root cascades: successors' parent_event_id no longer matches
    the (recomputed) root hash."""
    e1 = _event(EventType.OBSERVATION, {"x": 1})
    e2 = _event(EventType.CANDIDATE_EVALUATED, {"y": 2})
    root_hash = e1.computed_hash()
    e2_linked = e2.model_copy(update={"parent_event_id": root_hash})
    assert e2_linked.parent_event_id == e1.computed_hash()
    tampered_hash = e1.model_copy(update={"payload": {"x": 999}}).computed_hash()
    assert tampered_hash != root_hash
    assert e2_linked.parent_event_id == root_hash != tampered_hash


# -- record -> event projection ------------------------------------------------

def test_record_append_projects_candidate_event():
    ledger = EvolutionLedger()
    rid = ledger.append(_rec("accept"))
    assert rid  # record id returned (backward compat)
    assert ledger.length == 1
    assert ledger.chain_ok()  # record chain still works
    ev = ledger.events()[-1]
    assert ev.event_type == EventType.CANDIDATE_ACCEPTED
    assert ev.observation_hash == "o1"
    assert ev.candidate_hash == "r1"
    assert ev.isr_hash == "r1"
    assert ev.artifact_hash == "art1"
    assert ev.subject_id == "r1"
    assert ev.payload["decision"] == "accept"
    assert ev.event_id == rid  # projected event is traceable to its record


def test_record_append_rejected_records_rejected_event():
    ledger = EvolutionLedger()
    ledger.append(_rec("reject"))
    assert ledger.events()[-1].event_type == EventType.CANDIDATE_REJECTED


def test_selection_append_projects_selection_event():
    ledger = EvolutionLedger()
    sel_id_chosen = ledger.append_selection({"selected_candidate_id": "cand-1", "candidates": []})
    ev = ledger.events()[-1]
    assert ev.event_type == EventType.CANDIDATE_SELECTED
    assert ev.subject_id == "cand-1"
    assert ev.candidate_hash == "cand-1"
    assert sel_id_chosen  # backward-compat selection id

    sel_id_none = ledger.append_selection({"selected_candidate_id": None, "candidates": []})
    ev2 = ledger.events()[-1]
    assert ev2.event_type == EventType.CANDIDATE_REJECTED
    assert sel_id_none


# -- projection equivalence + determinism --------------------------------------

def test_projection_equivalence_record_to_event():
    """project_record(record) round-trips to the same event append(record) emits."""
    record = _rec("accept")
    l1 = EvolutionLedger()
    l1.append(record)
    emitted = l1.events()[-1]

    l2 = EvolutionLedger()
    l2.append_event(project_record(record))
    projected = l2.events()[-1]

    assert emitted.event_hash == projected.event_hash
    assert emitted.observation_hash == projected.observation_hash


def test_projection_equivalence_selection_to_event():
    payload = {"selected_candidate_id": "cand-1", "candidates": [], "rationale": "r"}
    l1 = EvolutionLedger()
    l1.append_selection(payload)
    emitted = l1.events()[-1]

    l2 = EvolutionLedger()
    l2.append_event(project_selection(payload))
    projected = l2.events()[-1]

    assert emitted.event_hash == projected.event_hash


def test_deterministic_reconstruction_same_records_same_hashes():
    recs = [_rec("accept"), _rec("reject"), _rec("accept")]
    l1 = EvolutionLedger()
    for r in recs:
        l1.append(r)
    l2 = EvolutionLedger()
    for r in recs:
        l2.append(r)
    assert [e.event_hash for e in l1.events()] == [e.event_hash for e in l2.events()]
    assert l1.verify_event_chain() and l2.verify_event_chain()


def test_replay_reconstructs_event_sequence(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    recs = [_rec("accept"), _rec("accept")]
    for r in recs:
        ledger.append(r)
    replay = EvolutionLedger.load(str(tmp_path))
    assert len(replay.events()) == 2
    assert [e.event_type for e in replay.events()] == [
        EventType.CANDIDATE_ACCEPTED,
        EventType.CANDIDATE_ACCEPTED,
    ]
    assert replay.verify_event_chain()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
