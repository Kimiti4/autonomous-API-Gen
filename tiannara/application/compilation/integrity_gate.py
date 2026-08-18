"""R2.10.6 — CompilationIntegrityGate: the eight gates of a certified compile.

The gate certifies that a compilation consumed the ISR without participating
in it. Every gate returns a GateResult (gate_id, held, evidence) so a failed
compilation names EXACTLY what failed:

  A  read-only               — the backend compile left the ISR byte-identical
                               (semantic hash stable before and after).
  B  determinism              — two compiles of the same ISR under the same
                               target produce the same artifact hash.
  C  provenance               — the result binds isr_hash / target / backend /
                               version, and artifact_hash is the artifact's
                               own content hash.
  D  semantic coverage        — every semantic the ISR expresses is DECLARED
                               in the coverage (never silently discarded).
  E  backend independence     — compiling under a DIFFERENT target still
                               leaves the ISR unchanged.
  F  round-trip               — the artifact re-declares its semantic source
                               (isr_hash) matching the compiled ISR.
  G  constitutional preservation — the backend's projection carries the
                               constitutional surface content-identically.
  H  evidence binding         — the compilation is chain-anchored in the
                               evidence ledger (no ledger = not certifiable).

The gate holds no evaluation machinery of its own and imports no backend:
backends arrive as the ``CompilerBackend`` protocol seam.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from constitutional_architecture.isr.semantics.projection import canonicalize

from .consumption_contract import (
    CompilationResult,
    CompilationTarget,
    CompilerBackend,
    constitutional_surface_intact,
    enumerate_isr_semantics,
    reconstruct_semantic_source,
)


@dataclass(frozen=True)
class GateResult:
    """One gate's verdict with its evidence."""

    gate_id: str
    held: bool
    evidence: str


GATE_READ_ONLY = "A_read_only"
GATE_DETERMINISM = "B_determinism"
GATE_PROVENANCE = "C_provenance"
GATE_SEMANTIC_COVERAGE = "D_semantic_coverage"
GATE_BACKEND_INDEPENDENCE = "E_backend_independence"
GATE_ROUND_TRIP = "F_round_trip"
GATE_CONSTITUTIONAL_PRESERVATION = "G_constitutional_preservation"
GATE_EVIDENCE_BINDING = "H_evidence_binding"


@dataclass(frozen=True)
class CompilationIntegrityVerdict:
    """The certified compile: held only if every gate held. ``result`` is the
    primary compilation (None when any gate failed); ``ledger_event_range``
    mirrors the R2.10.4 verdict shape (event-hash range recorded)."""

    held: bool
    gates: tuple[GateResult, ...]
    result: Optional[CompilationResult]
    ledger_event_range: Optional[tuple[str, str]] = None


