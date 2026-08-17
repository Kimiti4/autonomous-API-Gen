"""R2.10.3-F — requirements & acceptance traceability primitive.

Requirements are SEMANTIC OBLIGATIONS, not implementation tasks. The ISR
declares what must be accomplished and what must be demonstrably true for
acceptance; the Evaluation Engine makes the epistemic determination; the
testing/anchoring primitive (H) provides the durable evidence binding.

The acceptance criterion sits deliberately in the middle layer between
"too weak to evaluate" (``statement = "system is reliable"`` — nothing
mechanically determinable) and "too coupled to a testing technology"
(``pytest_test = "test_reliability.py"`` — the ISR becomes a test manifest).
The obligation carries a semantic KIND and SUBJECTS: enough for an
evaluation substrate to dispatch on, no mechanism for how.

This landing ACTIVATES B's reservation: ``BusinessCapability.requirement_refs``
was carried empty and unvalidated since R2.10.3-B; F introduces
``Requirement`` and makes those refs resolvable against ``System.requirements``
WITHOUT editing the ``BusinessCapability`` construct — the first real test of
whether the R2.10.2 derived dependency graph was correct.

Separation preserved: no ``is_satisfied()``, no score, no verdict in this
module. ``obligation + kind + subject_refs`` is exactly the surface a future
evaluator consumes; F declares what constitutes acceptance, it does not
determine whether acceptance is demonstrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class RequirementValidationError(ValueError):
    """A requirement or criterion violates its construction or structural contract."""


@unique
class ObligationKind(str, Enum):
    """The semantic KIND of obligation. A dispatch category for a future
    evaluation substrate — never a test mechanism."""

    ORDERING = "ORDERING"  # X must take effect before Y
    PRESENCE = "PRESENCE"  # X must be available / occur
    ABSENCE = "ABSENCE"  # X must not occur
    INVARIANT = "INVARIANT"  # X must always hold
    THRESHOLD = "THRESHOLD"  # X must remain within bounds


@dataclass(frozen=True)
class AcceptanceCriterion:
    """A semantic predicate: what must be demonstrably true for a requirement
    to be satisfied. NOT a test implementation.

    The ISR declares the obligation; the evaluation system makes the epistemic
    determination; testing/anchoring (H) provides the durable evidence binding.
    This type carries no is_satisfied(), no framework, no assertion — it is the
    thing evidence will later be bound TO, never the thing that evaluates.
    """

    criterion_id: str
    obligation: str  # semantic statement of what must be true
    kind: ObligationKind
    subject_refs: tuple[str, ...] = ()  # genes the criterion applies to

    def __post_init__(self) -> None:
        if not self.criterion_id:
            raise RequirementValidationError("criterion_id is required")
        if not self.obligation:
            raise RequirementValidationError("obligation is required")


@dataclass(frozen=True)
class Requirement:
    """A semantic obligation: what the system must accomplish. Not an
    implementation task. References capabilities and genes by identity."""

    requirement_id: str
    statement: str  # the obligation, semantically
    target_refs: tuple[str, ...]  # BusinessCapability ids this targets
    acceptance_refs: tuple[str, ...] = ()  # AcceptanceCriterion ids
    constraint_refs: tuple[str, ...] = ()  # ISR semantic genes this constrains

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise RequirementValidationError("requirement_id is required")
        if not self.statement:
            raise RequirementValidationError("statement is required")
        if not self.target_refs:
            raise RequirementValidationError(
                "target_refs required: an obligation must bind to something explicit"
            )


# -- acceptance neutrality lint (the middle layer's guard) ---------------------

REQUIREMENT_MECHANISM_TERMS: frozenset[str] = frozenset({
    # test frameworks / runners / assertion artifacts
    "pytest", "junit", "cypress", "selenium", "jest", "mocha", "testng",
    "test_file", "test_name", "test_case", "assertion_library",
    # probe mechanisms that belong to the evaluation surface, not the obligation
    "http_request", "sql_query", "browser_action", "grpc_call",
})


def requirement_mechanism_hits(value: Any) -> tuple[str, ...]:
    """Which test-mechanism terms (if any) leaked into a semantic form."""
    lowered = canonicalize(value).lower()
    return tuple(term for term in REQUIREMENT_MECHANISM_TERMS if term in lowered)


def assert_requirement_technology_agnostic(value: Any) -> None:
    """Gate: no test framework or probe mechanism may leak into the obligation.

    ``"Order cancellation must become effective before settlement"`` passes;
    ``"run test_cancel_order.py via pytest"`` fails. The obligation stays an
    obligation; testing/anchoring (H) owns the evidence binding.
    """
    hits = requirement_mechanism_hits(value)
    if hits:
        raise RequirementValidationError(
            f"requirement semantic couples to test mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -------------------------------------

def _gene_ids(system: Any) -> set[str]:
    """ISR semantic gene identities a requirement may constrain.

    The R2.10.3-E boundary identity space: modules, services, workflows,
    interfaces, policies, entities, and business capabilities.
    """
    ids: set[str] = set()
    for module in system.modules:
        ids.add(module.id)
        ids.update(service.id for service in module.services)
        ids.update(workflow.id for workflow in module.workflows)
        ids.update(interface.id for interface in module.interfaces)
        ids.update(policy.id for policy in module.policies)
        ids.update(entity.id for entity in module.entities)
    ids.update(capability.capability_id for capability in system.business_capabilities)
    return ids


def validate_system_requirement_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's requirements + criteria.

    Rejects, pre-execution: duplicate requirement ids, duplicate criterion
    ids, dangling target refs (must name business capabilities), dangling
    acceptance refs (must name declared criteria), dangling constraint refs
    (must name ISR genes), dangling criterion subject refs, and — the
    R2.10.3-B reservation activation — dangling ``requirement_refs`` on
    business capabilities. Empty tuple means valid.
    """
    errors: list[str] = []
    requirement_ids = {r.requirement_id for r in system.requirements}
    criterion_ids = {c.criterion_id for c in system.acceptance_criteria}
    capability_ids = {c.capability_id for c in system.business_capabilities}
    gene_ids = _gene_ids(system)

    seen_requirements: set[str] = set()
    for requirement in system.requirements:
        if requirement.requirement_id in seen_requirements:
            errors.append(
                f"duplicate requirement id '{requirement.requirement_id}'"
            )
        seen_requirements.add(requirement.requirement_id)
        for target_ref in requirement.target_refs:
            if target_ref not in capability_ids:
                errors.append(
                    f"requirement '{requirement.requirement_id}' targets unknown "
                    f"capability '{target_ref}'"
                )
        for acceptance_ref in requirement.acceptance_refs:
            if acceptance_ref not in criterion_ids:
                errors.append(
                    f"requirement '{requirement.requirement_id}' references "
                    f"unknown acceptance criterion '{acceptance_ref}'"
                )
        for constraint_ref in requirement.constraint_refs:
            if constraint_ref not in gene_ids:
                errors.append(
                    f"requirement '{requirement.requirement_id}' constrains "
                    f"unknown gene '{constraint_ref}'"
                )

    seen_criteria: set[str] = set()
    for criterion in system.acceptance_criteria:
        if criterion.criterion_id in seen_criteria:
            errors.append(
                f"duplicate acceptance criterion id '{criterion.criterion_id}'"
            )
        seen_criteria.add(criterion.criterion_id)
        for subject_ref in criterion.subject_refs:
            if subject_ref not in gene_ids:
                errors.append(
                    f"acceptance criterion '{criterion.criterion_id}' applies "
                    f"to unknown gene '{subject_ref}'"
                )

    # R2.10.3-B reservation ACTIVATED: requirement_refs now resolve.
    for capability in system.business_capabilities:
        for requirement_ref in capability.requirement_refs:
            if requirement_ref not in requirement_ids:
                errors.append(
                    f"business capability '{capability.capability_id}' "
                    f"references unknown requirement '{requirement_ref}'"
                )
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_requirements(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of requirement obligations.

    Returns the declared obligations (statement, targets, acceptance refs,
    constraint refs). Never test files, runners, assertions, or queries —
    those are evaluation/backend concerns, not the obligation.
    """
    return tuple(
        canonical_form(requirement)
        for requirement in getattr(isr.system, "requirements", ())
    )


def project_acceptance_criteria(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of acceptance criteria.

    Returns the semantic predicates (obligation + kind + subjects). Never
    test implementations — the criterion is the thing evidence is bound TO,
    never the thing that evaluates.
    """
    return tuple(
        canonical_form(criterion)
        for criterion in getattr(isr.system, "acceptance_criteria", ())
    )