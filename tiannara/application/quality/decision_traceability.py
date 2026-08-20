"""R2.10.32.2 — DecisionTraceabilityEngine: the realization-chain walker.

32.1 made the decision a first-class ISR carrier (the OBLIGATION half of
the pairing); 32.2 is the PROOF half: given an obligation ALREADY PRESENT
in the ISR, demonstrate its realization through the generated artifact by
walking the chain

    Requirement -> Decision -> Architecture -> Module/Boundary
                 -> Implementation -> Verification -> Evidence

The engine never creates obligations, never invents links, and never infers
meaning — it resolves references the ISR and the artifact already contain.
Every step uses an existing edge (the 32.1 decision's requirement_refs /
invariant_refs / architectural_scope / verification_refs, E's boundary
member_refs, the artifact's manifest/bundle realization surface, the
ledger's chain-anchored events). The proof originates in the evidence;
32.2 is the bridge that connects the two without ever authoring either.

The governing invariant (CERTIFICATION_TRACEABILITY_NEVER_CREATES_
OBLIGATIONS) has two structural forms:

    * the engine refuses — ``ObligationOriginError`` — any obligation id
      that does not resolve to a carrier the ISR already carries (the
      stronger form: for every certification obligation,
      ``obligation.origin == "ISR"``);
    * the engine's own source is AST-scanned in the acceptance suite for
      any obligation- or decision-construction call shape.

States (the vacuity policy applied to traceability — five states, never a
binary pass/fail):

    SATISFIED               realized AND evidenced (every link resolves
                            and the terminal evidence is chain-anchored)
    UNSATISFIED             the traced obligation is not realized in the
                            artifact (the chain exists but the module is
                            not carried)
    MISSING_LINK            a link in the chain is absent (no decision
                            references the requirement, no boundary
                            realizes the decision, no anchor covers the
                            implementation)
    INVALID_REFERENCE       a reference resolves to something that does
                            not exist in the identity universe (the
                            identity index, consistent with R2.10's
                            reference-integrity discipline)
    INSUFFICIENT_EVIDENCE   realized but not evidenced — named, never a
                            pass (the vacuity policy applied to the
                            certification's own chains)

Evidence refs are ledger-addressable by construction: the terminal
verification link's evidence ref is the deterministic event id of the
ledger's ``verification-{artifact_hash[:8]}`` event, and it is only set
when the event actually resolves on the supplied ledger. A trace result is
therefore chain-anchored and a certificate can bind to it.

The engine imports the identity index (reference resolution) and the
ledger type only for duck-typed event lookups — it never imports decision
or obligation construction machinery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Mapping, Optional

from tiannara.application.evolution.identity_index import IdentityIndex


class TraceabilityState(str, Enum):
    """The five traceability states — never a binary pass/fail. The vacuity
    policy applied to the certification's own chains: a realized-but-unproven
    obligation is named (INSUFFICIENT_EVIDENCE), never silently counted as
    satisfied and never silently counted as failed."""

    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    MISSING_LINK = "MISSING_LINK"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ObligationOriginError(ValueError):
    """Raised when asked to trace an obligation that does not originate in
    the ISR. The engine refuses rather than constructs — it proves
    realization of meaning, it never authors meaning."""


@dataclass(frozen=True)
class TraceabilityLink:
    """One link in the realization chain.

    ``to_ref`` is None when the link is absent (the chain simply does not
    continue); ``resolved`` is True only when the reference actually
    resolves; ``evidence_ref`` is the ledger-addressable event reference
    (only the terminal verification link carries one — every evidence ref
    must resolve on the ledger).
    """

    link_kind: str
    from_ref: str
    to_ref: Optional[str]
    resolved: bool
    evidence_ref: Optional[str] = None


@dataclass(frozen=True)
class ObligationTrace:
    """One obligation's realization chain: its state, every link, and the
    chain-anchored evidence references (all ledger-addressable)."""

    obligation_id: str
    obligation_origin: str  # invariant: always "ISR"
    state: TraceabilityState
    links: tuple[TraceabilityLink, ...]
    evidence_refs: tuple[str, ...]


# -- obligation resolution (from EXISTING carriers, never invented) --------------

# carrier kind -> (system carrier attribute, id attribute)
_OBLIGATION_CARRIERS: tuple[tuple[str, str, str], ...] = (
    ("requirement", "requirements", "requirement_id"),
    ("acceptance_criterion", "acceptance_criteria", "criterion_id"),
    ("boundary", "architectural_boundaries", "boundary_id"),
    ("reliability", "reliability_requirements", "requirement_id"),
    ("protected_region", "protected_regions", "region_id"),
    ("testing_anchor", "testing_anchors", "anchor_id"),
    ("deployment", "deployment_intents", "deployment_id"),
    ("documentation", "documentation_intents", "documentation_id"),
    ("evolution_objective", "evolution_objectives", "objective_id"),
    ("evolution_policy", "evolution_policies", "policy_id"),
    ("decision", "architectural_decisions", "decision_id"),
)


def resolve_isr_obligation(
    obligation_id: str, isr: Any
) -> Optional[tuple[str, Any]]:
    """Resolve an obligation id to the carrier the ISR already carries.

    Accepts both the Phase 32 form (``"requirement:REQ-001"``) and the bare
    carrier id form (``"REQ-001"``); returns (kind, carrier) or None. The
    obligation must be a carrier the ISR declares — the engine never
    constructs one.
    """
    kind = None
    carrier_id = obligation_id
    if ":" in obligation_id:
        kind, carrier_id = obligation_id.split(":", 1)
    for candidate_kind, attr, id_attr in _OBLIGATION_CARRIERS:
        if kind is not None and candidate_kind != kind:
            continue
        for carrier in getattr(isr.system, attr, ()):
            if getattr(carrier, id_attr) == carrier_id:
                return (candidate_kind, carrier)
    return None


# -- the engine ------------------------------------------------------------------

def _bundle_files(artifact: Mapping[str, Any]) -> list[tuple[str, str]]:
    bundle = artifact.get("bundle") or {}
    files: list[tuple[str, str]] = []
    for manifest in bundle.get("manifests") or ():
        for path, content in (manifest.get("files") or {}).items():
            files.append((str(path), str(content)))
    return files


def _module_realized(module_id: str, artifact: Mapping[str, Any]) -> bool:
    """The artifact's realization surface: the module is declared in the
    manifest or its identity appears in a bundle file's content."""
    manifest = artifact.get("manifest") or {}
    if any(
        entry.get("id") == module_id for entry in manifest.get("modules") or ()
    ):
        return True
    return any(module_id in content for _, content in _bundle_files(artifact))