class CompilationIntegrityGate:
    """Certifies one ISR -> backend compilation under the eight gates."""

    def __init__(self, ledger: Any = None) -> None:
        self._ledger = ledger

    def verify(
        self,
        isr: Any,
        target: CompilationTarget,
        backend: CompilerBackend,
        *,
        ledger: Any = None,
    ) -> CompilationIntegrityVerdict:
        """Run all eight gates. The gate compiles the ISR three times (the
        primary compile, the determinism twin, and the different-target
        independence probe) — none of which may touch the ISR."""
        before = canonicalize(isr.system)
        primary = backend.compile(isr, target)
        after = canonicalize(isr.system)
        twin = backend.compile(isr, target)
        alt_target = CompilationTarget(
            target_id=f"{target.target_id}-independent",
            language=target.language,
            runtime=target.runtime,
            framework=target.framework,
            capabilities=frozenset(target.capabilities),
            version=target.version,
        )
        before_alt = canonicalize(isr.system)
        alt = backend.compile(isr, alt_target)
        after_alt = canonicalize(isr.system)

        gates = (
            self._gate_a(before, after, primary),
            self._gate_b(primary, twin),
            self._gate_c(primary),
            self._gate_d(isr, primary),
            self._gate_e(before_alt, after_alt, alt),
            self._gate_f(isr, primary),
            self._gate_g(isr, backend),
        )
        h_result, event_range = self._gate_h(primary, ledger)
        gates = gates + (h_result,)
        held = all(gate.held for gate in gates)
        return CompilationIntegrityVerdict(
            held,
            gates,
            primary if held else None,
            event_range,
        )

    # -- the eight gates -------------------------------------------------------

    def _gate_a(
        self, before: str, after: str, result: CompilationResult
    ) -> GateResult:
        held = before == after
        return GateResult(
            GATE_READ_ONLY,
            held,
            (
                "backend compile left the ISR byte-identical (semantic "
                f"hash stable, isr_hash {result.isr_hash[:12]}…)"
                if held
                else "backend MUTATED the ISR during compilation: semantic "
                     "hash changed"
            ),
        )

    def _gate_b(
        self, primary: CompilationResult, twin: CompilationResult
    ) -> GateResult:
        held = (
            primary.artifact_hash == twin.artifact_hash
            and primary.isr_hash == twin.isr_hash
        )
        return GateResult(
            GATE_DETERMINISM,
            held,
            (
                "two compiles produced identical artifact hash "
                f"{primary.artifact_hash[:12]}… and isr hash "
                f"{primary.isr_hash[:12]}…"
                if held
                else f"non-deterministic compile: artifact hashes "
                     f"{primary.artifact_hash[:12]}… vs {twin.artifact_hash[:12]}…"
            ),
        )

    def _gate_c(self, result: CompilationResult) -> GateResult:
        provenance = result.provenance
        bound = (
            provenance.isr_hash == result.isr_hash
            and provenance.target_id == result.target_id
            and provenance.backend_id == result.backend_id
            and provenance.backend_version == result.backend_version
        )
        expected_hash = self._artifact_hash(result.artifact)
        artifact_self_consistent = expected_hash == result.artifact_hash
        held = bound and artifact_self_consistent
        return GateResult(
            GATE_PROVENANCE,
            held,
            (
                f"provenance binds isr_hash {result.isr_hash[:12]}…, target "
                f"'{result.target_id}', backend '{result.backend_id}' v"
                f"{result.backend_version}; artifact_hash is the artifact's "
                "own content hash"
                if held
                else (
                    "provenance unbound: isr_hash/target/backend/version "
                    "mismatch or artifact_hash does not match the artifact "
                    "content"
                )
            ),
        )

    def _gate_d(
        self, isr: Any, result: CompilationResult
    ) -> GateResult:
        required = enumerate_isr_semantics(isr)
        declared = {c.capability_id for c in result.capability_coverage}
        missing = sorted(required - declared)
        held = not missing
        return GateResult(
            GATE_SEMANTIC_COVERAGE,
            held,
            (
                f"all {len(required)} expressed semantics declared in the "
                "coverage (SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED — "
                "explicit, never silent)"
                if held
                else f"silently discarded: {missing}"
            ),
        )

    def _gate_e(
        self, before: str, after: str, alt: CompilationResult
    ) -> GateResult:
        held = before == after
        return GateResult(
            GATE_BACKEND_INDEPENDENCE,
            held,
            (
                "compilation under a different target left the ISR unchanged "
                f"(semantic hash stable, isr_hash {alt.isr_hash[:12]}…)"
                if held
                else "compiling under a different target MUTATED the ISR"
            ),
        )

    def _gate_f(self, isr: Any, result: CompilationResult) -> GateResult:
        reconstructed = reconstruct_semantic_source(result)
        expected = result.isr_hash
        held = reconstructed == expected
        return GateResult(
            GATE_ROUND_TRIP,
            held,
            (
                "artifact re-declares its semantic source "
                f"{expected[:12]}… — the realization round-trips to its source"
                if held
                else f"artifact semantic source {reconstructed[:12]}… != "
                     f"compiled isr_hash {expected[:12]}…"
            ),
        )

    def _gate_g(self, isr: Any, backend: CompilerBackend) -> GateResult:
        model = backend.semantic_projection(isr)
        mismatches = constitutional_surface_intact(isr, model)
        held = not mismatches
        return GateResult(
            GATE_CONSTITUTIONAL_PRESERVATION,
            held,
            (
                "backend projection carries the constitutional surface "
                "content-identically (requirements, acceptance criteria, "
                "reliability, deployment, boundaries, testing anchors, "
                "protected regions)"
                if held
                else f"constitutional surface weakened: {mismatches}"
            ),
        )

    def _gate_h(
        self, result: CompilationResult, ledger: Any
    ) -> tuple[GateResult, Optional[tuple[str, str]]]:
        active = ledger if ledger is not None else self._ledger
        if active is None:
            return (
                GateResult(
                    GATE_EVIDENCE_BINDING,
                    False,
                    "no evidence ledger bound — a compilation without "
                    "chain-anchored evidence cannot be certified",
                ),
                None,
            )
        event_id = active.record_compilation(result)
        chain_ok = active.verify_event_chain()
        event_range = (event_id, active.latest_event_hash)
        return (
            GateResult(
                GATE_EVIDENCE_BINDING,
                chain_ok,
                (
                    f"compilation chain-anchored as event '{event_id}' "
                    f"(isr_hash {result.isr_hash[:12]}…, artifact "
                    f"{result.artifact_hash[:12]}…); event chain intact"
                    if chain_ok
                    else "compilation recorded but the event chain FAILED "
                         "to verify — tamper or desync",
                ),
            ),
            event_range if chain_ok else None,
        )

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _artifact_hash(artifact: dict) -> str:
        import hashlib

        return hashlib.sha256(canonicalize(artifact).encode("utf-8")).hexdigest()