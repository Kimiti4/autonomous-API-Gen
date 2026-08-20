"""R2.10.32.6 — Failure Obligation Derivation: the controlled, provenance-
preserving derivation of failure obligations.

32.6 is the one place Phase 32 PRODUCES obligations, so the acceptance
surface is the provenance contract:

    * every derived obligation has an explicit ISR provenance chain
      (source_refs resolve to declared ISR facts) and a declared
      derivation rule (the rule exists in the declared set);
    * no implementation observation can become an obligation — the
      engine has no artifact-reading surface (structural);
    * an obligation with no source or no rule is rejected;
    * derivation is auditable end to end: "where did this requirement
      come from?" is answerable with an ISR fact and a rule;
    * provenance distinguishes derivations: the same fact through
      different declared rules yields distinct obligations;
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import ast
import inspect

import pytest

from constitutional_architecture.isr.model import (
    BusinessCapability,
    Deployment,
    DeploymentIntent,
    Entity,
    FailureMode,
    Module,
    NetworkingConfig,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    StorageConfig,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from tiannara.application.quality.failure_obligation_derivation import (
    DerivationValidationError,
    FailureDerivationRule,
    FailureObligation,
    FailureObligationDerivationEngine,
    FAILURE_DERIVATION_RULES,
    extract_isr_facts,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _isr() -> ISR:
    """A harness ISR declaring failure-bearing facts: a reliability
    requirement (D), external network exposure + persistent storage
    (G deployment), and a deployment intent (G)."""
    module = Module(
        id="MOD-A",
        name="MOD-A",
        entities=(Entity(id="e1", name="e1"),),
    )
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
    reliability = ReliabilityRequirement(
        requirement_id="REL-001",
        target_refs=("MOD-A",),
        failure_modes=(FailureMode.CASCADE_FAILURE,),
        dependency_constraints=("external settlement service",),
    )
    deployment = Deployment(
        id="DEP-001",
        name="Production",
        networking=NetworkingConfig(expose_publicly=True),
        storage=StorageConfig(persistent_storage_required=True),
    )
    intent = DeploymentIntent(
        deployment_id="DEP-INT-001",
        target_refs=("MOD-A",),
        rollout_strategy=RolloutStrategy.CANARY,
        rollout_constraints=("zero-downtime",),
        health_requirements=("healthy for one full cycle",),
        rollback_required=True,
        rollback_target_ref="MOD-A",
        rollback_invariants=("settlement ordering must be preserved",),
    )
    return ISR(
        system=System(
            id="fo-sys",
            name="FailureObligationSystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,),
            reliability_requirements=(reliability,),
            deployment=deployment,
            deployment_intents=(intent,),
        )
    )


class FailureObligationHarness:
    """The 32.6 machinery: the declared rule set, the harness ISR, and the
    derivation engine."""

    def __init__(self) -> None:
        self._recipe = CampaignReadinessHarness()

    def isr(self) -> ISR:
        return _isr()

    def derive(self, isr):
        return FailureObligationDerivationEngine().derive(isr)

    def isr_fact_exists(self, ref: str) -> bool:
        return ref in {f.fact_id for f in extract_isr_facts(self.isr())}

    def rule(self, rule_id: str):
        return next(
            r for r in FAILURE_DERIVATION_RULES if r.rule_id == rule_id
        )

    def matrix_summary(self):
        return self._recipe.matrix_summary()

    def recipe_isr_hash(self):
        return self._recipe.recipe_isr_hash()


@pytest.fixture(scope="module")
def deriv_harness() -> FailureObligationHarness:
    return FailureObligationHarness()


def test_every_derived_obligation_has_isr_provenance(deriv_harness):
    """The central invariant, first half: source_refs resolve to the ISR."""
    obligations = deriv_harness.derive(deriv_harness.isr())
    assert obligations
    for obligation in obligations:
        assert obligation.source_refs
        for ref in obligation.source_refs:
            assert deriv_harness.isr_fact_exists(ref)


def test_every_derived_obligation_has_a_declared_rule(deriv_harness):
    """The central invariant, second half: the rule exists in the declared
    set."""
    declared = {r.rule_id for r in FAILURE_DERIVATION_RULES}
    for obligation in deriv_harness.derive(deriv_harness.isr()):
        assert obligation.derivation_rule in declared


def test_implementation_observation_cannot_become_an_obligation(
    deriv_harness,
):
    """The forbidden path: there is no derivation from artifact observation.
    Structural — the engine has no artifact-reading surface."""
    tree = ast.parse(inspect.getsource(FailureObligationDerivationEngine))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "scan_artifact" not in fn
            assert "observe_implementation" not in fn
    params = list(inspect.signature(
        FailureObligationDerivationEngine.derive
    ).parameters)
    assert params == ["self", "isr"]


def test_obligation_without_source_or_rule_rejected():
    with pytest.raises(DerivationValidationError):
        FailureObligation(
            failure_id="f1",
            scenario="timeout",
            source_refs=(),
            derivation_rule="RULE-NETWORK-001",
            derived_invariant="i",
            expected_controls=(),
            verification_refs=(),
            evidence_refs=(),
        )
    with pytest.raises(DerivationValidationError):
        FailureObligation(
            failure_id="f1",
            scenario="timeout",
            source_refs=("DEP-014",),
            derivation_rule="",
            derived_invariant="i",
            expected_controls=(),
            verification_refs=(),
            evidence_refs=(),
        )


def test_derivation_is_auditable_end_to_end(deriv_harness):
    """A derived obligation can answer 'where did this requirement come
    from?' with an ISR fact and a rule."""
    obligation = deriv_harness.derive(deriv_harness.isr())[0]
    assert obligation.source_refs and obligation.derivation_rule
    rule = deriv_harness.rule(obligation.derivation_rule)
    assert obligation.scenario in rule.derived_failure_classes


def test_same_fact_different_rule_is_distinct(deriv_harness):
    """Provenance distinguishes derivations: same fact through different
    rules yields distinct, separately-auditable obligations."""
    extra_rules = (
        FailureDerivationRule(
            rule_id="RULE-EXTRA-A",
            source_fact_pattern="reliability_requirement",
            derived_failure_classes=("capacity_loss",),
            rationale="custom rule A for the provenance distinction test",
        ),
        FailureDerivationRule(
            rule_id="RULE-EXTRA-B",
            source_fact_pattern="reliability_requirement",
            derived_failure_classes=("recovery_failure",),
            rationale="custom rule B for the provenance distinction test",
        ),
    )
    obligations = FailureObligationDerivationEngine(
        extra_rules
    ).derive(deriv_harness.isr())
    assert len(obligations) == 2
    ids = {o.failure_id for o in obligations}
    assert len(ids) == len(obligations)
    assert {o.derivation_rule for o in obligations} == {
        "RULE-EXTRA-A",
        "RULE-EXTRA-B",
    }


def test_matrix_and_recipe_identity_unchanged(deriv_harness):
    assert deriv_harness.matrix_summary() == (12, 18, 0, 0)
    assert deriv_harness.recipe_isr_hash() == RECIPE_HASH