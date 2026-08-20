"""R2.10.32.3 — SecurityThreat: the ISR's security-obligation carrier.

Security threats are the security-intent spine of a system: a scenario the
architecture is AUTHORSED against, an invariant certification will hold the
implementation to, and the reference edges that let a later phase walk the
chain Threat → requirement → invariant → architectural control →
implementation → verification → evidence (R2.10.32.4).

This is the constitution's "Security by Design" principle made a semantic
gene — "security is a core architectural concern... never treat security as
an afterthought": security as an obligation represented BEFORE
implementation, never a finding scanned AFTER it.

The carrier is an OBLIGATION the architecture is authored against, NOT a
finding a scanner produces. The ownership boundary is therefore identical
to R2.10.32.1's decision boundary:

    * the threat is SUPPLIED by evolution / architecture selection — it is
      authored in the ISR and never inferred from the implementation. An
      application "having authentication" does NOT imply its threats; that
      inference belongs upstream (requirement/architecture evolution) or in
      an explicit obligation-derivation stage (R2.10.32.6), never in
      certification.
    * Phase 32 (certification) is the CONSUMER of threats, never their
      author — the authorship boundary is structural (the certification
      package has no construction surface for SecurityThreat).
    * an unrepresented threat surface is named as a gap (the vacuity
      policy: "no threat obligation supplied for authentication surface"
      is an ADVISORY, never a CRITICAL violation — a CRITICAL requires an
      actual ISR obligation).

Reference edges (all resolved against the existing ISR constructs, never
invented here):

    * requirement_refs            -> F's requirements (the obligations the
                                     threat endangers)
    * architectural_control_refs  -> E's boundaries (the controls that
                                     address the threat)
    * implementation_obligation_refs -> the decision carrier (R2.10.32.1 —
                                     the ISR's implementation obligations)
    * verification_refs           -> H's testing anchors — OBLIGATION/
                                     PROVENANCE edges, never proof that
                                     verification occurred. A threat
                                     asserting "TEST-123 PASSED" would
                                     shortcut the three-layer separation;
                                     the carrier structurally cannot hold
                                     verdicts.

The carrier is empty identity-neutral (R2.10.2 Option A): a system with no
threats hashes identically to a system without the field. When populated,
threats participate in the identity index like any other gene — addressable
by ("threat", threat_id) and referenceable by J's protected regions.

Boundaries (what this carrier MUST NOT become):

    * It does NOT scan, inspect artifacts, or infer threats from the
      implementation — threat discovery belongs to evolution/architecture
      selection (and, later, R2.10.32.6's obligation-derivation stage,
      which produces DERIVED obligations with provenance, never scanner
      assumptions).
    * It does NOT walk its own chain — the threat-traceability walk is
      R2.10.32.4, which consumes this carrier through the epistemic pattern
      R2.10.32.2 established.
    * It carries no security technology: THREAT_REALIZATION_TERMS gates the
      canonical semantic form (a threat about "JWT manipulation" is an
      implementation note, not a security concern — JWT/OAuth/mTLS are
      compiler backends per the constitution's plugin-first principle).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class ThreatValidationError(ValueError):
    """A security threat violates its construction or structural contract."""


class ThreatRealizationError(ThreatValidationError):
    """A threat couples to a security/messaging technology instead of a
    security concern (the plugin-first boundary, as in R2.10.32.1)."""


@unique
class ThreatSeverity(str, Enum):
    """The declared severity of a threat the architecture must defend
    against. A declaration, never a measurement — the ISR says how serious
    the threat is understood to be; certification holds the implementation
    to the invariant, it does not re-grade the threat."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class SecurityThreat:
    """A first-class ISR object: a security threat the architecture must
    defend against — the constitution's "Security by Design" principle made
    a semantic gene.

    The threat is an OBLIGATION the architecture is authored against, not a
    finding a scanner produces: it is supplied by evolution / architecture
    selection, referenced by identity, and consumed by certification.
    Reference-by-identity throughout, consistent with every R2.10 carrier
    and with 32.1's decision gene, so the threat is independently evolvable
    and traceable through the chain 32.4 will walk:
    Threat → requirement → invariant → architectural control →
    implementation → verification → evidence.
    """

    threat_id: str
    scenario: str                                # the threat scenario (technology-neutral)
    severity: ThreatSeverity
    requirement_refs: tuple[str, ...]            # security requirements this threatens
    invariant_statement: str                     # the security invariant that must hold
    architectural_control_refs: tuple[str, ...]  # boundaries/controls addressing it
    implementation_obligation_refs: tuple[str, ...]
    verification_refs: tuple[str, ...]           # tests/evidence verifying mitigation

    def __post_init__(self) -> None:
        if not self.threat_id:
            raise ThreatValidationError("threat_id is required")
        if not self.scenario:
            raise ThreatValidationError("a threat must state its scenario")
        if not self.invariant_statement:
            raise ThreatValidationError(
                "a threat without an invariant is undefined — the invariant "
                "is what certification will hold the implementation to"
            )
        if not self.requirement_refs and not self.architectural_control_refs:
            raise ThreatValidationError(
                "a threat must be tied to a requirement or an architectural "
                "control"
            )


