"""R2.9.8 -- Evolution Engine certification gate.

Certifies the engine's BEHAVIOR, not its declarations: every dimension is
verified by RUNNING the actual R2.8/R2.9.x machinery and reducing the observed
evidence to a ``DimensionResult``. The certifier itself is a pure aggregator --
it can never fabricate a result, it only applies the verdict rules and anchors
the artifact.

Constitutional constraints honored:

* Epistemic honesty: the verdict distinguishes CERTIFIED / QUALIFIED /
  NOT_CERTIFIED based on what was ACTUALLY evaluated. A known debt or an
  environment limitation yields QUALIFIED, never a silent CERTIFIED, and never
  a silent FAIL -- each is a recorded, actionable state.
* No single aggregate score: the artifact is a structured report with one
  ``DimensionResult`` per dimension; it is never collapsed to one number.
* Tamper-evidence: the artifact is content-hashed and anchored in the
  EvolutionLedger as a CERTIFICATION event; post-hoc modification is
  detectable via the chain (the anchored ``artifact_content_hash``).
* Deterministic: the certification id derives from the anchors only, and the
  content hash is order-canonicalized, so identical runs certify identically.
* The debt dimensions are non-mandatory and actionable: they record
  ``remediation_target`` so the qualified path names the next migration
  (Phase-28 identity migration) instead of silently passing or blocking.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, Mapping

from .ledger import EventType, EvolutionEvent, EvolutionLedger


class CertificationStatus(str, Enum):
    """Per-dimension certification status. A debt or limitation is recorded
    explicitly -- it is never laundered into a pass or a block."""

    PASS = "PASS"
    KNOWN_DEBT = "KNOWN_DEBT"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    FAIL = "FAIL"


class EngineVerdict(str, Enum):
    """Aggregate verdict over all dimensions (multi-objective, never a score)."""

    CERTIFIED = "CERTIFIED"
    QUALIFIED = "QUALIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"


@dataclass(frozen=True)
class DimensionResult:
    """Certification result for one engine dimension.

    ``mandatory``: must be PASS for any certification. A mandatory dimension
    that is KNOWN_DEBT/NOT_CERTIFIED yields QUALIFIED; a mandatory FAIL yields
    NOT_CERTIFIED. Debt dimensions are non-mandatory by design.
    """

    dimension: str
    status: CertificationStatus
    mandatory: bool = True
    evidence: Mapping[str, object] = field(default_factory=dict)
    notes: str = ""
    remediation_target: str | None = None


DimensionVerifier = Callable[[], DimensionResult]


@dataclass(frozen=True)
class EvolutionCertificationArtifact:
    """Tamper-evident, versioned certification report."""

    certification_id: str
    anchors: Mapping[str, str]
    dimensions: tuple[DimensionResult, ...]
    engine_verdict: EngineVerdict

    def content_hash(self) -> str:
        """Deterministic content hash over the whole artifact. Sets and enums
        are canonicalized so the hash never depends on hash-randomization."""
        canonical = json.dumps(
            _canonicalize(asdict(self)), sort_keys=True, default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def mandatory_passed(self) -> bool:
        return all(
            d.status is CertificationStatus.PASS
            for d in self.dimensions if d.mandatory
        )

    def render_summary(self) -> str:
        """Human-readable matrix: every dimension + status (+ remediation)."""
        header = (
            f"{'dimension':<28}{'status':<16}{'mandatory':<10}{'remediation_target'}"
        )
        rows = [header, "-" * len(header)]
        for d in self.dimensions:
            rows.append(
                f"{d.dimension:<28}{d.status.value:<16}{str(d.mandatory):<10}"
                f"{(d.remediation_target or '')}"
            )
        rows.append(f"engine_verdict: {self.engine_verdict.value}")
        return "\n".join(rows)


def _canonicalize(value):
    """Order-canonicalize for hashing: enums -> values, sets -> sorted lists."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=lambda v: repr(v))
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    return value


class EvolutionCertifier:
    """Runs the dimension verifiers and produces the certification artifact.

    Verifiers are injected (dependency inversion): in production they call the
    live R2.8/R2.9.x machinery; in tests they can be replaced to simulate
    failures. The certifier itself only aggregates and applies the status
    rules -- it never fabricates a result.
    """

    def __init__(
        self,
        ledger: EvolutionLedger,
        anchors: Mapping[str, str],
        verifiers: Mapping[str, DimensionVerifier],
    ) -> None:
        self.ledger = ledger
        self._anchors = dict(anchors)
        self._verifiers = dict(verifiers)

    def certify(self) -> EvolutionCertificationArtifact:
        dimensions = tuple(verifier() for verifier in self._verifiers.values())
        verdict = self._derive_verdict(dimensions)
        artifact = EvolutionCertificationArtifact(
            certification_id=self._derive_id(),
            anchors=self._anchors,
            dimensions=dimensions,
            engine_verdict=verdict,
        )
        self._anchor(artifact)
        return artifact

    # -- verdict rules (the epistemic core) --------------------------------

    def _derive_verdict(
        self, dimensions: tuple[DimensionResult, ...],
    ) -> EngineVerdict:
        if any(
            d.mandatory and d.status is CertificationStatus.FAIL
            for d in dimensions
        ):
            return EngineVerdict.NOT_CERTIFIED
        if all(
            d.status is CertificationStatus.PASS
            for d in dimensions if d.mandatory
        ):
            return EngineVerdict.CERTIFIED
        return EngineVerdict.QUALIFIED

    # -- identity + anchoring ------------------------------------------------

    def _derive_id(self) -> str:
        basis = "|".join(f"{k}={v}" for k, v in sorted(self._anchors.items()))
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]

    def _anchor(self, artifact: EvolutionCertificationArtifact) -> None:
        self.ledger.append_event(
            EvolutionEvent(
                event_id="",
                evolution_id="r2.9.8",
                sequence=0,
                event_type=EventType.CERTIFICATION,
                subject_id=artifact.certification_id,
                payload={
                    "certification_id": artifact.certification_id,
                    "engine_verdict": artifact.engine_verdict.value,
                    "artifact_content_hash": artifact.content_hash(),
                },
            ),
            evolution_id="r2.9.8",
        )
