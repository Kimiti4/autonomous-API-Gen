"""R2.10.32.4 — SecurityTraceabilityEngine: the security realization-chain walker.

32.3 made the threat a first-class ISR carrier (the security-OBLIGATION half
of the pairing); 32.4 is the PROOF half: given a threat ALREADY PRESENT in
the ISR, demonstrate its realization through the generated artifact by
walking the chain

    Threat -> Requirement -> Invariant -> Architectural Control
           -> Implementation Obligation -> Verification -> Evidence

The governing invariant (locked, one verb wider than 32.2's):

    Security Traceability may prove or disprove realization of an
    ISR-declared threat obligation; it may never create, modify, infer,
    or reclassify that obligation.

32.2 forbade CREATING obligations; 32.4 also forbids RECLASSIFYING them,
because the carrier's most easily-corrupted field is severity. 32.3
declared severity *declared, never measured*, and that declaration is
exactly what a traceability engine would be tempted to "refine" into a
calculated risk score the moment it sees realization evidence. That
temptation is structurally refused: the trace carries the DECLARED
severity verbatim (``declared_severity``) and reports realization
evidence alongside it, but the engine never recomputes, adjusts, or
overrides it. Risk analysis — if it ever exists — is a future,
explicitly-defined mechanism, not a side effect of tracing. The two
questions are never conflated:

    A. Was the security obligation realized?   <- this engine answers
    B. Is the declared severity appropriate?   <- this engine must not

The epistemic architecture is REUSED, not rebuilt: TraceabilityState,
TraceabilityLink, ObligationOriginError, the five-state determination,
the first-unresolvable-link freeze, the ledger-addressable evidence refs,
and the reference-integrity discipline all import unchanged from the
R2.10.32.2 engine. This engine supplies only the chain definition and
the six threat link resolvers. The obligation-class pattern holds:
decisions (32.1/32.2) and threats (32.3/32.4) both originate in the ISR,
both trace through the same epistemic states, and both are equally
forbidden to the certifier's imagination — a scanner-observed-but-
undeclared threat surface is not traceable (it raises
``ObligationOriginError``), because it is not an obligation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from constitutional_architecture.isr.model import ThreatSeverity as DeclaredSeverity
from tiannara.application.evolution.identity_index import IdentityIndex
from tiannara.application.quality.decision_traceability import (
    ObligationOriginError,
    TraceabilityLink,
    TraceabilityState,
    _module_realized,
    _verification_event_ref,
    determine_trace_state,
    reference_exists,
)


@dataclass(frozen=True)
class SecurityObligationTrace:
    """The security trace. Extends the 32.2 trace with one field — the
    DECLARED severity — carried through verbatim so the record can never
    be read as having recomputed it. Question A (state) and question B
    (severity) are structurally separate: there is no risk score, no
    computed severity."""

    threat_id: str
    obligation_origin: str                 # invariant: always "ISR"
    declared_severity: DeclaredSeverity    # carried, never reinterpreted
    state: TraceabilityState
    links: tuple[TraceabilityLink, ...]
    evidence_refs: tuple[str, ...]


def resolve_isr_threat(threat_id: str, isr: Any) -> Optional[Any]:
    """Resolve a threat id against ``System.security_threats`` — and only
    there, so the origin invariant is structural. Accepts the bare id form
    (``"THREAT-004"``) and the Phase 32 kind form (``"threat:THREAT-004"``);
    returns the carrier or None. The engine never constructs one.
    """
    candidate = threat_id
    if ":" in threat_id:
        kind, candidate = threat_id.split(":", 1)
        if kind != "threat":
            return None
    for threat in getattr(isr.system, "security_threats", ()):
        if threat.threat_id == candidate:
            return threat
    return None


class SecurityTraceabilityEngine:
    """32.4 — Security Traceability.

    Given a threat ALREADY PRESENT in the ISR, demonstrates its realization
    through the generated artifact by walking:
    Threat → Requirement → Invariant → Architectural Control → Implementation
    Obligation → Verification → Evidence.

    Proves or disproves realization. Never creates, modifies, infers, or
    reclassifies the obligation. Severity is declared, never measured.
    """

    CHAIN = (
        "threat_to_requirement",
        "requirement_to_invariant",
        "invariant_to_architectural_control",
        "architectural_control_to_implementation",
        "implementation_to_verification",
        "verification_to_evidence",
    )

    def __init__(self, identity_index: Any = None) -> None:
        self._identity_index = identity_index or IdentityIndex

    def trace(
        self,
        threat_id: str,
        isr: Any,
        artifact: Mapping[str, Any],
        *,
        ledger: Any = None,
    ) -> SecurityObligationTrace:
        threat = resolve_isr_threat(threat_id, isr)
        if threat is None:
            raise ObligationOriginError(
                f"threat '{threat_id}' does not originate in the ISR; the "
                "security traceability engine does not create threats"
            )
        from_ref = threat.threat_id
        broken = False
        links: list[TraceabilityLink] = []
        for link_kind in self.CHAIN:
            if broken:
                # the chain already broke; every further link is ABSENT,
                # never re-attempted (the first-unresolvable-link freeze).
                links.append(TraceabilityLink(link_kind, from_ref, None, False))
                continue
            link = self._resolve_link(
                link_kind, threat, isr, artifact, ledger
            )
            links.append(link)
            if link.resolved:
                from_ref = link.to_ref or from_ref
            else:
                broken = True
        state = determine_trace_state(
            tuple(links), isr, self._identity_index
        )
        return SecurityObligationTrace(
            threat_id=threat_id,
            obligation_origin="ISR",
            declared_severity=threat.severity,  # carried verbatim
            state=state,
            links=tuple(links),
            evidence_refs=tuple(
                link.evidence_ref for link in links if link.evidence_ref
            ),
        )

    # -- link resolvers (the six 32.3 edges, read-only) ------------------------

    def _resolve_link(
        self,
        link_kind: str,
        threat: Any,
        isr: Any,
        artifact: Mapping[str, Any],
        ledger: Any,
    ) -> TraceabilityLink:
        if link_kind == "threat_to_requirement":
            return self._threat_to_requirement(threat, isr)
        if link_kind == "requirement_to_invariant":
            return self._requirement_to_invariant(threat, isr)
        if link_kind == "invariant_to_architectural_control":
            return self._invariant_to_architectural_control(threat, isr)
        if link_kind == "architectural_control_to_implementation":
            return self._architectural_control_to_implementation(
                threat, isr, artifact
            )
        if link_kind == "implementation_to_verification":
            return self._implementation_to_verification(threat, isr)
        if link_kind == "verification_to_evidence":
            return self._verification_to_evidence(
                threat, isr, artifact, ledger
            )
        raise AssertionError(f"unknown link kind '{link_kind}'")

    def _threat_to_requirement(self, threat: Any, isr: Any) -> TraceabilityLink:
        """The threat -> the requirement it endangers, via the 32.3
        requirement_refs edge (F)."""
        to_ref = threat.requirement_refs[0] if threat.requirement_refs else None
        return TraceabilityLink(
            "threat_to_requirement", threat.threat_id, to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _requirement_to_invariant(self, threat: Any, isr: Any) -> TraceabilityLink:
        """The requirement -> the invariant that must hold. The invariant
        lives IN the threat carrier (invariant_statement, guaranteed by
        32.3 construction) — the link resolves to the threat itself, the
        invariant-bearing carrier, exactly as 32.2 resolves a decision to
        the E/D/J carrier that declares its invariant."""
        to_ref = threat.threat_id
        return TraceabilityLink(
            "requirement_to_invariant",
            threat.requirement_refs[0] if threat.requirement_refs else to_ref,
            to_ref,
            self._reference_exists(to_ref, isr),
        )

    def _invariant_to_architectural_control(
        self, threat: Any, isr: Any
    ) -> TraceabilityLink:
        """The invariant -> the architectural control that addresses it,
        via the 32.3 architectural_control_refs edge (E boundaries). The
        first control is walked AS WRITTEN — a control that does not
        resolve in the identity universe is INVALID_REFERENCE, never
        silently filtered."""
        to_ref = (
            threat.architectural_control_refs[0]
            if threat.architectural_control_refs
            else None
        )
        return TraceabilityLink(
            "invariant_to_architectural_control", threat.threat_id, to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _architectural_control_to_implementation(
        self, threat: Any, isr: Any, artifact: Mapping[str, Any]
    ) -> TraceabilityLink:
        """The control -> the implementation obligation that realizes it,
        via the 32.3 implementation_obligation_refs edge (the 32.1
        decision carrier). The link is resolved only when the obligation
        exists AND its scoped module is actually carried by the artifact —
        an unrealized implementation obligation is UNSATISFIED, never
        silently passed."""
        to_ref = (
            threat.implementation_obligation_refs[0]
            if threat.implementation_obligation_refs
            else None
        )
        resolved = False
        if to_ref is not None and self._reference_exists(to_ref, isr):
            decision = next(
                (
                    d
                    for d in isr.system.architectural_decisions
                    if d.decision_id == to_ref
                ),
                None,
            )
            if decision is not None and decision.architectural_scope:
                resolved = _module_realized(
                    decision.architectural_scope[0], artifact
                )
        return TraceabilityLink(
            "architectural_control_to_implementation",
            threat.architectural_control_refs[0]
            if threat.architectural_control_refs
            else threat.threat_id,
            to_ref,
            resolved,
        )

    def _implementation_to_verification(
        self, threat: Any, isr: Any
    ) -> TraceabilityLink:
        """The implementation -> the anchor that declares its verification,
        via the 32.3 verification_refs edge (H anchors)."""
        to_ref = threat.verification_refs[0] if threat.verification_refs else None
        return TraceabilityLink(
            "implementation_to_verification",
            threat.implementation_obligation_refs[0]
            if threat.implementation_obligation_refs
            else threat.threat_id,
            to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _verification_to_evidence(
        self, threat: Any, isr: Any, artifact: Mapping[str, Any], ledger: Any
    ) -> TraceabilityLink:
        """The anchor -> the chain-anchored verification evidence. The
        evidence ref is the deterministic ledger event id; it is set ONLY
        when the event actually resolves on the supplied ledger — a
        realized-but-unrecorded obligation is INSUFFICIENT_EVIDENCE, named
        and never passed."""
        to_ref = threat.verification_refs[0] if threat.verification_refs else None
        resolved = to_ref is not None and self._reference_exists(to_ref, isr)
        evidence_ref = _verification_event_ref(artifact)
        if evidence_ref is not None and ledger is not None:
            if ledger.event_by_ref(evidence_ref) is None:
                evidence_ref = None
        return TraceabilityLink(
            "verification_to_evidence",
            to_ref or threat.threat_id,
            to_ref,
            resolved,
            evidence_ref,
        )

    # -- helpers ------------------------------------------------------------------

    def _reference_exists(self, ref: str, isr: Any) -> bool:
        """R2.10's reference-integrity discipline: a reference resolves iff
        it is a member of the identity index's resolvable universe."""
        return reference_exists(ref, isr, self._identity_index)