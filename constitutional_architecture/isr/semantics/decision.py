"""R2.10.32.1 — ArchitecturalDecision: the ISR's decision-record carrier.

Architectural decisions are the traceability spine of a system: WHY a
strategy was selected over its alternatives. They are first-class ISR
objects because decisions are ARCHITECTURE — they explain the system's
shape — and because later phases (traceability, threat-model chains,
responsibility analysis) need them addressable by identity, not buried in
free text.

The carrier is the ADR's constitutionally complete skeleton (the
arc42/ADR mapping is explicit in the field names):

    arc42 Context          -> context
    arc42 Problem           -> question
    arc42 Alternatives      -> alternatives
    arc42 Trade-offs        -> trade_offs
    arc42 Benefits          -> benefits
    arc42 Risks             -> risks  (declared risks of the choice)
    arc42 Risks (rejected)  -> rejected  (alternative -> reasons rejected)
    arc42 Future evolution  -> future_evolution

A decision is a RECORD of an actual choice: it must consider at least two
alternatives, must select one of them, and must justify itself (at least
one of trade_offs / benefits). A single option is not a decision; an
unexplained decision is not a decision.

Reference edges (all resolved against the existing ISR constructs, never
invented here):

    * requirement_refs     -> F's requirements (the obligations the
                              decision serves)
    * invariant_refs       -> the invariant-bearing carriers of E/D/J
                              (boundary ids, reliability requirement ids,
                              protected region ids)
    * architectural_scope  -> the System's modules (what the decision
                              governs)
    * verification_refs    -> H's testing anchors — OBLIGATION/PROVENANCE
                              edges, never proof that verification
                              occurred. The ISR declares what evidence
                              must establish; the evaluation system
                              produces it; certification judges it. A
                              decision asserting "TEST-123 PASSED" would
                              shortcut that three-layer separation, so the
                              carrier structurally cannot hold verdicts.

Boundaries (what this carrier MUST NOT become):

    * It does NOT generate decisions, infer ADRs, or evaluate design
      quality — it is a record, and records do not judge themselves.
    * It does NOT author obligations: Phase 32 (certification) is the
      CONSUMER of decisions, never their author — the ISR is the only
      source of truth, and the authorship boundary is structural.
    * It carries no realization technology: DECISION_REALIZATION_TERMS
      gates the canonical semantic form (a decision about "python" is an
      implementation note, not architecture).
    * No architecture_ref / implementation_refs fields yet — resolving
      decisions to their implementing structures is the traceability
      phase's job (R2.10.32.2), which walks the existing structures.

The carrier is empty identity-neutral (R2.10.2 Option A): a system with no
decisions hashes identically to a system without the field. When
populated, decisions participate in the identity index like any other
gene — addressable by ("decision", decision_id), referenceable by J's
protected regions, and carried by the consumption contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class DecisionValidationError(ValueError):
    """An architectural decision violates its construction or structural contract."""


@dataclass(frozen=True)
class ArchitecturalDecision:
    """A record of an actual architectural choice, in ADR-complete form.

    The carrier maps the ADR skeleton onto ISR semantics: context is the
    situation, question the decision problem, alternatives the real
    options, selected_strategy the chosen one, and the trade-off/benefit/
    risk/rejection fields the decision's own justification. Reference
    fields resolve against existing constructs (requirements from F,
    invariants from E/D/J, modules from the System, verification from H's
    anchors) — this carrier authors NO new obligation.
    """

    decision_id: str
    context: str
    question: str
    selected_strategy: str
    alternatives: tuple[str, ...]
    trade_offs: tuple[str, ...] = ()
    benefits: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    rejected: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    future_evolution: tuple[str, ...] = ()
    requirement_refs: tuple[str, ...] = ()
    invariant_refs: tuple[str, ...] = ()
    architectural_scope: tuple[str, ...] = ()
    verification_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise DecisionValidationError("decision_id is required")
        if not self.context:
            raise DecisionValidationError("context is required")
        if not self.question:
            raise DecisionValidationError("question is required")
        if len(self.alternatives) < 2:
            raise DecisionValidationError(
                f"decision '{self.decision_id}' must consider at least two "
                f"alternatives — a single option is not a decision"
            )
        if self.selected_strategy not in self.alternatives:
            raise DecisionValidationError(
                f"decision '{self.decision_id}' selected_strategy "
                f"'{self.selected_strategy}' is not among its alternatives"
            )
        if not self.trade_offs and not self.benefits:
            raise DecisionValidationError(
                f"decision '{self.decision_id}' must declare trade_offs or "
                f"benefits — an unexplained decision is not a decision"
            )


# -- mechanism lint (the dangerous boundary — no realization technology) -------

DECISION_REALIZATION_TERMS: frozenset[str] = frozenset({
    # frameworks
    "react", "django", "flask", "fastapi", "spring", "rails", "angular",
    "vue", "svelte", "express", "ktor",
    # languages / runtimes
    "python", "javascript", "typescript", "java", "golang", "go", "rust",
    "csharp", "c#", "ruby", "php", "kotlin", "scala",
    # databases / infrastructure
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "kubernetes", "docker", "aws", "azure", "gcp", "terraform",
})


def realization_terms_present(content: str) -> tuple[str, ...]:
    """Which realization terms (if any) appear in canonical decision content.

    The scan runs over the LOWERCASED canonical form, so a decision about
    "direct database access" passes while one prescribing "postgres"
    fails — the ISR declares the architectural choice, never the
    implementation technology.
    """
    return tuple(
        term for term in DECISION_REALIZATION_TERMS if term in content.lower()
    )


def assert_decision_technology_agnostic(decision: ArchitecturalDecision) -> None:
    """Gate: no framework/language/database may leak into a decision.

    ``"adopt a purpose-built query store"`` passes; ``"adopt postgres"``
    fails. The decision records the architectural choice; the realization
    selection is passed to the compiler at compile time and never embedded
    in the ISR.
    """
    hits = realization_terms_present(canonicalize(decision))
    if hits:
        raise DecisionValidationError(
            f"decision '{decision.decision_id}' couples to realization "
            f"term(s): {hits}"
        )


# -- structural validation (pre-execution) -------------------------------------

def _requirement_ids(system: Any) -> set[str]:
    return {r.requirement_id for r in system.requirements}


def _invariant_carrier_ids(system: Any) -> set[str]:
    """The invariant-bearing carriers of E/D/J: boundary ids, reliability
    requirement ids, and protected region ids. The invariants THEMSELVES
    are statements inside those carriers (no separate invariant id
    namespace exists); a decision references the carrier that declares the
    invariant it honors."""
    ids: set[str] = {b.boundary_id for b in system.architectural_boundaries}
    ids.update(r.requirement_id for r in system.reliability_requirements)
    ids.update(r.region_id for r in system.protected_regions)
    return ids


def validate_system_decision_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's architectural decisions.

    Rejects, pre-execution: duplicate decision ids and dangling reference
    edges — requirement_refs must name F's requirements, invariant_refs
    must name E/D/J's invariant-bearing carriers, architectural_scope must
    name modules, and verification_refs must name H's testing anchors.
    Empty tuple means valid.
    """
    errors: list[str] = []
    requirement_ids = _requirement_ids(system)
    invariant_ids = _invariant_carrier_ids(system)
    module_ids = {m.id for m in system.modules}
    anchor_ids = {a.anchor_id for a in system.testing_anchors}
    seen: set[str] = set()
    for decision in system.architectural_decisions:
        if decision.decision_id in seen:
            errors.append(f"duplicate decision id '{decision.decision_id}'")
        seen.add(decision.decision_id)
        for ref in decision.requirement_refs:
            if ref not in requirement_ids:
                errors.append(
                    f"decision '{decision.decision_id}' requirement_ref "
                    f"'{ref}' does not name a requirement (F)"
                )
        for ref in decision.invariant_refs:
            if ref not in invariant_ids:
                errors.append(
                    f"decision '{decision.decision_id}' invariant_ref "
                    f"'{ref}' does not name an invariant-bearing carrier (E/D/J)"
                )
        for ref in decision.architectural_scope:
            if ref not in module_ids:
                errors.append(
                    f"decision '{decision.decision_id}' architectural_scope "
                    f"'{ref}' does not name a module"
                )
        for ref in decision.verification_refs:
            if ref not in anchor_ids:
                errors.append(
                    f"decision '{decision.decision_id}' verification_ref "
                    f"'{ref}' does not name a testing anchor (H)"
                )
    return tuple(errors)


# -- projection (semantics only) ------------------------------------------------

def project_architectural_decisions(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of the decision record.

    Returns the ADR-complete declarations (context, question, alternatives,
    selection, justification, rejected alternatives, future evolution, and
    the four reference edges). Never verdicts, never verification results,
    never implementation artifacts.
    """
    return tuple(
        canonical_form(decision)
        for decision in getattr(isr.system, "architectural_decisions", ())
    )