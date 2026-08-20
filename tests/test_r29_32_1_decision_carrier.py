"""R2.10.32.1 — the ArchitecturalDecision ISR carrier: the decision record.

The carrier makes architectural decisions first-class ISR objects: WHY the
system's shape is what it is, in ADR-complete form, addressable by identity,
and structurally incapable of authoring obligations. The acceptance surface:

    * the carrier is constitutionally ADR-complete (every ADR element has a
      field: context, problem->question, alternatives, trade-offs, benefits,
      risks/rejected, future evolution);
    * the selection is a real choice: selected_strategy must be among >=2
      alternatives, and an unexplained decision (no trade_offs, no benefits)
      is rejected;
    * the carrier is empty identity-neutral (R2.10.2 Option A): the frozen
      recipe ISR and the capability matrix are byte-identical before and
      after the carrier lands;
    * a populated decision participates in the identity index like any other
      gene — addressed by ("decision", decision_id), path-identifiable,
      protectable by J, ref-verified against the existing carriers;
    * technology neutrality: no framework/language/database may leak into a
      decision;
    * the authorship boundary is structural: Phase 32 (certification) is the
      CONSUMER of decisions, never their author — the ISR is the only
      author.
"""
import ast
import pathlib

import pytest

import tiannara
from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    BusinessCapability,
    Entity,
    FailureMode,
    Module,
    ProtectedRegion,
    ProtectionKind,
    ReliabilityRequirement,
    Requirement,
    TestingAnchor as AnchorDeclaration,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.decision import (
    ArchitecturalDecision,
    DecisionValidationError,
    assert_decision_technology_agnostic,
    project_architectural_decisions,
    realization_terms_present,
    validate_system_decision_constraints,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    validate_system_evolution_policy_constraints,
)
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    canonicalize,
    semantic_content_hash,
)
from tiannara.application.evolution.identity_index import IdentityIndex

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def minimal_decision() -> ArchitecturalDecision:
    """The smallest constitutionally valid decision: two alternatives, one
    selected, one justification field. Deliberately free of any
    realization vocabulary."""
    return ArchitecturalDecision(
        decision_id="d1",
        context="c",
        question="q",
        selected_strategy="a",
        alternatives=("a", "b"),
        trade_offs=("t",),
        benefits=(),
        risks=(),
        rejected={},
        future_evolution=(),
    )


def empty_system_isr() -> ISR:
    """An ISR with no decisions (and no other semantic carriers)."""
    return ISR(
        system=System(
            id="dec-sys",
            name="DecisionSystem",
            modules=(
                Module(
                    id="MOD-A",
                    name="MOD-A",
                    entities=(Entity(id="e1", name="e1"),),
                ),
            ),
        )
    )


def decision_system() -> ISR:
    """A populated ISR: one decision whose four reference edges resolve
    against the existing carriers — requirements from F (REQ-001),
    invariants from E/D/J (BND-001, REL-001, REG-001), modules from the
    System (MOD-A), verification from H's anchors (ANCHOR-001)."""
    capability = BusinessCapability(
        capability_id="CAP-001",
        intent="settlement ordering across contexts",
    )
    requirement = Requirement(
        requirement_id="REQ-001",
        statement="settlement must become effective in the same order as "
        "authorization",
        target_refs=("CAP-001",),
    )
    boundary = ArchitecturalBoundary(
        boundary_id="BND-001",
        member_refs=("MOD-A",),
    )
    reliability = ReliabilityRequirement(
        requirement_id="REL-001",
        target_refs=("CAP-001",),
        failure_modes=(FailureMode.PARTIAL_CAPACITY_LOSS,),
    )
    region = ProtectedRegion(
        region_id="REG-001",
        subject_refs=("CAP-001",),
        protection_kind=ProtectionKind.IMMUTABLE,
    )
    anchor = AnchorDeclaration(
        anchor_id="ANCHOR-001",
        subject_refs=("REQ-001",),
    )
    decision = ArchitecturalDecision(
        decision_id="DEC-001",
        context="the system must guarantee settlement ordering across "
        "bounded contexts",
        question="how should cross-context ordering be guaranteed",
        selected_strategy="eventual ordering via a durable record",
        alternatives=(
            "eventual ordering via a durable record",
            "synchronous coupling",
        ),
        trade_offs=(
            "synchronous coupling trades availability for immediacy",
        ),
        benefits=(
            "the durable record preserves ordering independent of availability",
        ),
        risks=("records grow unboundedly",),
        rejected={
            "synchronous coupling": (
                "locks writers to readers",
                "reduces availability",
            ),
        },
        future_evolution=("a bounded replay window",),
        requirement_refs=("REQ-001",),
        invariant_refs=("BND-001", "REL-001", "REG-001"),
        architectural_scope=("MOD-A",),
        verification_refs=("ANCHOR-001",),
    )
    return ISR(
        system=System(
            id="dec-sys",
            name="DecisionSystem",
            modules=(
                Module(
                    id="MOD-A",
                    name="MOD-A",
                    entities=(Entity(id="e1", name="e1"),),
                ),
            ),
            business_capabilities=(capability,),
            requirements=(requirement,),
            architectural_boundaries=(boundary,),
            reliability_requirements=(reliability,),
            protected_regions=(region,),
            testing_anchors=(anchor,),
            architectural_decisions=(decision,),
        )
    )


