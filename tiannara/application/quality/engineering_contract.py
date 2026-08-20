"""R2.10.32 — the engineering certification contract (gates, not averages).

The contract is the declared, frozen surface the certification harness
enforces. It carries the eight certification dimensions, the three-verdict
space (never a score), the per-dimension gates with their calibration
basis, and the declared assumptions every certificate inherits.

Design commitments (R2.10.32, user-specified and source-locked):

  * GATES NOT AVERAGES — a dimension either meets its gate or it does not;
    there is no aggregate score anywhere in the contract. A single critical
    violation is structurally dispositive for the whole certificate.
  * ISR_CONFORMANCE IS DISPOSITIVE — it is the only gate marked
    ``is_dispositive``; a certificate whose mandatory obligations are not
    enforced is NOT_CERTIFIED before any gradable dimension is evaluated.
  * CALIBRATION IS DECLARED — every gate carries its rationale and every
    contract its declared assumptions, so the threshold basis is part of
    the certificate's evidence rather than a hidden constant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EngineeringDimension(str, Enum):
    """The eight certification dimensions. ISR_CONFORMANCE is dispositive;
    the other seven are gradable and gated."""

    __test__ = False

    ISR_CONFORMANCE = "ISR_CONFORMANCE"
    IMPLEMENTATION = "IMPLEMENTATION"
    ARCHITECTURE = "ARCHITECTURE"
    DESIGN = "DESIGN"
    FAILURE_ENGINEERING = "FAILURE_ENGINEERING"
    SECURITY = "SECURITY"
    EVOLVABILITY = "EVOLVABILITY"
    OPERATIONS = "OPERATIONS"


# The seven gradable dimensions, in certification order.
GRADABLE_DIMENSIONS: tuple[EngineeringDimension, ...] = (
    EngineeringDimension.IMPLEMENTATION,
    EngineeringDimension.ARCHITECTURE,
    EngineeringDimension.DESIGN,
    EngineeringDimension.FAILURE_ENGINEERING,
    EngineeringDimension.SECURITY,
    EngineeringDimension.EVOLVABILITY,
    EngineeringDimension.OPERATIONS,
)


class EngineeringVerdict(str, Enum):
    """The three-verdict space. Never a score: the verdict is rendered from
    the gates, and any critical violation is structurally dispositive."""

    __test__ = False

    CERTIFIED = "CERTIFIED"
    QUALIFIED_PARTIAL = "QUALIFIED_PARTIAL"
    NOT_CERTIFIED = "NOT_CERTIFIED"


class FindingSeverity(str, Enum):
    """Finding severities. CRITICAL is structurally dispositive for the
    certificate; MAJOR fails its dimension's gate; MINOR and ADVISORY are
    carried and named but do not fail a gate."""

    __test__ = False

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    ADVISORY = "ADVISORY"


@dataclass(frozen=True)
class DimensionGate:
    """One declared gate over one dimension.

    ``threshold`` is the human-readable, machine-checkable predicate the
    harness enforces (the gate's calibration). ``is_dispositive`` is true
    only for ISR_CONFORMANCE — conformance failure ends certification
    before any gradable dimension runs.
    """

    dimension: EngineeringDimension
    threshold: str
    is_dispositive: bool
    rationale: str


@dataclass(frozen=True)
class EngineeringQualityContract:
    """The declared, frozen certification contract.

    ``declared_assumptions`` records the calibration basis (severity
    rules, vacuity policy, abstraction threshold) so every certificate
    inherits it as evidence — the gate calibration is never a hidden
    constant.
    """

    contract_id: str
    gates: tuple[DimensionGate, ...]
    declared_assumptions: tuple[str, ...]

    def gate_for(self, dimension: EngineeringDimension) -> DimensionGate:
        for gate in self.gates:
            if gate.dimension == dimension:
                return gate
        raise KeyError(f"no declared gate for {dimension.value}")

    def dispositive_gate(self) -> DimensionGate:
        for gate in self.gates:
            if gate.is_dispositive:
                return gate
        raise KeyError("the contract declares no dispositive gate")


def default_engineering_contract() -> EngineeringQualityContract:
    """The R2.10.32 baseline contract.

    Every gate's calibration basis is stated here, in the contract, so the
    certificate's verdicts are auditable against the declared threshold.
    """
    return EngineeringQualityContract(
        contract_id="R2.10.32-contract-v1",
        gates=(
            DimensionGate(
                dimension=EngineeringDimension.ISR_CONFORMANCE,
                threshold=(
                    "every mandatory ISR obligation is enforced by the "
                    "artifact: declared supported AND content-bound to the "
                    "certified ISR; partial or unsupported declarations "
                    "are violations for mandatory obligations"
                ),
                is_dispositive=True,
                rationale=(
                    "a certificate of an artifact that does not enforce "
                    "its own ISR's mandatory obligations is void — "
                    "conformance is checked first and ends certification "
                    "before any gradable dimension runs"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.IMPLEMENTATION,
                threshold=(
                    "no CRITICAL or MAJOR findings; stub-only surfaces and "
                    "unwired generated surfaces fail this gate"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: a generated implementation whose surface "
                    "is never wired (router registries left as stubs) or "
                    "whose units are mostly empty bodies cannot be "
                    "certified as implemented"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.ARCHITECTURE,
                threshold=(
                    "no CRITICAL or MAJOR findings; circular module "
                    "dependencies are CRITICAL, layer violations are MAJOR"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: cyclic module graphs are structurally "
                    "uncertifiable; directional layer violations fail the "
                    "gate; isolated/decoration-only layers are named MINOR"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.DESIGN,
                threshold=(
                    "no CRITICAL or MAJOR findings; dead-code ratio and "
                    "stub ratio above calibration fail this gate"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: dead-code ratio >= 0.30 or stub ratio "
                    ">= 0.50 is MAJOR (a decorative surface); lower "
                    "amounts are named MINOR"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.FAILURE_ENGINEERING,
                threshold=(
                    "no CRITICAL or MAJOR findings; every mandatory "
                    "failure scenario is handled (CRITICAL when not), and "
                    "an ISR declaring no failure scenarios fails this gate"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: scenarios come from the ISR's reliability "
                    "recovery objectives, migration rollback invariants, "
                    "and deployment rollback invariants; an unhandled "
                    "mandatory scenario is silent-loss risk (CRITICAL); "
                    "absence of declared scenarios is MAJOR — certification "
                    "demands declared failure semantics, never vacuous pass"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.SECURITY,
                threshold=(
                    "no CRITICAL or MAJOR findings; hardcoded credentials "
                    "and wildcard CORS with credentialed auth are CRITICAL"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: credential literals in source are "
                    "CRITICAL; allow_origins=['*'] combined with "
                    "allow_credentials and an OAuth bearer surface is "
                    "CRITICAL (credential exposure cross-origin); wildcard "
                    "CORS without credentialed auth is MAJOR; container "
                    "running as root is MINOR"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.EVOLVABILITY,
                threshold=(
                    "evolvable under controlled mutation: evolution cost "
                    "<= 0.50 AND complexity within calibration AND "
                    "abstraction justified (supported/expressed >= 0.50)"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: the complexity gate CONJOINS the cost "
                    "gate so an over-abstracted surface cannot game "
                    "evolvability with a cheap simulated mutation — an "
                    "abstraction that expresses semantics the artifact "
                    "does not realize is MAJOR even when evolution cost "
                    "is low"
                ),
            ),
            DimensionGate(
                dimension=EngineeringDimension.OPERATIONS,
                threshold=(
                    "no CRITICAL or MAJOR findings; an ISR declaring no "
                    "deployment semantics, or whose declared deployment "
                    "semantics are not realized, fails this gate"
                ),
                is_dispositive=False,
                rationale=(
                    "calibration: certification demands a declared "
                    "rollout/rollback posture (MAJOR when absent or "
                    "declared-but-unrealized); health endpoint, container "
                    "image, and structured logging are named when present "
                    "and their absence noted MINOR"
                ),
            ),
        ),
        declared_assumptions=(
            "gate calibration: every threshold is declared in this "
            "contract's gates and inherited by every certificate as "
            "evidence — there are no hidden constants",
            "vacuity policy: evidence-limited dimensions (no executable "
            "surface carried by the artifact) pass their gates with an "
            "ADVISORY naming the absence — vacuity is named, never blurred",
            "severity calibration: CRITICAL = unenforced mandatory "
            "obligation / hardcoded credential / credentialed wildcard "
            "CORS / unhandled mandatory failure scenario / circular module "
            "dependency; MAJOR = unwired surface, stub-majority surface, "
            "abstraction not justified, absent or unrealized deployment "
            "semantics, absent failure scenarios; MINOR and ADVISORY are "
            "carried and named",
            "abstraction calibration: abstraction_justified = "
            "supported/expressed semantics >= 0.50; the complexity gate "
            "conjoins the evolution-cost gate so over-abstraction cannot "
            "game evolvability",
            "certification is measurement-only: the certifier never "
            "mutates the ISR or the artifact; the evolutionary quality "
            "loop mutates the ISR through the declared mutation operators "
            "and re-certifies — remediation is evolution, never editing "
            "the measurement",
        ),
    )