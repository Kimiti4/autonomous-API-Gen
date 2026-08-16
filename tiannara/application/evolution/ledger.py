"""R2 -- causal evolution ledger (R2.6 first-entry wiring, R2.7.5 event authority).

Append-only, content-addressed, hash-chained evidence of the Evolution Engine's
decisions. R2.6 introduced the ``EvolutionRecord`` / ``SelectionRecord`` causal
chains; R2.7.5 makes the finer-grained ``EvolutionEvent`` chain authoritative
(Observation -> Evaluation -> Selection -> Result ...) and reduces the legacy
records to backward-compatible projections computed from events.

Backward compatibility (R2.3/R2.4/R2.6 tests preserved):
  * ``append(EvolutionRecord)`` / ``append_selection(payload)`` keep returning
    the same record ids, fix ``parent_link`` to chain, and ``chain_ok`` /
    ``verify_chain`` / ``verify_selection_chain`` continue to verify the
    *record* chains exactly as before.
  * Records are still persisted to ``ledger.jsonl`` / ``selections.jsonl``.

On top of that, every record append also projects an ``EvolutionEvent`` onto the
authoritative ``events.jsonl`` chain. New R2.8+ code reads ``events()``; legacy
callers keep reading records. ``EvolutionRecord`` / ``SelectionRecord`` are
projections *of* the event chain, exactly as required by the R2.7.5 migration.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.services.canonical import canonical_hash


def stable_isr_hash(isr: "object") -> str:
    """Stable ISR identity for ledger binding.

    MIGRATED (Phase-28 identity migration, ADR
    adr-phase28-identity-migration): previously a strip-``created_at``
    exclude-list over the full canonical serialization; now delegates to the
    semantic projection (``semantic_content_hash``), which excludes
    version/provenance/runtime by construction -- the same identity
    ``ISR.content_hash`` carries post-migration.
    """
    from constitutional_architecture.isr.semantics.projection import (
        semantic_content_hash,
    )

    return semantic_content_hash(isr)


class EvolutionRecord(BaseModel):
    observation_hash: str
    broken_hash: str
    operator: str
    hypothesis: str
    repaired_hash: str
    repaired_diff: tuple[str, ...] = Field(default_factory=tuple)
    validation: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    fitness_delta: float = 0.0
    decision: str = "accept"
    parent_link: str = ""
    # R2.4.0b: link the ISR mutation to the generated artifact it produced and the
    # runtime evidence it earned. Empty defaults keep R2.3 records valid.
    repaired_artifact_hash: str = ""
    runtime_evidence_hash: str = ""
    created_at: str = ""

    def record_id(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class SelectionRecord(BaseModel):
    """R2.6 -- an auditable record of one competitive-evolution decision.

    Stores the full ``SelectionDecision`` payload (every competing candidate,
    its gate verdict, fitness, the Pareto frontier, the selected candidate and
    the rationale) so the ledger captures *why* A was chosen over B/C.

    R2.7.5: a SelectionRecord is a backward-compatible projection of an
    ``EvolutionEvent`` (event_type ``candidate_selected`` /
    ``candidate_rejected``); the event chain is authoritative.
    """

    payload: dict
    parent_link: str = ""

    def record_id(self) -> str:
        return canonical_hash({"parent_link": self.parent_link, "payload": self.payload})


# -- R2.7.5: authoritative event chain -----------------------------------------

import enum


class EventType(str, enum.Enum):
    """Canonical event types for an evolution run. Extensible; the engine
    emits these instead of (or in addition to) ad-hoc record shapes."""

    __test__ = False

    OBSERVATION = "observation"
    ANCHOR = "anchor"  # R2.7.5-G: anchored protected/holdout test identity set
    MEASUREMENT = "measurement"  # R2.8.3: per-mutation detection verdict + attribution
    CANDIDATE_GENERATED = "candidate_generated"
    CANDIDATE_EVALUATED = "candidate_evaluated"
    GATE_EVALUATED = "gate_evaluated"
    CANDIDATE_SELECTED = "candidate_selected"
    CANDIDATE_REJECTED = "candidate_rejected"
    CANDIDATE_ACCEPTED = "candidate_accepted"
    COMPILATION = "compilation"
    EXECUTION = "execution"
    DELIVERY = "delivery"
    DEPLOYMENT = "deployment"
    FEEDBACK = "feedback"
    CERTIFICATION = "certification"  # R2.8.14: chain-anchored certification artifact
    GENERATION_COMPLETED = "generation_completed"  # R2.9.3: one generation of the search
    SCHEDULER_DECISION = "scheduler_decision"  # R2.9.5: search-budget allocation + evidence snapshot
    ISR_CAPABILITY_AUDIT = "isr_capability_audit"  # R2.10.1: signed capability/expressivity matrix
    PRIMITIVE_CONTRACT = "primitive_contract"  # R2.10.2: signed primitive/extension/compatibility contract


class EvolutionEvent(BaseModel):
    """Authoritative, append-only, hash-chained evolution event.

    ``event_hash`` is the content hash over every field except itself; the
    chain links ``parent_event_id`` to the *prior event's event_hash*, so
    tampering any field (or removing/duplicating an event) breaks
    ``verify_event_chain`` -- and a tampered root cascades to all successors.
    """

    __test__ = False

    model_config = ConfigDict(frozen=True)

    event_id: str
    evolution_id: str
    sequence: int
    event_type: EventType
    parent_event_id: str = ""
    subject_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    observation_hash: str = ""
    candidate_hash: str = ""
    isr_hash: str = ""
    artifact_hash: str = ""
    environment_hash: str = ""
    created_at: str = ""
    event_hash: str = ""

    def content(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data.pop("event_hash", None)
        return data

    def computed_hash(self) -> str:
        return canonical_hash(self.content())

    def is_intact(self) -> bool:
        return self.event_hash == self.computed_hash()


# -- projection functions (record -> event) -----------------------------------

def project_record(record: EvolutionRecord, evolution_id: str = "") -> EvolutionEvent:
    """Backward-compatible projection: an EvolutionRecord -> EvolutionEvent."""
    etype = (
        EventType.CANDIDATE_ACCEPTED if record.decision == "accept"
        else EventType.CANDIDATE_REJECTED
    )
    return EvolutionEvent(
        event_id=record.record_id(),
        evolution_id=evolution_id or f"evolution-{record.observation_hash[:8]}",
        sequence=0,
        event_type=etype,
        parent_event_id="",
        subject_id=record.repaired_hash,
        payload=record.model_dump(mode="json"),
        observation_hash=record.observation_hash,
        candidate_hash=record.repaired_hash,
        isr_hash=record.repaired_hash,
        artifact_hash=record.repaired_artifact_hash,
        environment_hash="",
        created_at=record.created_at,
    )


def project_selection(payload: dict, evolution_id: str = "") -> EvolutionEvent:
    """Backward-compatible projection: a SelectionRecord payload -> event."""
    selected = payload.get("selected_candidate_id")
    etype = (
        EventType.CANDIDATE_SELECTED if selected else EventType.CANDIDATE_REJECTED
    )
    return EvolutionEvent(
        event_id=canonical_hash({"payload": payload}),
        evolution_id=evolution_id or f"evolution-{str(selected or 'sel')[:8]}",
        sequence=0,
        event_type=etype,
        parent_event_id="",
        subject_id=str(selected or ""),
        payload=payload,
        observation_hash="",
        candidate_hash=selected or "",
        isr_hash="",
        artifact_hash="",
        environment_hash="",
        created_at="",
    )


# -- ledger --------------------------------------------------------------------

class EvolutionLedger:
    def __init__(self, root: str | None = None):
        self._root = root
        self._records: list[EvolutionRecord] = []
        self._ids: list[str] = []
        self._selection_records: list[SelectionRecord] = []
        self._selection_ids: list[str] = []
        self._path: str | None = None
        # R2.7.5: authoritative event log.
        self._events: list[EvolutionEvent] = []
        self._event_hashes: list[str] = []
        self._event_path: str | None = None
        if root:
            os.makedirs(root, exist_ok=True)
            self._path = os.path.join(root, "ledger.jsonl")
            self._event_path = os.path.join(root, "events.jsonl")

    @property
    def length(self) -> int:
        return len(self._records)

    @property
    def latest_id(self) -> str:
        return self._ids[-1] if self._ids else ""

    # -- backward-compatible record chain (unchanged semantics) ------------------

    def append(self, record: EvolutionRecord) -> str:
        parent = self.latest_id
        if record.parent_link != parent:
            record = record.model_copy(update={"parent_link": parent})
        record_id = record.record_id()
        self._records.append(record)
        self._ids.append(record_id)
        if self._path:
            entry = {"id": record_id, **record.model_dump(mode="json")}
            line = json.dumps(entry, sort_keys=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        # R2.7.5: authoritatively record the same decision as an EvolutionEvent
        # projection so the event chain is the single source of truth.
        self.append_event(
            project_record(record, evolution_id=self.latest_event_hash or ""),
            evolution_id=self.latest_event_hash or "",
        )
        return record_id

    def get(self, record_id: str) -> EvolutionRecord | None:
        for i, rid in enumerate(self._ids):
            if rid == record_id:
                return self._records[i]
        return None

    def chain_ok(self) -> bool:
        for i, record in enumerate(self._records):
            expected = self._ids[i - 1] if i > 0 else ""
            if record.parent_link != expected:
                return False
        return True

    def last_hash(self) -> str:
        """Record id of the most recently appended record ("" if empty)."""
        return self.latest_id

    def verify_chain(self) -> bool:
        """True iff every record's ``parent_link`` links to its predecessor."""
        return self.chain_ok()

    # -- backward-compatible selection sub-chain --------------------------------

    def append_selection(self, payload: dict) -> str:
        """Append an auditable selection decision; returns its record id."""
        parent = self._selection_ids[-1] if self._selection_ids else ""
        record = SelectionRecord(payload=payload, parent_link=parent)
        record_id = record.record_id()
        self._selection_records.append(record)
        self._selection_ids.append(record_id)
        if self._path:
            from pathlib import Path
            entry = {"id": record_id, **record.model_dump(mode="json")}
            line = json.dumps(entry, sort_keys=True)
            sel_path = Path(self._path).with_name("selections.jsonl")
            with open(sel_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        # R2.7.5: authoritatively record the selection as an EvolutionEvent.
        self.append_event(
            project_selection(payload, evolution_id=self.latest_event_hash or ""),
            evolution_id=self.latest_event_hash or "",
        )
        return record_id

    def get_selection(self, record_id: str) -> SelectionRecord | None:
        for i, rid in enumerate(self._selection_ids):
            if rid == record_id:
                return self._selection_records[i]
        return None

    @property
    def latest_selection_id(self) -> str:
        return self._selection_ids[-1] if self._selection_ids else ""

    def verify_selection_chain(self) -> bool:
        for i, record in enumerate(self._selection_records):
            expected = self._selection_ids[i - 1] if i > 0 else ""
            if record.parent_link != expected:
                return False
        return True

    # -- R2.7.5: authoritative event chain -------------------------------------

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def latest_event_hash(self) -> str:
        return self._event_hashes[-1] if self._event_hashes else ""

    def append_event(self, event: EvolutionEvent, *, evolution_id: str = "") -> str:
        """Append an event to the authoritative chain.

        Sets ``parent_event_id`` to the prior event's ``event_hash`` (cascade on
        tamper), assigns ``sequence``, computes ``event_hash``, and persists to
        ``events.jsonl`` when a root is configured. Returns the event_id.
        """
        parent = self.latest_event_hash
        seq = len(self._events)
        ev = event.model_copy(update={
            "parent_event_id": parent,
            "sequence": seq,
            "evolution_id": evolution_id or event.evolution_id,
        })
        # Finalize the event_id FIRST so the hash is computed over the final id
        # (projected events arrive with an id; direct-authored ones get a uuid).
        if not ev.event_id:
            ev = ev.model_copy(update={"event_id": uuid.uuid4().hex})
        ev = ev.model_copy(update={"event_hash": ev.computed_hash()})
        self._events.append(ev)
        self._event_hashes.append(ev.event_hash)
        if self._event_path:
            entry = {"id": ev.event_hash, **ev.model_dump(mode="json")}
            line = json.dumps(entry, sort_keys=True)
            with open(self._event_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return ev.event_id

    def get_event(self, event_id: str) -> EvolutionEvent | None:
        for ev in self._events:
            if ev.event_id == event_id:
                return ev
        return None

    def events(self) -> list[EvolutionEvent]:
        return list(self._events)

    def verify_event_chain(self) -> bool:
        """True iff every event links to its predecessor's event_hash and every
        event_hash is intact (tamper-evident, cascading on a tampered root)."""
        for i, ev in enumerate(self._events):
            if not ev.is_intact():
                return False
            expected_parent = self._event_hashes[i - 1] if i > 0 else ""
            if ev.parent_event_id != expected_parent:
                return False
        return True

    def verify_environment_binding(self) -> bool:
        """True iff all events share the anchor's environment_hash.

        R2.8.9/10: detects cross-evolution replay -- valid events from a
        different environment injected into this ledger will carry a different
        environment_hash than the anchor, breaking the binding.
        """
        if not self._events:
            return True
        anchor_env = self._events[0].environment_hash
        return all(ev.environment_hash == anchor_env for ev in self._events)

    def event_chain_ok(self) -> bool:
        return self.verify_event_chain()

    # -- R2.7.5-F: replay / reconstruction from durable files ------------------

    @classmethod
    def load(cls, root: str) -> "EvolutionLedger":
        """Reconstruct an in-memory ledger from its durable JSONL files.

        The event chain is authoritative: ``verify_event_chain`` re-derives
        integrity over the replayed events, so a tampered, deleted, duplicated,
        or re-ordered ``events.jsonl`` is detected on load. Records and
        selections are replayed as backward-compatible projections.
        """
        ledger = cls.__new__(cls)
        ledger._root = root
        ledger._records = []
        ledger._ids = []
        ledger._selection_records = []
        ledger._selection_ids = []
        ledger._events: list[EvolutionEvent] = []
        ledger._event_hashes = []
        from pathlib import Path

        root_path = Path(root)
        ledger._path = str(root_path / "ledger.jsonl")
        ledger._event_path = str(root_path / "events.jsonl")

        record_path = root_path / "ledger.jsonl"
        if record_path.exists():
            for line in record_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                rid = entry.pop("id", None)
                rec = EvolutionRecord(**entry)
                ledger._records.append(rec)
                ledger._ids.append(rid if rid else rec.record_id())

        event_path = root_path / "events.jsonl"
        if event_path.exists():
            for line in event_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                entry.pop("id", None)  # id was the event_hash; re-derive below
                ev = EvolutionEvent(**entry)
                ledger._events.append(ev)
                ledger._event_hashes.append(ev.event_hash)

        sel_path = root_path / "selections.jsonl"
        if sel_path.exists():
            for line in sel_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                sid = entry.pop("id", None)
                rec = SelectionRecord(**entry)
                ledger._selection_records.append(rec)
                ledger._selection_ids.append(sid if sid else rec.record_id())

        return ledger
