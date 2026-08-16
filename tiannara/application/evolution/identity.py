"""R2.9.7 -- Three-identity reproducibility model.

Constitutional separation of ISR identity into three concerns that must never
be conflated:

    semantic_hash          = H(canonical(Semantic Architecture))
    provenance_identity    = lineage (parent, mutation source, evolution, created_at)
    runtime_execution_id   = execution-instance identity

The recurring defect (R2.3/4/8/9.4/9.5/9.6) was folding volatile provenance
(``created_at``, stamped by ``ISR.with_system``) into the semantic content
hash, making the constitutional "source of truth" unstable across runs. This
module makes that conflation structurally impossible going forward.

The semantic hash is computed by an INCLUSION-based projection: the projector
explicitly defines what architecture IS on a substrate, rather than excluding
known-volatile fields. Nested provenance/runtime data cannot leak because it is
never part of the architectural projection. The canonical serializer has no
``default=str`` fallback -- unhandled types raise, forcing explicit
canonicalization instead of hiding representation differences.

This module is ADDITIVE: it reads the ISR and never mutates the Phase-28 model.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class CanonicalizationError(TypeError):
    """Raised when a value has no explicit canonical form.

    Deliberate: no ``default=str`` fallback. Representation differences must be
    canonicalized explicitly, never papered over.
    """


@dataclass(frozen=True)
class ProvenanceIdentity:
    """Lineage identity -- where the ISR came from. May be volatile."""

    parent_hash: str | None = None
    created_at: str | None = None
    mutation_source: str | None = None
    evolution_id: str | None = None


@dataclass(frozen=True)
class ISRIdentity:
    """The three-identity separation for one ISR.

    ``semantic_hash`` is the canonical reproducibility identity -- computed over
    architectural content only. ``provenance`` and ``runtime_execution_id`` are
    separate identities, never folded into it.
    """

    semantic_hash: str
    provenance: ProvenanceIdentity
    runtime_execution_id: str | None = None


# ---------------------------------------------------------------------------
# Canonical serialization -- explicit, no default=str
# ---------------------------------------------------------------------------

def canonicalize(value: Any) -> str:
    return json.dumps(_canonical_form(value), sort_keys=True, separators=(",", ":"))


def _canonical_form(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return repr(value)                      # deterministic float rendering
    if isinstance(value, Enum):
        return {"__enum__": value.value}
    if isinstance(value, dict):
        return {str(k): _canonical_form(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_form(v) for v in value]
    if isinstance(value, (set, frozenset)):
        forms = sorted(canonicalize(_canonical_form(v)) for v in value)
        return [json.loads(f) for f in forms]   # deterministic set ordering
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_form(asdict(value))
    raise CanonicalizationError(f"no canonical form for {type(value).__name__}")


# ---------------------------------------------------------------------------
# Semantic projection -- inclusion-based, substrate-replaceable
# ---------------------------------------------------------------------------

class SemanticProjector(Protocol):
    """Projects an ISR to its canonical Semantic Architecture.

    Inclusion-based: explicitly defines what architecture IS on a substrate.
    Each architectural element is projected to its canonical architectural form;
    provenance and runtime data are never projected. Replaceable per substrate
    (R2.10's Component/Requirement graphs get their own projector).
    """

    def project(self, isr: Any) -> dict: ...


class FSMSemanticProjector:
    """Semantic projection for the FSM / order-workflow substrate.

    The architectural schema on this substrate: workflows (states, transitions:
    from/to/trigger/guard/actions/metadata), modules, and constraints. Only
    these are projected; provenance and runtime data are absent from the schema
    by construction, so a volatile field nested anywhere cannot leak into the
    semantic hash.
    """

    SCHEMA = "fsm.semantic.v1"

    def project(self, isr: Any) -> dict:
        system = isr.system
        return {
            "schema": self.SCHEMA,
            "system_id": system.id,
            "system_name": system.name,
            "constraints": [self._scalar(c) for c in getattr(system, "constraints", ()) or ()],
            "modules": sorted(
                (
                    {
                        "id": module.id,
                        "name": module.name,
                        "workflows": sorted(
                            (self._workflow(wf) for wf in module.workflows),
                            key=canonicalize,
                        ),
                    }
                    for module in system.modules
                ),
                key=canonicalize,
            ),
        }

    def _workflow(self, wf: Any) -> dict:
        return {
            "id": wf.id,
            "name": wf.name,
            "states": [self._state(s) for s in wf.states],
            "transitions": sorted(
                (self._transition(t) for t in wf.transitions),
                key=canonicalize,
            ),
        }

    def _state(self, state: Any) -> dict:
        return {
            "id": state.id,
            "name": state.name,
            "state_type": self._scalar(state.state_type),
            "description": state.description,
            "entry_actions": [self._scalar(a) for a in getattr(state, "entry_actions", ()) or ()],
            "exit_actions": [self._scalar(a) for a in getattr(state, "exit_actions", ()) or ()],
            "metadata": {str(k): self._scalar(v) for k, v in state.metadata.items()},
        }

    def _transition(self, transition: Any) -> dict:
        return {
            "id": transition.id,
            "name": transition.name,
            "from_state_id": transition.from_state_id,
            "to_state_id": transition.to_state_id,
            "trigger": transition.trigger,
            "guard_condition": transition.guard_condition,
            "actions": [self._scalar(a) for a in transition.actions],
            "description": transition.description,
            "metadata": {str(k): self._scalar(v) for k, v in transition.metadata.items()},
        }

    @staticmethod
    def _scalar(value: Any) -> Any:
        return _canonical_form(value)


# ---------------------------------------------------------------------------
# Identity extraction
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdentityExtractor:
    """Computes the three identities from an ISR via semantic projection."""

    projector: SemanticProjector = FSMSemanticProjector()

    RUNTIME_FIELDS = ("runtime_execution_id", "execution_id", "run_id")

    def extract(self, isr: Any) -> ISRIdentity:
        return ISRIdentity(
            semantic_hash=self.semantic_hash(isr),
            provenance=self._provenance(isr),
            runtime_execution_id=self._runtime_id(isr),
        )

    def semantic_hash(self, isr: Any) -> str:
        architecture = self.projector.project(isr)
        return hashlib.sha256(
            canonicalize(architecture).encode("utf-8")
        ).hexdigest()

    def _provenance(self, isr: Any) -> ProvenanceIdentity:
        prov = getattr(isr, "provenance", None)
        if prov is None:
            return ProvenanceIdentity()
        created_at = getattr(prov, "created_at", None)
        return ProvenanceIdentity(
            parent_hash=getattr(prov, "parent_hash", None),
            created_at=created_at.isoformat() if isinstance(created_at, datetime)
            else (str(created_at) if created_at is not None else None),
            mutation_source=getattr(prov, "mutation_description", None)
            or getattr(prov, "mutation_source", None),
            evolution_id=getattr(prov, "evolution_run_id", None)
            or getattr(prov, "evolution_id", None),
        )

    def _runtime_id(self, isr: Any) -> str | None:
        for name in self.RUNTIME_FIELDS:
            value = getattr(isr, name, None)
            if value is not None:
                return str(value)
        return None


@dataclass(frozen=True)
class RuntimeTagged:
    """A runtime identity attached to an ISR WITHOUT mutating the model.

    The Phase-28 ISR carries no runtime field; the audit must still be able to
    demonstrate that a runtime identity slot is separate from (and never folded
    into) the semantic hash. This wrapper delegates the architectural surface
    (``system``/``provenance``) and exposes the runtime identity -- additive,
    never touching the ISR object itself.
    """

    isr: Any
    runtime_execution_id: str = ""

    @property
    def system(self) -> Any:
        return self.isr.system

    @property
    def provenance(self) -> Any:
        return getattr(self.isr, "provenance", None)


def tag_runtime(isr: Any, run_id: str) -> RuntimeTagged:
    return RuntimeTagged(isr, run_id)


def semantic_equivalent(
    a: Any, b: Any, extractor: IdentityExtractor | None = None
) -> bool:
    """Architectural equivalence, independent of provenance and runtime."""
    extractor = extractor or IdentityExtractor()
    return extractor.semantic_hash(a) == extractor.semantic_hash(b)