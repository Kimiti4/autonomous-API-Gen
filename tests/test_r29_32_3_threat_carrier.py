"""R2.10.32.3 — the SecurityThreat ISR carrier: the security-obligation record.

The carrier makes security threats first-class ISR objects: the security
intent the architecture is AUTHORSED against — scenarioed, severity-declared,
invariant-bound, control-referenced, and verification-linked — addressable by
identity, and structurally incapable of authoring anything. The acceptance
surface:

    * the carrier carries every link R2.10.32.4's traceability chain needs
      (requirement_refs, invariant_statement, architectural_control_refs,
      implementation_obligation_refs, verification_refs);
    * a threat without an invariant is undefined — rejected;
    * a threat tied to neither a requirement nor an architectural control is
      unanchored — rejected;
    * the carrier is empty identity-neutral (R2.10.2 Option A): the frozen
      recipe ISR and the capability matrix are byte-identical before and
      after the carrier lands;
    * a populated threat participates in the identity index like any other
      gene — addressed by ("threat", threat_id) and identity-affecting;
    * technology neutrality: no security/messaging technology (JWT, OAuth,
      mTLS, Kafka, ...) may leak into a threat — those are compiler
      backends per the constitution's plugin-first principle;
    * the authorship boundary is structural: Phase 32 (certification) is the
      CONSUMER of threats, never their author — the ISR is the only author.
      No scanning, no inference: an application "having authentication"
      does NOT imply its threats.
"""
import ast
import pathlib

import pytest

import tiannara
from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    ArchitecturalDecision,
    BusinessCapability,
    Entity,
    Module,
    Requirement,
    TestingAnchor as AnchorDeclaration,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.threat import (
    SecurityThreat,
    ThreatRealizationError,
    ThreatSeverity,
    ThreatValidationError,
    threat_terms_present,
    validate_system_threat_constraints,
    validate_threat_neutrality,
)
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    canonicalize,
    semantic_content_hash,
)
from tiannara.application.evolution.identity_index import IdentityIndex

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def minimal_threat() -> SecurityThreat:
    """The smallest constitutionally valid threat: an invariant, and one
    anchor edge (a requirement). Deliberately free of any security
    technology vocabulary."""
    return SecurityThreat(
        threat_id="t1",
        scenario="unauthorized access to cross-context data",
        severity=ThreatSeverity.CRITICAL,
        requirement_refs=("REQ-001",),
        invariant_statement="cross-context data must never be readable "
        "without authorization",
        architectural_control_refs=(),
        implementation_obligation_refs=(),
        verification_refs=(),
    )


def threat_with_scenario(scenario: str) -> SecurityThreat:
    return SecurityThreat(
        threat_id="t-tech",
        scenario=scenario,
        severity=ThreatSeverity.HIGH,
        requirement_refs=("REQ-001",),
        invariant_statement="authorization must hold across contexts",
        architectural_control_refs=(),
        implementation_obligation_refs=(),
        verification_refs=(),
    )


def empty_system() -> ISR:
    """An ISR with no threats (and no other semantic carriers)."""
    return ISR(
        system=System(
            id="threat-sys",
            name="ThreatSystem",
            modules=(
                Module(
                    id="MOD-A",
                    name="MOD-A",
                    entities=(Entity(id="e1", name="e1"),),
                ),
            ),
        )
    )


def populate_threat(threat: SecurityThreat) -> ISR:
    """An ISR carrying one threat whose reference edges resolve: the
    requirement from F (REQ-001), the boundary from E (BND-001), the
    decision obligation carrier (DEC-001), the anchor from H
    (ANCHOR-001)."""
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
        requirement_refs=("REQ-001",),
        invariant_refs=("BND-001",),
        architectural_scope=("MOD-A",),
        verification_refs=("ANCHOR-001",),
    )
    anchored = SecurityThreat(
        threat_id=threat.threat_id,
        scenario=threat.scenario,
        severity=threat.severity,
        requirement_refs=threat.requirement_refs,
        invariant_statement=threat.invariant_statement,
        architectural_control_refs=("BND-001",),
        implementation_obligation_refs=("DEC-001",),
        verification_refs=("ANCHOR-001",),
    )
    return ISR(
        system=System(
            id="threat-sys",
            name="ThreatSystem",
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
            testing_anchors=(anchor,),
            architectural_decisions=(decision,),
            security_threats=(anchored,),
        )
    )


@pytest.fixture(scope="module")
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


# -- the carrier carries the full chain -------------------------------------------


def test_threat_carrier_fields_support_the_full_chain():
    """The carrier carries every link 32.4's traceability chain needs."""
    fields = {f.name for f in dataclasses_fields()}
    for link in ("requirement_refs", "invariant_statement",
                 "architectural_control_refs", "implementation_obligation_refs",
                 "verification_refs"):
        assert link in fields
    threat = minimal_threat()
    assert threat.threat_id
    assert threat.scenario
    assert threat.severity in ThreatSeverity
    assert threat.invariant_statement


def dataclasses_fields():
    import dataclasses
    return dataclasses.fields(SecurityThreat)


def test_threat_without_invariant_rejected():
    with pytest.raises(ThreatValidationError):
        SecurityThreat(threat_id="t1", scenario="unauthorized_access",
                       severity=ThreatSeverity.CRITICAL,
                       requirement_refs=("r1",), invariant_statement="",
                       architectural_control_refs=(), implementation_obligation_refs=(),
                       verification_refs=())


