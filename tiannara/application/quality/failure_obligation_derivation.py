"""R2.10.32.6 — Failure Obligation Derivation: obligations DERIVED from
declared ISR facts via DECLARED derivation rules.

32.1–32.4 established obligation authorship (ISR-declared) and tracing
(without authorship); 32.5 established emergent-property analysis
(measured, never invented). 32.6 is the one place Phase 32 PRODUCES
obligations, so the boundary that keeps it honest is exact:

    Deriving an obligation from a declared ISR fact via a declared rule
    is NOT inventing an obligation.

The obligation still originates in the ISR — in the FACT ("an external
network dependency exists") — and the derivation is a controlled,
auditable transformation of that fact into the failure classes it
implies. What remains forbidden is the other path:

    implementation observation -> obligation

("the code contains a network call, therefore there must be a
network-partition requirement"). That path is obligation-contamination
regardless of how reasonable the inference seems, because its origin is
the artifact rather than the ISR. The engine has NO artifact-reading
surface (structurally asserted by the acceptance suite): the artifact is
what obligations are later traced INTO (by 32.4's epistemic machinery),
never what they are derived FROM.

The central invariant:

    Every derived failure obligation has an explicit ISR provenance chain
    and a declared derivation rule; no implementation observation may
    become a failure obligation without an explicit, authorized
    derivation rule whose source ultimately resolves to the ISR.
"""
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "DerivationValidationError",
    "FailureDerivationRule",
    "FailureObligation",
    "FailureObligationDerivationEngine",
    "FAILURE_DERIVATION_RULES",
    "ISRFact",
    "derive_id",
    "derive_invariant",
    "extract_isr_facts",
]


class DerivationValidationError(ValueError):
    """A derived obligation violates the provenance contract."""


@dataclass(frozen=True)
class FailureDerivationRule:
    """A DECLARED derivation rule: maps an ISR fact pattern to the failure
    classes it implies.

    Rules are declared, never invented per-observation — a fact can only
    produce obligations through a rule that already exists. If a new
    failure class is needed, that is a new DECLARED rule, not an ad-hoc
    inference.
    """

    rule_id: str
    source_fact_pattern: str  # the ISR fact pattern this rule applies to
    derived_failure_classes: tuple[str, ...]  # the failure classes it implies
    rationale: str


FAILURE_DERIVATION_RULES: tuple[FailureDerivationRule, ...] = (
    FailureDerivationRule(
        rule_id="RULE-NETWORK-001",
        source_fact_pattern="external_network_dependency",
        derived_failure_classes=(
            "timeout",
            "unavailable_dependency",
            "partial_response",
            "duplicate_operation",
        ),
        rationale="an external network dependency can fail by timing out, "
        "becoming unavailable, responding partially, or duplicating an "
        "operation",
    ),
    FailureDerivationRule(
        rule_id="RULE-PERSISTENCE-001",
        source_fact_pattern="persistent_data_store",
        derived_failure_classes=(
            "write_failure",
            "unavailable_store",
            "corrupted_read",
        ),
        rationale="a persistent data store can fail writes, become "
        "unavailable, or return corrupted reads",
    ),
    FailureDerivationRule(
        rule_id="RULE-RELIABILITY-001",
        source_fact_pattern="reliability_requirement",
        derived_failure_classes=(
            "capacity_degradation",
            "availability_loss",
            "recovery_required",
        ),
        rationale="a reliability requirement declares that failures must "
        "survive; the general implications are capacity degradation, "
        "availability loss, and the need for recovery",
    ),
    FailureDerivationRule(
        rule_id="RULE-DEPLOYMENT-001",
        source_fact_pattern="deployment_constraint",
        derived_failure_classes=(
            "rollout_failure",
            "rollback_invoked",
        ),
        rationale="a deployment intent's constraints imply the deployment "
        "may fail mid-rollout and must be able to roll back",
    ),
)


@dataclass(frozen=True)
class ISRFact:
    """A DECLARED ISR fact — the only legitimate origin of a derived
    failure obligation. Read from the ISR's obligation-bearing carriers
    (D reliability requirements, G deployment constraints and dependency
    declarations); never from the implementation artifact."""

    fact_id: str
    kind: str  # matches a rule's source_fact_pattern
    carrier: str  # the ISR carrier that declared this fact


