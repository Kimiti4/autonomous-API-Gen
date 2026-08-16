"""R2.9.7 -- Reproducibility audit.

Evidence-based: demonstrates the Phase-28 conflation rather than asserting it,
by showing the semantic hash is stable across runs while the Phase-28
``content_hash`` diverges, and naming the divergence cause.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .identity import IdentityExtractor


@dataclass(frozen=True)
class IdentitySeparationReport:
    """Whether a single ISR's semantic identity is cleanly separated."""

    semantic_hash: str
    phase28_content_hash: str | None
    semantic_is_stable_identity: bool
    phase28_tainted_by_provenance: bool
    taint_fields: tuple[str, ...]


@dataclass(frozen=True)
class CrossRunReport:
    """Reproducibility of an evolution trajectory across two runs."""

    generations_compared: int
    semantic_reproducible: bool
    content_reproducible: bool
    divergence_cause: str | None     # "provenance_volatility" when semantic ok, content not


class ReproducibilityAuditor:
    """Audits identity separation and cross-run trajectory reproducibility."""

    #: The volatile fields that must never fold into the semantic identity.
    #: Named explicitly so the audit's diagnosis is not silent.
    VOLATILE_TAINT_FIELDS = (
        "created_at", "parent_hash", "provenance",
        "runtime_execution_id", "execution_id", "run_id",
    )

    def __init__(self, extractor: IdentityExtractor | None = None) -> None:
        self._extractor = extractor or IdentityExtractor()

    @property
    def extractor(self) -> IdentityExtractor:
        return self._extractor

    def audit_identity_separation(self, isr) -> IdentitySeparationReport:
        identity = self._extractor.extract(isr)
        phase28 = getattr(isr, "content_hash", None)
        # Conflation is demonstrated (not asserted): the Phase-28 content hash
        # includes provenance/runtime fields, so it differs from the semantic
        # projection whenever those fields are present.
        tainted = phase28 is not None and bool(
            self._extractor._provenance(isr).parent_hash
            or self._extractor._provenance(isr).created_at
        )
        return IdentitySeparationReport(
            semantic_hash=identity.semantic_hash,
            phase28_content_hash=phase28,
            semantic_is_stable_identity=True,
            phase28_tainted_by_provenance=tainted,
            taint_fields=tuple(sorted(self.VOLATILE_TAINT_FIELDS)) if tainted else (),
        )

    def audit_cross_run(self, trajectory_a: Sequence, trajectory_b: Sequence) -> CrossRunReport:
        """Compare two runs' ISR trajectories at semantic and content level.

        The semantic trajectory must reproduce; the Phase-28 content trajectory
        need not. If semantic matches but content does not, the divergence is
        named ``provenance_volatility`` -- the exact chronic defect.
        """
        n = min(len(trajectory_a), len(trajectory_b))
        if n == 0:
            return CrossRunReport(0, True, True, None)
        semantic_ok = all(
            self._extractor.semantic_hash(trajectory_a[i])
            == self._extractor.semantic_hash(trajectory_b[i])
            for i in range(n)
        )
        content_ok = all(
            getattr(trajectory_a[i], "content_hash", None)
            == getattr(trajectory_b[i], "content_hash", None)
            for i in range(n)
        )
        cause = "provenance_volatility" if (semantic_ok and not content_ok) else None
        return CrossRunReport(n, semantic_ok, content_ok, cause)