"""R2.10.3-H — testing_anchoring primitive (intent and anchoring relationships).

H closes the loop between the ISR's semantic obligations and the evaluation
boundary — WITHOUT becoming a test-generation primitive. The inversion that
lets the testing layer define the software's meaning is the specific failure
mode H exists to avoid. The principle held since R2.8: **the ISR declares
what evidence must establish; the evaluation system determines how that
evidence is produced.** H is the declaration side, full stop.

A TestingAnchor declares:
  * WHICH semantic obligation is being demonstrated (obligation_refs → F's
    AcceptanceCriterion ids)
  * WHICH genes are exercised (subject_refs → behaviors/capabilities/
    requirements)
  * WHAT evidence must establish (evidence_requirements — semantic)
  * WHAT must remain protected (protection_policy — R2.8.7's
    protected-evaluation-surface semantics generalized into the ISR)
  * WHETHER the anchor is a fixed reference or follows its subjects
    (authority)

It contains NO test file, function, framework, fixture, marker, or execution
mechanism — those belong to the evaluation/compiler infrastructure. The
structural field guard leaves nowhere to put them, and
TESTING_MECHANISM_TERMS gates the canonical semantic form.

Scope holds:
  * H does NOT evaluate — no is_satisfied(), no verdict, no execution.
  * H does NOT wire obligation→anchor→evidence into the live evaluation
    loop — obligation_refs RESOLVE against System.acceptance_criteria
    (F's construct, untouched); binding an anchor to produced evidence is
    the evaluation system's follow-up, exactly as F left satisfaction to
    the evaluator.

Protection reuses the R2.8/E mechanism: a PROTECTED anchor's removal or
modification raises ConstitutionalViolation — one protection mechanism
across primitives, not a parallel security model.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class TestingAnchorValidationError(ValueError):
    """A testing anchor violates its construction or structural contract."""


@unique
class ProtectionPolicy(str, Enum):
    """Whether the anchor is immutable or may evolve.

    PROTECTED reuses R2.8.7's protected-evaluation-surface semantics:
    modification/removal is a constitutional violation, not an edit.
    """

    PROTECTED = "PROTECTED"
    EVOLVABLE = "EVOLVABLE"


@unique
class AnchorAuthority(str, Enum):
    """Whether the anchor is a fixed reference or follows its subjects."""

    AUTHORITATIVE = "AUTHORITATIVE"  # stable reference for evaluation
    DERIVED = "DERIVED"  # evolves with its subjects


@dataclass(frozen=True)
class TestingAnchor:
    """Testing intent and anchoring relationships. NOT a test implementation.

    Declares which semantic obligation is being demonstrated, which genes
    are exercised, what evidence must establish, and what must remain
    protected. Contains NO test file, function, framework, fixture, marker,
    or execution mechanism — those belong to the evaluation/compiler
    infrastructure.

    This is the declaration side of the ISR↔evidence loop. The evaluation
    system produces the evidence; the anchor declares what it must establish.
    """

    anchor_id: str
    subject_refs: tuple[str, ...]  # genes exercised (behaviors/capabilities/requirements)
    obligation_refs: tuple[str, ...] = ()  # AcceptanceCriterion ids demonstrated (F)
    evidence_requirements: tuple[str, ...] = ()  # semantic evidence obligations
    protection_policy: ProtectionPolicy = ProtectionPolicy.EVOLVABLE
    authority: AnchorAuthority = AnchorAuthority.DERIVED

    def __post_init__(self) -> None:
        if not self.anchor_id:
            raise TestingAnchorValidationError("anchor_id is required")
        if not self.subject_refs:
            raise TestingAnchorValidationError(
                "subject_refs required: an anchor must anchor something explicit"
            )


# -- mechanism lint (the dangerous boundary — no test machinery) --------------

TESTING_MECHANISM_TERMS: frozenset[str] = frozenset({
    # frameworks / runners
    "pytest", "junit", "cypress", "selenium", "jest", "mocha", "testng", "rspec",
    # test implementation artifacts
    "test_file", "test_function", "test_name", "test_case",
    "fixture", "conftest", "pytest_marker", "assert_function", "mock_object",
    # execution mechanisms
    "docker_command", "shell_command", "ci_step", "runner_config",
})


def testing_mechanism_hits(anchor: TestingAnchor) -> tuple[str, ...]:
    """Which test-mechanism terms (if any) leaked into an anchor's semantic form."""
    lowered = canonicalize(anchor).lower()
    return tuple(term for term in TESTING_MECHANISM_TERMS if term in lowered)


def assert_testing_technology_agnostic(anchor: TestingAnchor) -> None:
    """Gate: no test framework or execution mechanism may leak into the anchor.

    ``"settlement must demonstrate ORDERING before authorization"`` passes;
    ``"run test_cancel_order.py via pytest"`` fails. The anchor stays the
    declaration; the evaluation system owns the evidence production.
    """
    hits = testing_mechanism_hits(anchor)
    if hits:
        raise TestingAnchorValidationError(
            f"anchor '{anchor.anchor_id}' couples to test mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _subject_gene_ids(system: Any) -> set[str]:
    """The anchor identity space: behaviors (workflow ids), capabilities,
    and requirements — the genes an anchor can anchor."""
    ids: set[str] = set()
    for module in system.modules:
        ids.update(workflow.id for workflow in module.workflows)
    ids.update(c.capability_id for c in system.business_capabilities)
    ids.update(r.requirement_id for r in system.requirements)
    return ids


def validate_system_testing_anchor_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's testing anchors.

    Rejects, pre-execution: duplicate anchor ids, dangling subject refs
    (must name behaviors/capabilities/requirements), and dangling obligation
    refs (must name F's AcceptanceCriterion ids). The obligation_refs edge
    resolves against System.acceptance_criteria WITHOUT editing F's
    construct. Empty tuple means valid.
    """
    errors: list[str] = []
    subject_ids = _subject_gene_ids(system)
    criterion_ids = {c.criterion_id for c in system.acceptance_criteria}
    seen: set[str] = set()
    for anchor in system.testing_anchors:
        if anchor.anchor_id in seen:
            errors.append(f"duplicate anchor id '{anchor.anchor_id}'")
        seen.add(anchor.anchor_id)
        for subject_ref in anchor.subject_refs:
            if subject_ref not in subject_ids:
                errors.append(
                    f"anchor '{anchor.anchor_id}' subjects unknown gene "
                    f"'{subject_ref}'"
                )
        for obligation_ref in anchor.obligation_refs:
            if obligation_ref not in criterion_ids:
                errors.append(
                    f"anchor '{anchor.anchor_id}' demonstrates unknown "
                    f"acceptance criterion '{obligation_ref}'"
                )
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_testing_anchors(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of testing anchors.

    Returns the anchoring declarations (subjects, obligations, evidence
    requirements, protection, authority). Never test files, functions,
    frameworks, fixtures, markers, or execution commands — those are
    evaluation/compiler infrastructure, not the anchor.
    """
    return tuple(
        canonical_form(anchor)
        for anchor in getattr(isr.system, "testing_anchors", ())
    )