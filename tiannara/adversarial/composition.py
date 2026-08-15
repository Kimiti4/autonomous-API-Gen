"""Adversarial composition analysis (R2.8.11).

Single-attack suites prove each defense works in isolation. Composition tests
prove defenses do not INTERACT to create bypass paths.

The central hazard: a meta-attack disables the defense layer responsible for
catching a sibling attack, letting the sibling slip through even though every
individual defense "passes."

Constitutional basis:
  * "Security by design", "Fault tolerance" -- defense-in-depth / redundancy.
  * "Modularity" -- independent defense layers with explicit responsibilities.
  * "Verification First" -- adversarial testing, including composition.
  * "Capability must never outpace verification."
  * "Uncertainty should never be hidden" -- expose that hardening without a
    root of trust is still bypassable.
  * Constitutional root of trust -- "No constitutional rule is modified by the
    subsystem it governs" (PROTECTED_CORE).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Set, Tuple


class AttackPrimitive(str, Enum):
    DELETE_TEST = "delete_test"
    RENAME_TEST = "rename_test"
    SKIP_TEST = "skip_test"
    WEAKEN_ASSERTION = "weaken_assertion"
    REMOVE_ASSERTION = "remove_assertion"
    ALTER_FIXTURE = "alter_fixture"
    AGGREGATE_MIMIC = "aggregate_mimic"
    UNAUTHORIZED_GUTTING = "unauthorized_gutting"
    MASK_SPECIAL_CASE = "mask_special_case"
    MASK_EARLY_RETURN = "mask_early_return"
    MASK_FABRICATED = "mask_fabricated"
    ARCH_AUTH_REMOVAL = "arch_auth_removal"
    ARCH_BOUNDARY_REMOVAL = "arch_boundary_removal"
    ARCH_PERSISTENCE_DEGRADATION = "arch_persistence_degradation"
    ATTACK_GATE_CONFIG = "attack_gate_config"
    TAMPER_ANCHOR = "tamper_anchor"


class DefenseLayer(str, Enum):
    REGRESSION = "regression"
    IDENTITY = "identity"
    HOLDOUT = "holdout"
    ARCHITECTURAL = "architectural"
    EVIDENCE_INTEGRITY = "evidence_integrity"
    ATTEMPTATION = "attestation"
    VISIBILITY = "visibility"
    PROTECTED_CORE = "protected_core"


@dataclass(frozen=True)
class CompositeAttack:
    """A composed adversarial mutation: an ordered sequence of primitives
    applied to a single candidate.

    Information-hiding invariant: the composition structure lives only in the
    harness metadata. It never flows into CandidateEvidence and never reaches
    the gate.
    """
    composition_id: str
    primitives: Tuple[AttackPrimitive, ...]
    expected_defeated: bool
    expected_catching_layers: FrozenSet[str]
    holdout_intact: bool = True
    rationale: str = ""


@dataclass(frozen=True)
class ComposedMutationSpec:
    __test__ = False
    composition_id: str
    primitives: Tuple[AttackPrimitive, ...]
    expected_defeated: bool
    expected_catching_layers: FrozenSet[str]
    holdout_intact: bool = True
    rationale: str = ""


@dataclass(frozen=True)
class DefenseMatrix:
    """catches[p] = layers that catch primitive p (individually).
    disables[p] = layers that primitive p can disable in a composition."""
    catches: Dict[AttackPrimitive, FrozenSet[DefenseLayer]]
    disables: Dict[AttackPrimitive, FrozenSet[DefenseLayer]]

    def disabled_layers(self, composition: Tuple[AttackPrimitive, ...],
                        exclude: AttackPrimitive) -> Set[DefenseLayer]:
        out: Set[DefenseLayer] = set()
        for q in composition:
            if q != exclude:
                out |= set(self.disables.get(q, frozenset()))
        return out

    def surviving_catchers(self, p: AttackPrimitive,
                           composition: Tuple[AttackPrimitive, ...]) -> Set[DefenseLayer]:
        return set(self.catches.get(p, frozenset())) - self.disabled_layers(composition, exclude=p)


@dataclass(frozen=True)
class CompositionVerdict:
    composition_id: str
    defended: bool
    bypassed_primitives: Tuple[AttackPrimitive, ...]
    catches: Dict[str, Tuple[str, ...]]


def analyze_composition(attack, matrix: DefenseMatrix) -> CompositionVerdict:
    """A composite is defended iff EVERY primitive retains >=1 surviving catcher."""
    bypassed = []
    catches: Dict[str, Tuple[str, ...]] = {}

    for p in attack.primitives:
        survivors = matrix.surviving_catchers(p, attack.primitives)
        if not survivors:
            bypassed.append(p)
        else:
            catches[p.value] = tuple(sorted(s.value for s in survivors))

    return CompositionVerdict(
        composition_id=attack.composition_id,
        defended=not bypassed,
        bypassed_primitives=tuple(sorted(bypassed, key=lambda x: x.value)),
        catches=catches,
    )


P = AttackPrimitive
D = DefenseLayer


def vulnerable_matrix() -> DefenseMatrix:
    """Single-layer catches. Demonstrates that composition can bypass a
    defense that looks fine in isolation."""
    return DefenseMatrix(
        catches={
            P.DELETE_TEST: frozenset({D.IDENTITY, D.REGRESSION}),
            P.WEAKEN_ASSERTION: frozenset({D.ATTEMPTATION, D.REGRESSION}),
            P.MASK_SPECIAL_CASE: frozenset({D.HOLDOUT}),
            P.MASK_EARLY_RETURN: frozenset({D.HOLDOUT, D.REGRESSION}),
            P.MASK_FABRICATED: frozenset({D.HOLDOUT, D.REGRESSION}),
            P.ARCH_AUTH_REMOVAL: frozenset({D.ARCHITECTURAL}),
            P.ARCH_BOUNDARY_REMOVAL: frozenset({D.ARCHITECTURAL}),
            P.ARCH_PERSISTENCE_DEGRADATION: frozenset({D.ARCHITECTURAL}),
            P.AGGREGATE_MIMIC: frozenset({D.ATTEMPTATION}),
            P.ATTACK_GATE_CONFIG: frozenset({D.EVIDENCE_INTEGRITY}),
            P.TAMPER_ANCHOR: frozenset({D.EVIDENCE_INTEGRITY}),
        },
        disables={
            P.ATTACK_GATE_CONFIG: frozenset({D.ARCHITECTURAL}),
            P.TAMPER_ANCHOR: frozenset({D.EVIDENCE_INTEGRITY}),
        },
    )


def hardened_matrix() -> DefenseMatrix:
    """Two-layer redundancy for architectural/measurement attacks, backed by
    the R2.8.9 evidence chain. Closes the single-layer bypass, but is still
    beatable if an attacker disables BOTH redundant layers."""
    return DefenseMatrix(
        catches={
            P.DELETE_TEST: frozenset({D.IDENTITY, D.REGRESSION}),
            P.WEAKEN_ASSERTION: frozenset({D.ATTEMPTATION, D.REGRESSION}),
            P.MASK_SPECIAL_CASE: frozenset({D.HOLDOUT, D.EVIDENCE_INTEGRITY}),
            P.MASK_EARLY_RETURN: frozenset({D.HOLDOUT, D.REGRESSION, D.EVIDENCE_INTEGRITY}),
            P.MASK_FABRICATED: frozenset({D.HOLDOUT, D.REGRESSION, D.EVIDENCE_INTEGRITY}),
            P.ARCH_AUTH_REMOVAL: frozenset({D.ARCHITECTURAL, D.EVIDENCE_INTEGRITY}),
            P.ARCH_BOUNDARY_REMOVAL: frozenset({D.ARCHITECTURAL, D.EVIDENCE_INTEGRITY}),
            P.ARCH_PERSISTENCE_DEGRADATION: frozenset({D.ARCHITECTURAL, D.EVIDENCE_INTEGRITY}),
            P.AGGREGATE_MIMIC: frozenset({D.ATTEMPTATION, D.EVIDENCE_INTEGRITY}),
            P.ATTACK_GATE_CONFIG: frozenset({D.EVIDENCE_INTEGRITY}),
            P.TAMPER_ANCHOR: frozenset({D.EVIDENCE_INTEGRITY}),
        },
        disables={
            P.ATTACK_GATE_CONFIG: frozenset({D.ARCHITECTURAL}),
            P.TAMPER_ANCHOR: frozenset({D.EVIDENCE_INTEGRITY}),
        },
    )


def rooted_matrix() -> DefenseMatrix:
    """Adds an immutable protected-core backstop that NO primitive can disable.
    This is the constitutional root of trust."""
    h = hardened_matrix()
    catches = dict(h.catches)
    protected = (P.ARCH_AUTH_REMOVAL, P.ARCH_BOUNDARY_REMOVAL,
                 P.ARCH_PERSISTENCE_DEGRADATION, P.ATTACK_GATE_CONFIG,
                 P.TAMPER_ANCHOR, P.MASK_SPECIAL_CASE, P.MASK_EARLY_RETURN,
                 P.MASK_FABRICATED, P.DELETE_TEST, P.RENAME_TEST,
                 P.WEAKEN_ASSERTION, P.REMOVE_ASSERTION, P.AGGREGATE_MIMIC,
                 P.SKIP_TEST, P.ALTER_FIXTURE, P.UNAUTHORIZED_GUTTING)
    for p in protected:
        catches[p] = catches.get(p, frozenset()) | frozenset({D.PROTECTED_CORE})
    return DefenseMatrix(catches=catches, disables=dict(h.disables))


COMPOSITION_MATRIX: Tuple[CompositeAttack, ...] = (
    CompositeAttack(
        composition_id="COMPOSE_WEAKEN_PLUS_MASK",
        primitives=(P.WEAKEN_ASSERTION, P.MASK_SPECIAL_CASE),
        expected_defeated=True,
        expected_catching_layers=frozenset({"regression", "holdout"}),
        holdout_intact=False,
        rationale="Weaken visible assertion AND mask holdout. Both layers must "
                  "still fire independently.",
    ),
    CompositeAttack(
        composition_id="COMPOSE_DELETE_PLUS_MASK",
        primitives=(P.DELETE_TEST, P.MASK_SPECIAL_CASE),
        expected_defeated=True,
        expected_catching_layers=frozenset({"identity", "holdout"}),
        holdout_intact=False,
        rationale="Delete visible test AND mask holdout.",
    ),
    CompositeAttack(
        composition_id="COMPOSE_ARCH_BOUNDARY_PLUS_MASK",
        primitives=(P.ARCH_BOUNDARY_REMOVAL, P.MASK_SPECIAL_CASE),
        expected_defeated=True,
        expected_catching_layers=frozenset({"invariant", "holdout"}),
        holdout_intact=False,
        rationale="Remove architectural boundary AND mask holdout.",
    ),
    CompositeAttack(
        composition_id="COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK",
        primitives=(P.ARCH_AUTH_REMOVAL, P.MASK_SPECIAL_CASE),
        expected_defeated=True,
        expected_catching_layers=frozenset({"invariant", "holdout"}),
        holdout_intact=False,
        rationale="Remove architectural auth AND mask holdout.",
    ),
    CompositeAttack(
        composition_id="COMPOSE_TRIPLE_DELETE_FORGE_MASK",
        primitives=(P.DELETE_TEST, P.AGGREGATE_MIMIC,
                    P.MASK_SPECIAL_CASE),
        expected_defeated=True,
        expected_catching_layers=frozenset({"identity", "attestation", "holdout"}),
        holdout_intact=False,
        rationale="Depth-3 attack: delete + forge aggregate + mask holdout.",
    ),
    CompositeAttack(
        composition_id="COMPOSED_CONTROL_SINGLE",
        primitives=(),
        expected_defeated=False,
        expected_catching_layers=frozenset(),
        holdout_intact=True,
        rationale="Control: a legitimate candidate (no attacks) must be accepted.",
    ),
)


@dataclass(frozen=True)
class ComposedDetectionMetrics:
    __test__ = False
    composition_id: str
    primitives: Tuple[str, ...]
    expected_defeated: bool
    expected_catching_layers: Tuple[str, ...]
    actual_catching_layers: Tuple[str, ...]
    defended: bool
    detector_cancellation: bool
    holdout_intact: bool
    candidate_hash: str
    evidence_hash: str
    detail: str = ""


@dataclass(frozen=True)
class ComposedMeasurementSummary:
    __test__ = False
    total_compositions: int
    adversarial_total: int
    control_total: int
    detection_rate: float
    false_negative_rate: float
    false_positive_rate: float
    false_positive_n: int
    mutation_score: float
    detector_cancellation_count: int
    mean_defense_depth: float
    holdout_integrity: bool
    deterministic_replay: bool
    layer_attribution: Dict[str, int]
    per_layer_detection: Dict[str, int]