def test_unanchored_threat_rejected():
    with pytest.raises(ThreatValidationError):
        SecurityThreat(threat_id="t1", scenario="s", severity=ThreatSeverity.HIGH,
                       requirement_refs=(), invariant_statement="inv",
                       architectural_control_refs=(), implementation_obligation_refs=(),
                       verification_refs=())


# -- identity neutrality (Option A) ---------------------------------------------


def test_threat_carrier_is_identity_neutral_when_empty(campaign_harness):
    """An empty threat carrier is byte-identical to no carrier at all:
    the frozen recipe ISR hashes exactly as before the field existed."""
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH
    canonical = canonical_form(empty_system().system)
    assert "security_threats" not in canonical


def test_populated_threat_participates_in_identity():
    isr_with = populate_threat(minimal_threat())
    populated_index = IdentityIndex.derive(isr_with)
    assert ("threat", "t1") in populated_index.genes
    assert populated_index.genes[("threat", "t1")].threat_id == "t1"
    assert (
        populated_index.path_identities["system.security_threats[0]"]
        == "t1"
    )
    assert populated_index.dangling_references == ()
    assert semantic_content_hash(isr_with) != semantic_content_hash(
        empty_system()
    )


def test_threat_reference_edges_resolve():
    """The four reference edges resolve against the existing carriers:
    requirement_refs -> F's requirements, architectural_control_refs -> E's
    boundaries, implementation_obligation_refs -> the decision/obligation
    carriers, verification_refs -> H's anchors. A dangling edge is
    rejected."""
    assert validate_system_threat_constraints(
        populate_threat(minimal_threat()).system
    ) == ()
    dangling = populate_threat(minimal_threat()).system
    dangling = dangling.__class__(
        id=dangling.id,
        name=dangling.name,
        modules=dangling.modules,
        business_capabilities=dangling.business_capabilities,
        requirements=dangling.requirements,
        architectural_boundaries=dangling.architectural_boundaries,
        testing_anchors=dangling.testing_anchors,
        architectural_decisions=dangling.architectural_decisions,
        security_threats=(
            SecurityThreat(
                threat_id="t-d",
                scenario="s",
                severity=ThreatSeverity.LOW,
                requirement_refs=("NO-SUCH-REQ",),
                invariant_statement="inv",
                architectural_control_refs=("NO-SUCH-BND",),
                implementation_obligation_refs=("NO-SUCH-DEC",),
                verification_refs=("NO-SUCH-ANCHOR",),
            ),
        ),
    )
    errors = validate_system_threat_constraints(dangling)
    assert "NO-SUCH-REQ" in " ".join(errors)
    assert "NO-SUCH-BND" in " ".join(errors)
    assert "NO-SUCH-DEC" in " ".join(errors)
    assert "NO-SUCH-ANCHOR" in " ".join(errors)
    dangling_index = IdentityIndex.derive(ISR(system=dangling))
    assert any("threat 't-d'" in d for d in dangling_index.dangling_references)


# -- technology neutrality ---------------------------------------------------------


def test_threat_is_technology_neutral():
    """Scenarios reference security concerns, never security technologies."""
    with pytest.raises(ThreatRealizationError):
        validate_threat_neutrality(threat_with_scenario("JWT manipulation"))
    validate_threat_neutrality(threat_with_scenario("authentication bypass"))
    lowered = canonicalize(minimal_threat())
    assert not threat_terms_present(lowered)


def test_security_technologies_rejected_from_threats():
    """JWT/OAuth/mTLS/Kafka are compiler backends per the constitution's
    plugin-first principle — never reasoning-model content."""
    for scenario in ("JWT manipulation", "oauth token theft", "mTLS bypass",
                     "kafka replay"):
        with pytest.raises(ThreatRealizationError):
            validate_threat_neutrality(threat_with_scenario(scenario))


# -- the authorship boundary --------------------------------------------------------


def test_quality_package_cannot_construct_threats():
    """Structural: Phase 32's certification package contains no construction
    surface for SecurityThreat — the ISR is the only author of threats,
    certification is the consumer. No scanning, no inference. The import
    ban targets the threat CARRIER (``isr.semantics.threat``) and its
    constructor name only: R2.10.32.4 consumes the DECLARED severity type
    through the model facade (``isr.model``) — carrying a declaration is
    not authorship."""
    quality_dir = pathlib.Path(tiannara.__file__).parent / "application" / "quality"
    assert quality_dir.is_dir()
    offenders: list[str] = []
    for source in sorted(quality_dir.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = ast.unparse(node.func)
                if "SecurityThreat" in fn:
                    offenders.append(f"{source.name}: constructs {fn}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    "semantics.threat" in module
                    or module == "threat"
                    or module.endswith(".threat")
                ):
                    offenders.append(
                        f"{source.name}: imports {module}"
                    )
                for alias in node.names:
                    if alias.name == "SecurityThreat":
                        offenders.append(
                            f"{source.name}: imports {alias.name}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        "threat" in alias.name.lower()
                        and "semantics" in alias.name.lower()
                    ):
                        offenders.append(
                            f"{source.name}: imports {alias.name}"
                        )
    assert not offenders, offenders


# -- identity stability ------------------------------------------------------------


def test_matrix_and_recipe_identity_unchanged(campaign_harness):
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH
    assert campaign_harness.matrix_summary() == (12, 18, 0, 0)