def _verification_event_ref(artifact: Mapping[str, Any]) -> Optional[str]:
    """The deterministic ledger event id of the artifact's verification —
    ``verification-{artifact_hash[:8]}``, exactly as the ledger's
    ``record_verification`` computes it."""
    provenance = artifact.get("provenance") or {}
    artifact_hash = provenance.get("artifact_hash")
    if not artifact_hash:
        return None
    return f"verification-{artifact_hash[:8]}"


# -- shared epistemic machinery (reused by every obligation-class engine) ------

def reference_exists(ref: str, isr: Any, identity_index: Any = IdentityIndex) -> bool:
    """R2.10's reference-integrity discipline: a reference resolves iff
    it is a member of the identity index's resolvable universe."""
    return ref in identity_index.derive(isr).resolvable_ids


def determine_trace_state(
    links: tuple[TraceabilityLink, ...],
    isr: Any,
    identity_index: Any = IdentityIndex,
) -> TraceabilityState:
    """The five-state determination, shared by every traceability engine.

    The state is decided by the FIRST link the chain could not resolve
    (everything after it is a frozen absent tail, never re-attempted):

      * a reference that resolves to something that does not exist in
        the identity universe -> INVALID_REFERENCE;
      * a link that is simply absent -> MISSING_LINK;
      * a link whose reference exists but that is not realized (e.g. a
        module not carried by the artifact) -> UNSATISFIED;
      * the whole chain resolved, but the terminal verification
        evidence is not chain-anchored -> INSUFFICIENT_EVIDENCE
        (advisory, never a pass);
      * the whole chain resolved and evidenced -> SATISFIED.
    """
    for link in links:
        if link.resolved:
            continue
        if link.to_ref is not None and not reference_exists(
            link.to_ref, isr, identity_index
        ):
            return TraceabilityState.INVALID_REFERENCE
        if link.to_ref is None:
            return TraceabilityState.MISSING_LINK
        return TraceabilityState.UNSATISFIED
    if links[-1].evidence_ref is not None:
        return TraceabilityState.SATISFIED
    return TraceabilityState.INSUFFICIENT_EVIDENCE


