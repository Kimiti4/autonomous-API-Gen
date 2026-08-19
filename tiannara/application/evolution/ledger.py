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
import threading
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from constitutional_architecture.isr.semantics.projection import canonical_form
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
    VERIFICATION = "verification"  # R2.10.8: chain-addressable artifact verification result
    GENERATION_OUTCOME = "generation_outcome"  # R2.10.9: one campaign generation outcome (intent -> ISR -> compilation -> verification)
    CALIBRATION = "calibration"  # R2.10.31.1: one 31.1 calibration report (a measurement, never a certification)
    MATRIX = "matrix"  # R2.10.31.2: one 31.2 backend-matrix report (coverage and invariance, never throughput)
    TAXONOMY_CASE = "taxonomy_case"  # R2.10.31.3: one induced failure observation + its classifier disposition
    TAXONOMY_VALIDATION = "taxonomy_validation"  # R2.10.31.3: one 31.3 failure-taxonomy validation report
    SCALE_RAMP = "scale_ramp"  # R2.10.31.4: one 31.4 scale-ramp report (per-level gates + measured envelope)


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
        # R2.10.9: serialize concurrent campaign appends (parallel load keeps
        # the chain intact by construction — parent/sequence are assigned
        # under the lock).
        self._append_lock = threading.Lock()
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

        R2.10.9: concurrent appends (the campaign's parallel load) are
        serialized by ``_append_lock`` so parent/sequence assignment and the
        file append stay atomic — the chain cannot interleave.
        """
        with self._append_lock:
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

    def event_by_ref(self, event_id: str) -> EvolutionEvent | None:
        """Lookup by event reference (alias of ``get_event``) — the R2.10.8
        verifier cross-checks the claimed compilation event against the
        independently-recorded chain."""
        return self.get_event(event_id)

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

    # -- R2.10.5: generation records (the full delta is the content) -----------

    def record_generation(self, record: Any, *, evolution_id: str = "") -> str:
        """Record one universal-search generation as a MEASUREMENT event
        carrying the FULL canonical delta content.

        R2.10.5's headline: the final selected ISR must be reconstructable
        byte-exactly from the ledger alone. Each selected generation
        therefore records every edit's canonical ``new_gene`` content
        (``canonical_form``), not just the edit addresses — the recorded
        material is sufficient to replay the entire lineage from the
        initial ISR. ``record`` is duck-typed (generation, selected_delta,
        parent_semantic_hash, selected_candidate_hash, policy_resolved_from,
        feasible_count, population_size) so the ledger never imports the
        search module. Returns the event_id.
        """
        edits = sorted(record.selected_delta.edits, key=lambda e: (e.domain, e.gene_id))
        event = EvolutionEvent(
            event_id=(
                f"{evolution_id or 'universal'}-generation-{record.generation}-"
                f"{record.selected_delta.delta_id}"
            ),
            evolution_id=evolution_id or record.selected_delta.delta_id,
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=record.selected_candidate_hash,
            payload={
                "generation": record.generation,
                "parent_semantic_hash": record.parent_semantic_hash,
                "selected_candidate_hash": record.selected_candidate_hash,
                "policy_resolved_from": record.policy_resolved_from,
                "feasible_count": record.feasible_count,
                "population_size": record.population_size,
                "delta": {
                    "delta_id": record.selected_delta.delta_id,
                    "edits": [
                        {
                            "domain": edit.domain,
                            "gene_id": edit.gene_id,
                            "new_gene": canonical_form(edit.new_gene),
                        }
                        for edit in edits
                    ],
                },
            },
            isr_hash=record.parent_semantic_hash,
            candidate_hash=record.selected_candidate_hash,
        )
        self.append_event(event, evolution_id=evolution_id or record.selected_delta.delta_id)
        return event.event_id

    def recorded_deltas(self) -> tuple[dict, ...]:
        """The full canonical delta material of every recorded generation,
        in append order — the reconstruction input for R2.10.5's replay.
        Only generation records carry the ``delta`` payload key."""
        return tuple(
            ev.payload["delta"]
            for ev in self._events
            if ev.event_type is EventType.MEASUREMENT and "delta" in ev.payload
        )

    def event_chain_ok(self) -> bool:
        return self.verify_event_chain()

    # -- R2.10.6: compilation evidence (duck-typed, additive) -----------------

    def record_compilation(self, result: Any, *, evolution_id: str = "") -> str:
        """Chain-anchor one compilation on the authoritative event chain.

        ``result`` is duck-typed (artifact, isr_hash, target_id, backend_id,
        backend_version, artifact_hash, capability_coverage) so the ledger
        never imports the consumption-contract module — the R2.10.6 gate
        calls this through the duck-typed seam. The payload binds the ISR,
        the target, the backend, the artifact, and the explicit coverage
        declaration (support value + note per capability). Returns the
        event_id.
        """
        coverage = tuple(
            {
                "capability_id": item.capability_id,
                "support": item.support.value,
                "note": item.note,
            }
            for item in result.capability_coverage
        )
        evolution_id = evolution_id or f"compilation-{result.backend_id}"
        event = EvolutionEvent(
            event_id=(
                f"compilation-{result.backend_id}-{result.artifact_hash[:8]}"
            ),
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.COMPILATION,
            subject_id=result.isr_hash,
            payload={
                "isr_hash": result.isr_hash,
                "target_id": result.target_id,
                "backend_id": result.backend_id,
                "backend_version": result.backend_version,
                "artifact_hash": result.artifact_hash,
                "coverage": coverage,
            },
            isr_hash=result.isr_hash,
            candidate_hash=result.artifact_hash,
            artifact_hash=result.artifact_hash,
        )
        self.append_event(event, evolution_id=evolution_id)
        return event.event_id

    # -- R2.10.7: conformance evidence (duck-typed, additive) ------------------

    def record_conformance(self, report: Any, *, evolution_id: str = "") -> str:
        """Chain-anchor one backend conformance report on the authoritative
        event chain.

        ``report`` is duck-typed (backend_id, backend_version, conforms,
        failed_gates, capability_coverage, isr_semantic_hash_at_conformance)
        so the ledger never imports the conformance module — the R2.10.7
        evaluator calls this through the duck-typed seam. The payload binds
        the backend, its declared coverage summary, its verdict, and the ISR
        hash the report was produced against. Returns the event_id.
        """
        summary: dict[str, int] = {}
        for item in report.capability_coverage:
            summary[item.support.value] = summary.get(item.support.value, 0) + 1
        evolution_id = evolution_id or f"conformance-{report.backend_id}"
        isr_hash = report.isr_semantic_hash_at_conformance
        event = EvolutionEvent(
            event_id=(
                f"conformance-{report.backend_id}-{isr_hash[:8]}"
            ),
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id=isr_hash,
            payload={
                "backend_id": report.backend_id,
                "backend_version": report.backend_version,
                "conforms": report.conforms,
                "failed_gates": list(report.failed_gates),
                "isr_hash": isr_hash,
                "coverage_summary": summary,
            },
            isr_hash=isr_hash,
            candidate_hash=f"conformance-{report.backend_id}",
            artifact_hash="",
        )
        self.append_event(event, evolution_id=evolution_id)
        return event.event_id

    # -- R2.10.8: artifact verification results (duck-typed, additive) ---------

    def record_verification(
        self,
        *,
        artifact_hash: str,
        verified: bool,
        failures: tuple[str, ...] = (),
        evolution_id: str = "",
    ) -> str:
        """Chain-anchor one artifact verification verdict on the authoritative
        event chain.

        The R2.10.8 verifier records its independent verdict — never the
        compiler's — so a later reviewer can address the exact event that
        judged the artifact. The event binds the artifact identity, the
        verdict, and the failure inventory; appending after it is protected
        by the hash chain. Returns the event_id.
        """
        evolution_id = evolution_id or f"verification-{artifact_hash[:8]}"
        event = EvolutionEvent(
            event_id=f"verification-{artifact_hash[:8]}",
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.VERIFICATION,
            subject_id=artifact_hash,
            payload={
                "artifact_hash": artifact_hash,
                "verified": verified,
                "failures": list(failures),
            },
            isr_hash="",
            candidate_hash=artifact_hash,
            artifact_hash=artifact_hash,
        )
        self.append_event(event, evolution_id=evolution_id)
        return event.event_id

    # -- R2.10.9: campaign generation outcomes (duck-typed, additive) ----------

    def record_generation_outcome(
        self,
        intent_id: str,
        compiled: Any,
        verified: Any,
        *,
        campaign_id: str = "",
        evolution_id: str = "",
    ) -> str:
        """Chain-anchor one campaign generation outcome: the full provenance
        chain from intent through ISR, compilation, and verification.

        ``compiled`` / ``verified`` are duck-typed (artifact_hash, isr_hash,
        target_id, backend_id / verified, failures, verification_event_ref)
        so the ledger never imports the campaign package. The event binds
        intent -> ISR -> compilation -> verification and is the
        ``provenance_chain_ref`` of the outcome's metrics — every outcome is
        individually addressable on the chain. Returns the event_id.
        """
        event_id = (
            f"generation-{campaign_id}-{intent_id}-"
            f"{compiled.artifact_hash[:8]}"
        )
        evolution_id = evolution_id or f"campaign-{campaign_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.GENERATION_OUTCOME,
            subject_id=intent_id,
            payload={
                "campaign_id": campaign_id,
                "intent_id": intent_id,
                "isr_hash": compiled.isr_hash,
                "target_id": compiled.target_id,
                "backend_id": compiled.backend_id,
                "artifact_hash": compiled.artifact_hash,
                "compilation_event_ref": (
                    f"compilation-{compiled.backend_id}-"
                    f"{compiled.artifact_hash[:8]}"
                ),
                "verification_verified": verified.verified,
                "verification_event_ref": verified.verification_event_ref,
                "failures": list(verified.failures),
            },
            isr_hash=compiled.isr_hash,
            candidate_hash=compiled.artifact_hash,
            artifact_hash=compiled.artifact_hash,
        )
        self.append_event(event, evolution_id=evolution_id)
        return event.event_id

    def chain_complete(self, provenance_chain_ref: str) -> bool:
        """Per-outcome chain-completeness: the outcome event resolves AND its
        two chain-anchored references — the COMPILATION event and the
        VERIFICATION event — both resolve on the same ledger.

        R2.10.31.1's provenance gate is mechanical: an outcome without a
        resolvable compilation or verification anchor is unauditable and
        fails calibration. Global chain integrity (parent links, tamper
        cascade) is ``verify_event_chain``'s concern — this is the
        per-outcome check.
        """
        event = self.event_by_ref(provenance_chain_ref)
        if event is None:
            return False
        payload = event.payload or {}
        compilation_ref = payload.get("compilation_event_ref")
        verification_ref = payload.get("verification_event_ref")
        if not compilation_ref or not verification_ref:
            return False
        return (
            self.event_by_ref(compilation_ref) is not None
            and self.event_by_ref(verification_ref) is not None
        )

    # -- R2.10.31.1: calibration reports (measurement, not certification) -------

    def record_calibration(
        self,
        calibration_id: str,
        seed: int,
        baseline: Any,
        *,
        deterministic: bool,
        provenance_complete: bool,
        failures_classified: bool,
        verdict: str,
        declared_assumptions: tuple[str, ...] = (),
    ) -> str:
        """Chain-anchor one 31.1 calibration report.

        ``baseline`` is duck-typed (a JSON-safe payload of the baseline
        distribution — per-category outcomes and per-failure-class counts)
        so the ledger never imports the campaign package. The verdict is a
        MEASUREMENT (``READY_FOR_31_2`` / ``NOT_READY``) — there is no
        certification here; 31.5 certifies. The declared-stub limitation is
        recorded with the report, never hidden. Returns the event_id.
        """
        event_id = f"calibration-{calibration_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=event_id,
            sequence=0,
            event_type=EventType.CALIBRATION,
            subject_id=calibration_id,
            payload={
                "calibration_id": calibration_id,
                "seed": seed,
                "baseline": baseline,
                "deterministic_replay_verified": deterministic,
                "provenance_complete": provenance_complete,
                "failures_fully_classified": failures_classified,
                "calibration_verdict": verdict,
                "declared_assumptions": list(declared_assumptions),
            },
        )
        self.append_event(event, evolution_id=event_id)
        return event.event_id

    def record_matrix(
        self,
        matrix_id: str,
        cases: Any,
        *,
        invariance: bool,
        verdict: str,
        declared_assumptions: tuple[str, ...] = (),
    ) -> str:
        """Chain-anchor one 31.2 backend-matrix report.

        ``cases`` is duck-typed (a JSON-safe list of per-case dispositions —
        intent/backend/disposition/hashes/unsupported semantics/failure
        class/evidence refs) so the ledger never imports the campaign
        package. The verdict is a MEASUREMENT (``READY_FOR_31_3`` /
        ``NOT_READY``) — there is no certification here; 31.5 certifies.
        The 31.1 declared-stub assumption is carried on the event, never
        dropped. Returns the event_id.
        """
        event_id = f"matrix-{matrix_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=event_id,
            sequence=0,
            event_type=EventType.MATRIX,
            subject_id=matrix_id,
            payload={
                "matrix_id": matrix_id,
                "case_count": len(cases),
                "cases": cases,
                "cross_backend_invariance_held": invariance,
                "verdict": verdict,
                "declared_assumptions": list(declared_assumptions),
            },
        )
        self.append_event(event, evolution_id=event_id)
        return event.event_id

    def record_taxonomy_case(
        self, observation: Any, disposition: Any
    ) -> str:
        """Chain-anchor one 31.3 failure observation + its classifier
        disposition.

        ``observation`` / ``disposition`` are duck-typed (JSON-safe payloads
        built by the campaign package; the ledger never imports it) so every
        induced failure and its disposition are individually addressable
        and the whole validation is replayable. Returns the event_id.
        """
        event_id = f"taxonomy-case-{observation['observation_id']}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=f"taxonomy-validation",
            sequence=0,
            event_type=EventType.TAXONOMY_CASE,
            subject_id=observation["intent_id"],
            payload={
                "observation": observation,
                "disposition": disposition,
            },
        )
        self.append_event(event, evolution_id="taxonomy-validation")
        return event.event_id

    def record_taxonomy_validation(
        self,
        validation_id: str,
        cases: Any,
        *,
        all_correct: bool,
        no_conflation: bool,
        verdict: str,
        declared_assumptions: tuple[str, ...] = (),
    ) -> str:
        """Chain-anchor one 31.3 taxonomy-validation report.

        ``cases`` is duck-typed (a JSON-safe list of per-case dispositions)
        so the ledger never imports the campaign package. The verdict is a
        MEASUREMENT (``READY_FOR_31_4`` / ``NOT_READY``) — there is no
        certification here; 31.5 certifies. The 31.1 declared-stub
        assumption is carried on the event, never dropped. Returns the
        event_id.
        """
        event_id = f"taxonomy-{validation_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=event_id,
            sequence=0,
            event_type=EventType.TAXONOMY_VALIDATION,
            subject_id=validation_id,
            payload={
                "validation_id": validation_id,
                "case_count": len(cases),
                "cases": cases,
                "all_correct": all_correct,
                "no_conflation": no_conflation,
                "verdict": verdict,
                "declared_assumptions": list(declared_assumptions),
            },
        )
        self.append_event(event, evolution_id=event_id)
        return event.event_id

    def record_scale_ramp(
        self,
        ramp_id: str,
        per_level: Any,
        *,
        scale_envelope: int,
        ramp_complete: bool,
        envelope_hit_at: int | None,
        envelope_reason: str | None,
        corpus_growth_strategy: str,
        rerun_subset: Any,
        reachable_top: int,
        scheduled_levels: Any,
        level_budget_seconds: int,
        taxonomy_exercised: bool,
        verdict: str,
        declared_assumptions: tuple[str, ...] = (),
    ) -> str:
        """Chain-anchor one 31.4 scale-ramp report.

        ``per_level`` is duck-typed (a JSON-safe list of per-level
        results — scale/counts/tallies/gates/envelope/duration) so the
        ledger never imports the campaign package. The report records the
        measured envelope and the declared methodology (growth strategy,
        rerun subset, reachable top, per-level budget) — the ramp is
        reproducible because its methodology is on the chain. The verdict
        is a MEASUREMENT (``READY_FOR_31_5`` / ``NOT_READY``) — there is
        no certification here; 31.5 certifies. Returns the event_id.
        """
        event_id = f"scale-ramp-{ramp_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=event_id,
            sequence=0,
            event_type=EventType.SCALE_RAMP,
            subject_id=ramp_id,
            payload={
                "ramp_id": ramp_id,
                "per_level": per_level,
                "scale_envelope": scale_envelope,
                "ramp_complete": ramp_complete,
                "envelope_hit_at": envelope_hit_at,
                "envelope_reason": envelope_reason,
                "corpus_growth_strategy": corpus_growth_strategy,
                "rerun_subset": rerun_subset,
                "reachable_top": reachable_top,
                "scheduled_levels": list(scheduled_levels),
                "level_budget_seconds": level_budget_seconds,
                "taxonomy_exercised": taxonomy_exercised,
                "scale_ramp_verdict": verdict,
                "declared_assumptions": list(declared_assumptions),
            },
        )
        self.append_event(event, evolution_id=event_id)
        return event.event_id

    def record_certification(
        self,
        certification_id: str,
        verdict: str,
        certification_statement: str,
        dimensions: Any,
        *,
        measured_envelope: int,
        declared_assumptions: tuple[str, ...] = (),
        evidence_chain_refs: Any = (),
        content_hash: str = "",
    ) -> str:
        """Chain-anchor one 31.5 CertificationArtifact.

        ``dimensions`` is duck-typed (a JSON-safe list of dimension
        payloads — dimension_id/verdict/evidence_refs/bounds) so the
        ledger never imports the campaign package. The event is the
        certification itself, not a document that describes it: the
        content hash commits to the evidence references, and every claim
        is independently reconstructible from the chain. Returns the
        event_id.
        """
        event_id = f"certification-{certification_id}"
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=event_id,
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id=certification_id,
            payload={
                "certification_id": certification_id,
                "verdict": verdict,
                "certification_statement": certification_statement,
                "dimensions": dimensions,
                "measured_envelope": measured_envelope,
                "declared_assumptions": list(declared_assumptions),
                "evidence_chain_refs": list(evidence_chain_refs),
                "content_hash": content_hash,
            },
        )
        self.append_event(event, evolution_id=event_id)
        return event.event_id

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
        ledger._append_lock = threading.Lock()
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