def extract_isr_facts(isr) -> tuple[ISRFact, ...]:
    """Read the DECLARED facts from the ISR: D reliability requirements,
    G deployment constraints, and declared dependency declarations
    (external network exposure, persistent storage). The derivation's
    sources are the ISR's existing obligation-bearing carriers."""
    facts: list[ISRFact] = []
    system = isr.system
    for req in system.reliability_requirements:
        facts.append(
            ISRFact(
                fact_id=req.requirement_id,
                kind="reliability_requirement",
                carrier="reliability_requirement",
            )
        )
    if system.deployment is not None:
        if system.deployment.networking.expose_publicly:
            facts.append(
                ISRFact(
                    fact_id=f"{system.deployment.id}:external-network",
                    kind="external_network_dependency",
                    carrier="deployment",
                )
            )
        if system.deployment.storage.persistent_storage_required:
            facts.append(
                ISRFact(
                    fact_id=f"{system.deployment.id}:persistent-storage",
                    kind="persistent_data_store",
                    carrier="deployment",
                )
            )
    for intent in system.deployment_intents:
        facts.append(
            ISRFact(
                fact_id=intent.deployment_id,
                kind="deployment_constraint",
                carrier="deployment_intent",
            )
        )
    return tuple(facts)


def derive_id(fact_id: str, rule_id: str, failure_class: str) -> str:
    """Deterministic obligation identity: (fact_id, rule_id, failure_class)
    yields a stable identity, so re-derivation is idempotent and
    obligations are chain-addressable."""
    return f"{fact_id}::{rule_id}::{failure_class}"


def derive_invariant(failure_class: str) -> str:
    """The derived invariant: what must hold despite the failure class."""
    return (
        f"the system must tolerate {failure_class} without violating its "
        "declared reliability objectives"
    )


@dataclass(frozen=True)
class FailureObligation:
    """A failure obligation DERIVED from a declared ISR fact via a declared
    rule.

    The obligation originates in the ISR — the source fact — and the
    derivation is explicit and auditable through `source_refs` and
    `derivation_rule`. This is what separates an ISR-derived obligation
    from a scanner-generated observation: the former can answer "where
    did this requirement come from?" with an ISR fact and a rule; the
    latter cannot.
    """

    failure_id: str
    scenario: str  # the derived failure class
    source_refs: tuple[str, ...]  # ISR facts this is derived from
    derivation_rule: str  # the declared rule applied
    derived_invariant: str  # the invariant that must hold
    expected_controls: tuple[str, ...]  # controls expected to handle the failure
    verification_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise DerivationValidationError(
                "a derived obligation with no ISR source is an invention, "
                "not a derivation"
            )
        if not self.derivation_rule:
            raise DerivationValidationError(
                "a derived obligation with no declared rule is unauditable"
            )


class FailureObligationDerivationEngine:
    """32.6 — Failure Obligation Derivation.

    Derives failure obligations from DECLARED ISR FACTS via DECLARED
    DERIVATION RULES. Reads the ISR's reliability/deployment/dependency
    facts, matches them against the declared rules, and produces
    obligations carrying their full provenance. NEVER reads the
    implementation artifact to invent obligations — the artifact is what
    obligations are later traced INTO (by 32.4's machinery), never what
    they are derived FROM.

    No severity authorship: a failure obligation's criticality comes from
    its source fact and its rule, not from this engine's judgment.
    """

    def __init__(
        self,
        rules: tuple[FailureDerivationRule, ...] = FAILURE_DERIVATION_RULES,
    ) -> None:
        self._rules = rules

    def derive(self, isr) -> tuple[FailureObligation, ...]:
        """Derive every obligation the declared rules produce from the
        declared ISR facts. Idempotent: the same ISR yields the same
        obligations."""
        obligations: list[FailureObligation] = []
        for fact in extract_isr_facts(isr):
            for rule in self._rules:
                if rule.source_fact_pattern == fact.kind:
                    for failure_class in rule.derived_failure_classes:
                        obligations.append(
                            FailureObligation(
                                failure_id=derive_id(
                                    fact.fact_id, rule.rule_id, failure_class
                                ),
                                scenario=failure_class,
                                source_refs=(fact.fact_id,),
                                derivation_rule=rule.rule_id,
                                derived_invariant=derive_invariant(failure_class),
                                expected_controls=(),
                                verification_refs=(),
                                evidence_refs=(),
                            )
                        )
        return tuple(obligations)