# -- mechanism lint (the dangerous boundary — no security technology) -----------

THREAT_REALIZATION_TERMS: frozenset[str] = frozenset({
    # authentication / identity technologies
    "jwt", "jws", "jwe", "oauth", "oidc", "saml", "kerberos", "webauthn",
    "keycloak", "cognito", "okta", "mtls", "tls", "ssl",
    # credential / session formats
    "api key", "bearer token", "access token", "session cookie",
    # messaging / transport
    "kafka", "rabbitmq", "pulsar", "nats", "grpc", "websocket",
    # cryptography primitives-as-technology
    "aes", "rsa", "sha256",
})


def threat_terms_present(content: str) -> tuple[str, ...]:
    """Which security/messaging realization terms (if any) appear in
    canonical threat content.

    The scan runs over the LOWERCASED canonical form, so a threat about
    "credential theft during cross-context requests" passes while one
    prescribing "JWT manipulation" fails — the ISR declares the security
    concern, never the security technology (JWT/OAuth/mTLS are compiler
    backends per the constitution's plugin-first principle).
    """
    return tuple(
        term for term in THREAT_REALIZATION_TERMS if term in content.lower()
    )


def validate_threat_neutrality(threat: SecurityThreat) -> None:
    """Gate: no security/messaging technology may leak into a threat.

    ``"credential theft"`` passes; ``"JWT manipulation"`` fails. The threat
    records the security concern; the realizing technology is selected by
    the compiler at compile time and never embedded in the ISR.
    """
    hits = threat_terms_present(canonicalize(threat))
    if hits:
        raise ThreatRealizationError(
            f"threat '{threat.threat_id}' couples to security realization "
            f"term(s): {hits}"
        )


# -- structural validation (pre-execution) --------------------------------------

def _requirement_ids(system: Any) -> set[str]:
    return {r.requirement_id for r in system.requirements}


def _boundary_ids(system: Any) -> set[str]:
    return {b.boundary_id for b in system.architectural_boundaries}


def _decision_ids(system: Any) -> set[str]:
    return {d.decision_id for d in system.architectural_decisions}


def _anchor_ids(system: Any) -> set[str]:
    return {a.anchor_id for a in system.testing_anchors}


def validate_system_threat_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's security threats.

    Rejects, pre-execution: duplicate threat ids and dangling reference
    edges — requirement_refs must name F's requirements,
    architectural_control_refs must name E's boundaries,
    implementation_obligation_refs must name the decision/obligation
    carriers (R2.10.32.1), and verification_refs must name H's testing
    anchors. Empty tuple means valid.
    """
    errors: list[str] = []
    requirement_ids = _requirement_ids(system)
    boundary_ids = _boundary_ids(system)
    decision_ids = _decision_ids(system)
    anchor_ids = _anchor_ids(system)
    seen: set[str] = set()
    for threat in system.security_threats:
        if threat.threat_id in seen:
            errors.append(f"duplicate threat id '{threat.threat_id}'")
        seen.add(threat.threat_id)
        for ref in threat.requirement_refs:
            if ref not in requirement_ids:
                errors.append(
                    f"threat '{threat.threat_id}' requirement_ref "
                    f"'{ref}' does not name a requirement (F)"
                )
        for ref in threat.architectural_control_refs:
            if ref not in boundary_ids:
                errors.append(
                    f"threat '{threat.threat_id}' architectural_control_ref "
                    f"'{ref}' does not name a boundary (E)"
                )
        for ref in threat.implementation_obligation_refs:
            if ref not in decision_ids:
                errors.append(
                    f"threat '{threat.threat_id}' implementation_obligation_ref "
                    f"'{ref}' does not name a decision/obligation carrier"
                )
        for ref in threat.verification_refs:
            if ref not in anchor_ids:
                errors.append(
                    f"threat '{threat.threat_id}' verification_ref "
                    f"'{ref}' does not name a testing anchor (H)"
                )
    return tuple(errors)