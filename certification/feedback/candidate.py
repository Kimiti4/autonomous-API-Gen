"""EvolutionCandidate — the governed variant abstraction for self-repair.

Backend variation is the first real evolution dimension: the ISR remains the
constitutional source of truth (candidate.isr_hash == parent.isr_hash), and the
candidate differs only in its compilation strategy (backend_id).

Future variant kinds (genome_variant, configuration_variant,
deployment_variant, security_variant, architecture_variant) plug into the same
candidate mechanism without redesigning the evolution engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

VARIANT_KIND_BACKEND_SWAP = "backend_swap"
ORIGIN_EVOLVED = "evolved"
ORIGIN_REFERENCE = "reference"

PROVENANCE_GOVERNED_REPAIR = "campaign_b.governed_repair"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvolutionCandidate:
    """A distinct, independently-measurable evolved candidate.

    Never rewrites the parent trial — it is a NEW trial with its own identity,
    keeping the exact parent lineage.

    D3 contract: carries the full lineage (parent_trial_id, parent_backend_id,
    parent_candidate_id when chained), the constitutional hashes it preserves,
    the selected alternate backend, and provenance metadata.
    """
    parent_trial_id: str
    intent_id: str
    isr_hash: str
    genome_hash: str
    backend_id: str
    candidate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variant_kind: str = VARIANT_KIND_BACKEND_SWAP
    origin: str = ORIGIN_EVOLVED
    reason: str = ""
    parent_candidate_id: str | None = None
    # D3 additions — audit context.
    parent_backend_id: str = ""
    provenance: str = PROVENANCE_GOVERNED_REPAIR
    created_at: str = field(default_factory=_utcnow)

    def lineage(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "parent_trial_id": self.parent_trial_id,
            "parent_candidate_id": self.parent_candidate_id,
            "intent_id": self.intent_id,
            "isr_hash": self.isr_hash,
            "genome_hash": self.genome_hash,
            "parent_backend_id": self.parent_backend_id,
            "backend_id": self.backend_id,
            "variant_kind": self.variant_kind,
            "origin": self.origin,
            "provenance": self.provenance,
            "reason": self.reason,
            "created_at": self.created_at,
        }
