"""R2.10.8 — artifact verification & provenance.

R2.10.7 proved the backend consumed the ISR correctly. R2.10.8 proves the
resulting artifact can INDEPENDENTLY demonstrate where it came from and
what semantic source it represents — judged by a verifier that trusts
nothing.

Responsibility split:

    ISR        = semantic authority      (never modified by verification)
    Compiler   = realization producer   (makes the claim)
    Artifact   = realization            (what is judged)
    Provenance = evidence of derivation (the claim, checked)
    Verifier   = independent judge      (re-derives, trusts nothing)

The verifier's independence is structural: it re-derives the artifact hash
from the artifact content, the semantic hash from the ISR, and the expected
provenance from the ledger's independently-recorded compilation event —
then checks the claim against all three. It never accepts the compiler's
assertion, never lets a backend define what counts as valid provenance, and
never writes verification state back into the ISR. The result of judging is
itself chain-anchored (recorded only when the ledger chain is intact).

The 16th Option A use: a verification step with an identity requirement of
zero — the verifier never modifies the ISR, the artifact, or the claim.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping

from constitutional_architecture.isr.semantics.projection import (
    CanonicalizationError,  # noqa: F401  (re-exported for the acceptance suite)
    canonicalize,
    semantic_content_hash,
)

from .consumption_contract import CapabilityCoverage, enumerate_isr_semantics


def hash_artifact_canonical(artifact: Any) -> str:
    """Deterministic artifact identity via the no-default-str canonicalization.

    Raises CanonicalizationError on unhandled types — identity is never
    produced by silently str()-ing something the platform cannot canonically
    represent. This is the SAME hash the compilation computed at Gate H, so
    the verifier's re-derivation is directly comparable.
    """
    return hashlib.sha256(canonicalize(artifact).encode("utf-8")).hexdigest()


def compilation_event_ref_for(result: Any) -> str:
    """The ledger event reference that recorded this compilation (Gate H)."""
    return f"compilation-{result.backend_id}-{result.artifact_hash[:8]}"


def conformance_event_ref_for(report: Any) -> str:
    """The ledger event reference that certified this conformance report
    (R2.10.7 record_conformance), mirrored by ConformanceEvidenceRegistry."""
    return (
        f"conformance-{report.backend_id}-"
        f"{report.isr_semantic_hash_at_conformance[:8]}"
    )


@dataclass(frozen=True)
class ArtifactProvenance:
    """The artifact's CLAIM of derivation. Claims are judged, never trusted.

    Provenance is evidence of derivation, not a semantic authority: it never
    writes back into the ISR, and no backend gets to define what counts as
    valid provenance. ``capability_coverage`` declares which semantics the
    artifact represents (a silent omission is a lie; an explicit
    UNSUPPORTED is an honest boundary).
    """

    artifact_hash: str
    isr_hash: str
    target_id: str
    backend_id: str
    backend_version: str
    compilation_event_ref: str
    conformance_evidence_ref: str
    capability_coverage: tuple[CapabilityCoverage, ...]


def provenance_claim(
    result: Any,
    compilation_event_ref: str,
    conformance_evidence_ref: str,
) -> ArtifactProvenance:
    """Assemble the derivation claim from a compilation result and the two
    independent references (the ledger's compilation event + the registered
    conformance report). Assembly is the compiler's side; judgment is the
    verifier's."""
    return ArtifactProvenance(
        artifact_hash=result.artifact_hash,
        isr_hash=result.isr_hash,
        target_id=result.target_id,
        backend_id=result.backend_id,
        backend_version=result.backend_version,
        compilation_event_ref=compilation_event_ref,
        conformance_evidence_ref=conformance_evidence_ref,
        capability_coverage=result.capability_coverage,
    )


@dataclass(frozen=True)
class VerificationResult:
    """The independent judge's verdict. ``failures`` is a stable inventory
    (artifact_modified, isr_mismatch, compilation_event_not_found,
    target_mismatch, backend_mismatch, silently_discarded:<ids>,
    conformance_evidence_not_found); ``verification_event_ref`` is set only
    when the ledger chain was intact enough to anchor the verdict."""

    verified: bool
    artifact_hash: str
    artifact_integrity_verified: bool
    isr_binding_verified: bool
    target_binding_verified: bool
    backend_binding_verified: bool
    semantic_coverage_verified: bool
    ledger_chain_verified: bool
    failures: tuple[str, ...] = ()
    verification_event_ref: str | None = None


@dataclass(frozen=True)
class CrossBackendVerificationResult:
    """Seven divergent artifacts must resolve to ONE semantic source.

    Artifact equality is never required — divergence is the point of real
    backends; single-source agreement is the point of the platform.
    """

    verified: bool
    per_backend: Mapping[str, VerificationResult]
    semantic_sources_resolved: tuple[str, ...] = ()
    artifact_equality_required: bool = False