@pytest.fixture(scope="module")
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


# -- the carrier is constitutionally ADR-complete -------------------------------


def test_decision_carrier_is_constitutionally_complete():
    """Every ADR element has a carrier field: Context -> context,
    Problem -> question, Alternatives -> alternatives, Selection ->
    selected_strategy, Trade-offs -> trade_offs, Benefits -> benefits,
    Risks -> risks/rejected, Future evolution -> future_evolution."""
    fields = frozenset(ArchitecturalDecision.__dataclass_fields__)
    assert {
        "decision_id",
        "context",
        "question",
        "selected_strategy",
        "alternatives",
        "trade_offs",
        "benefits",
        "risks",
        "rejected",
        "future_evolution",
        "requirement_refs",
        "invariant_refs",
        "architectural_scope",
        "verification_refs",
    } <= fields
    decision = minimal_decision()
    assert decision.context
    assert decision.question
    assert decision.selected_strategy in decision.alternatives
    assert len(decision.alternatives) >= 2
    assert decision.trade_offs or decision.benefits
    assert isinstance(decision.rejected, dict)


def test_selected_strategy_must_be_an_alternative():
    with pytest.raises(DecisionValidationError):
        ArchitecturalDecision(
            decision_id="d-x",
            context="c",
            question="q",
            selected_strategy="not-considered",
            alternatives=("a", "b"),
            trade_offs=("t",),
            benefits=(),
        )


def test_single_option_is_not_a_decision():
    with pytest.raises(DecisionValidationError):
        ArchitecturalDecision(
            decision_id="d-x",
            context="c",
            question="q",
            selected_strategy="only",
            alternatives=("only",),
            trade_offs=("t",),
            benefits=(),
        )


def test_unexplained_decision_rejected():
    with pytest.raises(DecisionValidationError):
        ArchitecturalDecision(
            decision_id="d-x",
            context="c",
            question="q",
            selected_strategy="a",
            alternatives=("a", "b"),
            trade_offs=(),
            benefits=(),
        )


# -- identity neutrality (Option A) ---------------------------------------------


def test_decision_carrier_is_identity_neutral_when_empty(campaign_harness):
    """An empty decision carrier is byte-identical to no carrier at all:
    the frozen recipe ISR hashes exactly as before the field existed."""
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH
    canonical = canonical_form(empty_system_isr().system)
    assert "architectural_decisions" not in canonical


def test_empty_carrier_omitted_from_canonical_projection():
    populated = canonical_form(decision_system().system)
    assert "architectural_decisions" in populated


def test_matrix_and_recipe_unchanged(campaign_harness):
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH
    assert campaign_harness.matrix_summary() == (12, 18, 0, 0)


# -- the identity index ----------------------------------------------------------


def test_decision_participates_in_the_identity_index():
    populated_index = IdentityIndex.derive(decision_system())
    assert ("decision", "DEC-001") in populated_index.genes
    assert populated_index.genes[("decision", "DEC-001")].decision_id == "DEC-001"
    assert (
        populated_index.path_identities["system.architectural_decisions[0]"]
        == "DEC-001"
    )
    assert populated_index.genes_by_domain()["decision"] == (
        ("DEC-001", populated_index.genes[("decision", "DEC-001")]),
    )
    assert populated_index.dangling_references == ()
    empty_index = IdentityIndex.derive(empty_system_isr())
    assert not empty_index.genes_by_domain().get("decision")
    assert semantic_content_hash(decision_system()) != semantic_content_hash(
        empty_system_isr()
    )