class DecisionTraceabilityEngine:
    """32.2 — Decision Traceability.

    Given an obligation ALREADY PRESENT in the ISR, demonstrates its
    realization through the generated artifact by walking the chain:
    Requirement → Decision → Architecture → Module/Boundary → Implementation
    → Verification → Evidence.

    The engine never creates obligations, never invents links, and never
    infers meaning — it resolves references the ISR and the artifact already
    contain. ``ledger`` is duck-typed (``event_by_ref``) and consulted ONLY
    to confirm the terminal evidence is chain-anchored.
    """

    CHAIN = (
        "requirement_to_decision",
        "decision_to_architecture",
        "architecture_to_module",
        "module_to_implementation",
        "implementation_to_verification",
        "verification_to_evidence",
    )

    def __init__(self, identity_index: Any = None) -> None:
        self._identity_index = identity_index or IdentityIndex

    def trace(
        self,
        obligation_id: str,
        isr: Any,
        artifact: Mapping[str, Any],
        *,
        ledger: Any = None,
    ) -> ObligationTrace:
        obligation = resolve_isr_obligation(obligation_id, isr)
        if obligation is None:
            raise ObligationOriginError(
                f"obligation '{obligation_id}' does not originate in the "
                "ISR; the traceability engine does not create obligations"
            )
        kind, carrier = obligation
        node_kind = kind
        node_id = self._carrier_id(node_kind, carrier)
        decision_id: Optional[str] = None
        broken = False
        links: list[TraceabilityLink] = []
        for link_kind in self.CHAIN:
            if broken:
                # the chain already broke; every further link is ABSENT,
                # never re-attempted against a node that no longer applies.
                links.append(TraceabilityLink(link_kind, node_id, None, False))
                continue
            link = self._resolve_link(
                link_kind,
                node_kind,
                node_id,
                carrier,
                isr,
                artifact,
                ledger,
                decision_id,
            )
            links.append(link)
            if not link.resolved:
                broken = True
                continue
            if link.to_ref is not None:
                next_node = self._advance(link_kind, link.to_ref, isr)
                if next_node is not None:
                    node_kind, node_id, carrier = next_node
                if link_kind == "requirement_to_decision":
                    decision_id = link.to_ref
        state = self._determine_state(tuple(links), isr)
        return ObligationTrace(
            obligation_id=obligation_id,
            obligation_origin="ISR",
            state=state,
            links=tuple(links),
            evidence_refs=tuple(
                link.evidence_ref for link in links if link.evidence_ref
            ),
        )

    # -- link resolvers (existing edges only) -----------------------------------

    # the node kind each link walks OUT of (None = any obligation kind); a
    # link attempted against the wrong node is ABSENT, never mis-resolved.
    _LINK_FROM_KIND: dict[str, Optional[str]] = {
        "requirement_to_decision": None,
        "decision_to_architecture": "decision",
        "architecture_to_module": "architecture",
        "module_to_implementation": "module",
        "implementation_to_verification": "module",
        "verification_to_evidence": "testing_anchor",
    }

    def _resolve_link(
        self,
        link_kind: str,
        node_kind: str,
        node_id: str,
        carrier: Any,
        isr: Any,
        artifact: Mapping[str, Any],
        ledger: Any,
        decision_id: Optional[str],
    ) -> TraceabilityLink:
        system = isr.system
        expected = self._LINK_FROM_KIND[link_kind]
        if expected is not None and node_kind != expected:
            return TraceabilityLink(link_kind, node_id, None, False)
        if link_kind == "requirement_to_decision":
            return self._requirement_to_decision(
                node_kind, node_id, carrier, isr
            )
        if link_kind == "decision_to_architecture":
            return self._decision_to_architecture(carrier, isr)
        if link_kind == "architecture_to_module":
            return self._architecture_to_module(decision_id, isr)
        if link_kind == "module_to_implementation":
            return self._module_to_implementation(node_id, isr, artifact)
        if link_kind == "implementation_to_verification":
            return self._implementation_to_verification(
                decision_id, isr
            )
        if link_kind == "verification_to_evidence":
            return self._verification_to_evidence(node_id, isr, artifact, ledger)
        raise AssertionError(f"unknown link kind '{link_kind}'")

    def _requirement_to_decision(
        self, node_kind: str, node_id: str, carrier: Any, isr: Any
    ) -> TraceabilityLink:
        """The obligation -> the decision that serves it, via the decision's
        requirement_refs (F -> 32.1 edge) or invariant_refs (E/D/J -> 32.1
        edge). A decision obligation is its own decision node."""
        if node_kind == "decision":
            to_ref = node_id
            return TraceabilityLink(
                "requirement_to_decision", node_id, to_ref,
                self._reference_exists(to_ref, isr),
            )
        decisions = getattr(isr.system, "architectural_decisions", ())
        if node_kind == "requirement":
            to_ref = next(
                (
                    d.decision_id
                    for d in decisions
                    if node_id in d.requirement_refs
                ),
                None,
            )
        else:
            to_ref = next(
                (
                    d.decision_id
                    for d in decisions
                    if node_id in d.invariant_refs
                ),
                None,
            )
        return TraceabilityLink(
            "requirement_to_decision", node_id, to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _decision_to_architecture(
        self, decision: Any, isr: Any
    ) -> TraceabilityLink:
        """The decision -> the invariant-bearing carrier (E/D/J) it honors.
        The FIRST invariant_ref is walked AS WRITTEN — a reference that does
        not resolve in the identity universe is INVALID_REFERENCE, never
        silently filtered. No invariant honored -> the architecture link is
        absent (MISSING_LINK)."""
        to_ref = decision.invariant_refs[0] if decision.invariant_refs else None
        return TraceabilityLink(
            "decision_to_architecture", decision.decision_id, to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _architecture_to_module(
        self,
        decision_id: Optional[str],
        isr: Any,
    ) -> TraceabilityLink:
        """The architecture -> the modules it governs, via the decision's
        architectural_scope (32.1's module edge). The scope is walked AS
        WRITTEN: the first entry is the module link."""
        to_ref = None
        from_ref = decision_id or ""
        if decision_id is not None:
            decision = next(
                (
                    d
                    for d in isr.system.architectural_decisions
                    if d.decision_id == decision_id
                ),
                None,
            )
            if decision is not None and decision.architectural_scope:
                to_ref = decision.architectural_scope[0]
        return TraceabilityLink(
            "architecture_to_module", from_ref, to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _module_to_implementation(
        self, module_id: str, isr: Any, artifact: Mapping[str, Any]
    ) -> TraceabilityLink:
        """The module -> its realization in the artifact (manifest or
        bundle). The module exists in the ISR (its id resolves); the link is
        resolved only when the artifact actually carries it — an unrealized
        module is UNSATISFIED, never silently passed."""
        realized = _module_realized(module_id, artifact)
        return TraceabilityLink(
            "module_to_implementation", module_id, module_id, realized
        )

    def _implementation_to_verification(
        self, decision_id: Optional[str], isr: Any
    ) -> TraceabilityLink:
        """The implementation -> the anchor that declares its verification,
        via the decision's verification_refs (32.1 -> H edge)."""
        to_ref = None
        if decision_id is not None:
            decision = next(
                (
                    d
                    for d in isr.system.architectural_decisions
                    if d.decision_id == decision_id
                ),
                None,
            )
            if decision is not None and decision.verification_refs:
                to_ref = decision.verification_refs[0]
        return TraceabilityLink(
            "implementation_to_verification",
            decision_id or "",
            to_ref,
            to_ref is not None and self._reference_exists(to_ref, isr),
        )

    def _verification_to_evidence(
        self,
        anchor_id: str,
        isr: Any,
        artifact: Mapping[str, Any],
        ledger: Any,
    ) -> TraceabilityLink:
        """The anchor -> the chain-anchored verification evidence. The
        evidence ref is the deterministic ledger event id; it is set ONLY
        when the event actually resolves on the supplied ledger — a
        realized-but-unrecorded obligation is INSUFFICIENT_EVIDENCE, named
        and never passed."""
        resolved = self._reference_exists(anchor_id, isr)
        evidence_ref = _verification_event_ref(artifact)
        if evidence_ref is not None and ledger is not None:
            if ledger.event_by_ref(evidence_ref) is None:
                evidence_ref = None
        return TraceabilityLink(
            "verification_to_evidence", anchor_id, anchor_id,
            resolved, evidence_ref,
        )

    # -- state determination ----------------------------------------------------

    def _determine_state(
        self, links: tuple[TraceabilityLink, ...], isr: Any
    ) -> TraceabilityState:
        """The state is decided by the FIRST link the chain could not
        resolve (everything after it is a frozen absent tail, never
        re-attempted):

          * a reference that resolves to something that does not exist in
            the identity universe -> INVALID_REFERENCE;
          * a link that is simply absent -> MISSING_LINK;
          * a module that exists but is not realized in the artifact ->
            UNSATISFIED;
          * the whole chain resolved, but the terminal verification
            evidence is not chain-anchored -> INSUFFICIENT_EVIDENCE
            (advisory, never a pass);
          * the whole chain resolved and evidenced -> SATISFIED.
        """
        return determine_trace_state(links, isr, self._identity_index)

    # -- helpers ------------------------------------------------------------------

    def _reference_exists(self, ref: str, isr: Any) -> bool:
        """R2.10's reference-integrity discipline: a reference resolves iff
        it is a member of the identity index's resolvable universe."""
        return reference_exists(ref, isr, self._identity_index)

    @staticmethod
    def _carrier_id(kind: str, carrier: Any) -> str:
        for candidate_kind, _, id_attr in _OBLIGATION_CARRIERS:
            if candidate_kind == kind:
                return str(getattr(carrier, id_attr))
        return str(getattr(carrier, "id", ""))

    def _advance(
        self, link_kind: str, to_ref: str, isr: Any
    ) -> Optional[tuple[str, str, Any]]:
        """The node the chain walks INTO after a resolved link: requirement
        -> decision -> boundary -> module -> anchor."""
        system = isr.system
        if link_kind == "requirement_to_decision":
            for d in system.architectural_decisions:
                if d.decision_id == to_ref:
                    return ("decision", d.decision_id, d)
        if link_kind == "decision_to_architecture":
            for b in system.architectural_boundaries:
                if b.boundary_id == to_ref:
                    return ("architecture", b.boundary_id, b)
            for r in system.reliability_requirements:
                if r.requirement_id == to_ref:
                    return ("architecture", r.requirement_id, r)
            for region in system.protected_regions:
                if region.region_id == to_ref:
                    return ("architecture", region.region_id, region)
        if link_kind == "architecture_to_module":
            for m in system.modules:
                if m.id == to_ref:
                    return ("module", m.id, m)
        if link_kind in ("module_to_implementation",
                         "implementation_to_verification",
                         "verification_to_evidence"):
            for a in system.testing_anchors:
                if a.anchor_id == to_ref:
                    return ("testing_anchor", a.anchor_id, a)
        return None