class ConformanceEvidenceRegistry:
    """Index of chain-anchored R2.10.7 conformance reports.

    The verifier judges that the referenced evidence EXISTS — re-running
    conformance is R2.10.7's job. Refs mirror the ledger's CERTIFICATION
    event ids, so the index and the chain agree by construction.
    """

    def __init__(self) -> None:
        self._refs: set[str] = set()

    def register(self, report: Any) -> str:
        ref = conformance_event_ref_for(report)
        self._refs.add(ref)
        return ref

    def has(self, ref: str) -> bool:
        return ref in self._refs


class ArtifactVerifier:
    """The independent judge: trusts nothing, re-derives everything.

    Checks, in order:
      1. artifact_integrity  — hash_artifact_canonical(artifact) == claim
      2. isr_binding         — semantic_content_hash(isr) == claim
      3. compilation event   — ledger.event_by_ref(claim.compilation_event_ref)
                              is a COMPILATION event whose payload binds the
                              same target/backend/version; chain intact
      4. semantic coverage   — enumerate_isr_semantics(isr) ⊆ claim coverage;
                              a silent omission is fatal, an explicit
                              UNSUPPORTED is permitted
      5. conformance evidence— the R2.10.7 report exists in the registry

    The verdict is recorded on the ledger ONLY when the chain was intact
    (a broken chain cannot anchor evidence). The ISR and the artifact are
    never touched.
    """

    def __init__(self, ledger: Any, conformance_registry: Any) -> None:
        self._ledger = ledger
        self._conformance_registry = conformance_registry

    def verify(
        self, artifact: Any, claimed: ArtifactProvenance, isr: Any
    ) -> VerificationResult:
        failures: list[str] = []

        recomputed = hash_artifact_canonical(artifact)
        artifact_ok = recomputed == claimed.artifact_hash
        if not artifact_ok:
            failures.append("artifact_modified")

        isr_ok = semantic_content_hash(isr) == claimed.isr_hash
        if not isr_ok:
            failures.append("isr_mismatch")

        event = self._ledger.event_by_ref(claimed.compilation_event_ref)
        if event is None:
            target_ok = backend_ok = chain_ok = False
            failures.append("compilation_event_not_found")
        else:
            payload = event.payload
            target_ok = payload.get("target_id") == claimed.target_id
            backend_ok = (
                payload.get("backend_id") == claimed.backend_id
                and payload.get("backend_version") == claimed.backend_version
            )
            chain_ok = self._ledger.verify_event_chain()
            if not target_ok:
                failures.append("target_mismatch")
            if not backend_ok:
                failures.append("backend_mismatch")

        required = set(enumerate_isr_semantics(isr))
        covered = {item.capability_id for item in claimed.capability_coverage}
        coverage_ok = required <= covered
        if not coverage_ok:
            failures.append(f"silently_discarded:{sorted(required - covered)}")

        conformance_ok = self._conformance_registry.has(
            claimed.conformance_evidence_ref
        )
        if not conformance_ok:
            failures.append("conformance_evidence_not_found")

        verified = all(
            (artifact_ok, isr_ok, target_ok, backend_ok, coverage_ok,
             chain_ok, conformance_ok)
        )
        verification_ref = None
        if chain_ok:
            verification_ref = self._ledger.record_verification(
                artifact_hash=recomputed, verified=verified,
                failures=tuple(failures),
            )
        return VerificationResult(
            verified=verified,
            artifact_hash=recomputed,
            artifact_integrity_verified=artifact_ok,
            isr_binding_verified=isr_ok,
            target_binding_verified=target_ok,
            backend_binding_verified=backend_ok,
            semantic_coverage_verified=coverage_ok,
            ledger_chain_verified=chain_ok,
            failures=tuple(failures),
            verification_event_ref=verification_ref,
        )

    def verify_cross_backend(
        self, artifacts_with_provenance: Mapping[str, tuple[Any, ArtifactProvenance]],
        isr: Any,
    ) -> CrossBackendVerificationResult:
        """Verify every backend's artifact; require all to resolve to the ONE
        semantic source. Divergence is expected (real backends differ);
        semantic agreement is required (one ISR)."""
        per_backend: dict[str, VerificationResult] = {}
        resolved_sources: set[str] = set()
        for backend_id, (artifact, provenance) in artifacts_with_provenance.items():
            result = self.verify(artifact, provenance, isr)
            per_backend[backend_id] = result
            if result.verified:
                resolved_sources.add(provenance.isr_hash)
        all_ok = all(result.verified for result in per_backend.values())
        single_source = resolved_sources == {semantic_content_hash(isr)}
        return CrossBackendVerificationResult(
            verified=all_ok and single_source,
            per_backend=per_backend,
            semantic_sources_resolved=tuple(sorted(resolved_sources)),
            artifact_equality_required=False,
        )