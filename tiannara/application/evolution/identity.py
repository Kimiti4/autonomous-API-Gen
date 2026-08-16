"""R2.9.7 -- Three-identity reproducibility model (MIGRATED).

Constitutional separation of ISR identity into three concerns that must never
be conflated:

    semantic_hash          = H(canonical(Semantic Architecture))
    provenance_identity    = lineage (parent, mutation source, evolution, created_at)
    runtime_execution_id   = execution-instance identity

The recurring defect (R2.3/4/8/9.4/9.5/9.6) was folding volatile provenance
(``created_at``, stamped by ``ISR.with_system``) into the semantic content
hash, making the constitutional "source of truth" unstable across runs.

PHASE-28 IDENTITY MIGRATION (ADR: adr-phase28-identity-migration): the
canonical semantic projection now lives in
``constitutional_architecture.isr.semantics.projection`` as the single source
of truth. ``canonicalize``, ``CanonicalizationError``, and
``FSMSemanticProjector.project`` delegate there; ``ISR.content_hash`` computes
the same identity, so ``semantic_hash == content_hash`` holds on every
substrate and ``content_reproducible`` flips to ``true``.

This module is ADDITIVE: it reads the ISR and never mutates the Phase-28 model.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from constitutional_architecture.isr.semantics.projection import (
    CanonicalizationError,
    canonicalize,
    project_semantic_architecture,
)

__all__ = [
    "CanonicalizationError",
    "FSMSemanticProjector",
    "ISRIdentity",
    "IdentityExtractor",
    "ProvenanceIdentity",
    "RuntimeTagged",
    "SemanticProjector",
    "canonicalize",
    "semantic_equivalent",
    "tag_runtime",
]


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
# Semantic projection -- single source of truth in constitutional_architecture
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

    MIGRATED: delegates to the full architectural projection
    (``project_semantic_architecture``), the single source of truth. The
    projection is the whole ``system`` tree (workflows, states, transitions,
    modules, constraints, entities, services, policies, deployment ...),
    canonicalized recursively; provenance and runtime data are absent from the
    schema by construction, so a volatile field nested anywhere cannot leak
    into the semantic hash. Post-migration, ``semantic_hash == content_hash``.
    """

    SCHEMA = "fsm.semantic.v1"

    def project(self, isr: Any) -> dict:
        return project_semantic_architecture(isr)


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