def test_decision_reference_edges_resolve():
    """The four reference edges resolve against the existing carriers:
    requirement_refs -> F's requirements, invariant_refs -> E/D/J's
    invariant-bearing carriers, architectural_scope -> modules,
    verification_refs -> H's anchors. A dangling edge is rejected."""
    assert validate_system_decision_constraints(decision_system().system) == ()
    dangling = decision_system().system
    dangling = dangling.__class__(
        id=dangling.id,
        name=dangling.name,
        modules=dangling.modules,
        business_capabilities=dangling.business_capabilities,
        requirements=dangling.requirements,
        architectural_boundaries=dangling.architectural_boundaries,
        reliability_requirements=dangling.reliability_requirements,
        protected_regions=dangling.protected_regions,
        testing_anchors=dangling.testing_anchors,
        architectural_decisions=(
            ArchitecturalDecision(
                decision_id="DEC-001",
                context="c",
                question="q",
                selected_strategy="a",
                alternatives=("a", "b"),
                trade_offs=("t",),
                benefits=(),
                requirement_refs=("NO-SUCH-REQ",),
                invariant_refs=("NO-SUCH-INV",),
                architectural_scope=("NO-SUCH-MOD",),
                verification_refs=("NO-SUCH-ANCHOR",),
            ),
        ),
    )
    errors = validate_system_decision_constraints(dangling)
    assert "NO-SUCH-REQ" in " ".join(errors)
    assert "NO-SUCH-INV" in " ".join(errors)
    assert "NO-SUCH-MOD" in " ".join(errors)
    assert "NO-SUCH-ANCHOR" in " ".join(errors)
    dangling_index = IdentityIndex.derive(ISR(system=dangling))
    assert any("decision 'DEC-001'" in d for d in dangling_index.dangling_references)


def test_verification_refs_are_obligation_edges_not_verdicts():
    """The decision's verification_refs name anchors (obligation/provenance
    edges); the carrier has no verdict, result, or pass/fail field — a
    decision can never claim verification happened."""
    assert not {"verdict", "result", "evidence", "is_satisfied"} & frozenset(
        ArchitecturalDecision.__dataclass_fields__
    )


# -- protectability and projection -----------------------------------------------


def test_decisions_are_referenceable_by_protected_regions():
    """J protects decisions like any other gene: a region may name a
    decision id as its subject."""
    system = decision_system().system
    with_region = system.__class__(
        id=system.id,
        name=system.name,
        modules=system.modules,
        business_capabilities=system.business_capabilities,
        requirements=system.requirements,
        architectural_boundaries=system.architectural_boundaries,
        reliability_requirements=system.reliability_requirements,
        protected_regions=system.protected_regions
        + (
            ProtectedRegion(
                region_id="REG-002",
                subject_refs=("DEC-001",),
                protection_kind=ProtectionKind.IMMUTABLE,
            ),
        ),
        testing_anchors=system.testing_anchors,
        architectural_decisions=system.architectural_decisions,
    )
    assert validate_system_evolution_policy_constraints(with_region) == ()


def test_decision_projection_is_semantics_only():
    projection = project_architectural_decisions(decision_system())
    assert len(projection) == 1
    assert projection[0]["decision_id"] == "DEC-001"
    assert projection[0]["selected_strategy"]
    assert "rejected" in projection[0]
    assert projection[0]["requirement_refs"] == ["REQ-001"]
    assert not any(
        key in projection[0]
        for key in ("verdict", "result", "evidence", "is_satisfied")
    )


# -- technology neutrality --------------------------------------------------------


def test_decision_is_technology_neutral():
    decision = minimal_decision()
    lowered = canonicalize(decision).lower()
    assert not realization_terms_present(lowered)
    assert_decision_technology_agnostic(decision)
    assert_decision_technology_agnostic(decision_system().system.architectural_decisions[0])


def test_realization_terms_rejected_from_decisions():
    with pytest.raises(DecisionValidationError):
        assert_decision_technology_agnostic(
            ArchitecturalDecision(
                decision_id="d-tech",
                context="c",
                question="q",
                selected_strategy="store it in postgres",
                alternatives=("store it in postgres", "keep it in memory"),
                trade_offs=("t",),
                benefits=(),
            )
        )


# -- the authorship boundary ------------------------------------------------------


def test_certification_never_authors_decisions():
    """Structural: Phase 32's certification package contains no construction
    surface for ArchitecturalDecision — the ISR is the only author of
    decisions, certification is the consumer."""
    quality_dir = pathlib.Path(tiannara.__file__).parent / "application" / "quality"
    assert quality_dir.is_dir()
    offenders: list[str] = []
    for source in sorted(quality_dir.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = ast.unparse(node.func)
                if "ArchitecturalDecision" in fn:
                    offenders.append(f"{source.name}: constructs {fn}")
            elif isinstance(node, ast.ImportFrom):
                if "decision" in (node.module or ""):
                    offenders.append(
                        f"{source.name}: imports {node.module}"
                    )
                for alias in node.names:
                    if "Decision" in alias.name:
                        offenders.append(
                            f"{source.name}: imports {alias.name}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "decision" in alias.name.lower():
                        offenders.append(
                            f"{source.name}: imports {alias.name}"
                        )
    assert not offenders, offenders
