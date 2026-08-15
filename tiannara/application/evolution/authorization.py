"""R2.8.4 -- ISR-Authoritative Mutation Authorization.

Moves the source of "this test change is legitimate" out of the adversarial
layer and into the ISR. The authorization is **derived from the accepted ISR
delta**, never hand-injected by the mutation harness:

    accepted ISR delta (parent_isr -> candidate_isr)
            │
            ▼  TestSurfaceProjector.project   (deterministic, Docker-free)
    authorized_test_ids            // tests the delta permits to change
            │
            ▼  RegressionGate (I1)
    guttings of authorized ids permitted; all others rejected

Design notes:
  * The projector is the narrow, FSM-substrate projection the spec permits. In
    production it is grounded in `compile(ISR)` test-surface diffing (the
    generated `{slug}::test_orchestration_runs_clean`); here it is an ISR-delta
    function so the lab stays hermetic and deterministic.
  * Authorization is **set-based** on test ids for R2.8.4. Carrying the
    canonical post-change *content_hash* (so a weakening of an authorized test
    is also caught) is a documented R2.8.8+ refinement.
  * This module imports neither the gate nor the adversarial lab, so it can be
    consumed by both without creating an import cycle.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from constitutional_architecture.isr.model import ISR
from tiannara.domain.services.canonical import canonical_hash


@dataclass(frozen=True)
class Authorization:
    """ISR-derived grant for a candidate's test-surface changes (R2.8.4).

    ``authorized_test_ids`` is the PROJECTION of the accepted ISR delta onto
    test identity. A test edit is legitimate only when its id is entailed by
    the delta -- this is the substance of "the ISR is the source of truth for
    what an evolution may authorize."
    """

    __test__ = False

    parent_isr_hash: str
    candidate_isr_hash: str
    delta_hash: str
    authorized_test_ids: frozenset[str]

    @property
    def authorization_hash(self) -> str:
        return canonical_hash(
            (self.parent_isr_hash, self.candidate_isr_hash, self.delta_hash,
             sorted(self.authorized_test_ids))
        )

    @classmethod
    def from_delta(cls, parent_isr: ISR, candidate_isr: ISR,
                   projector: "TestSurfaceProjector") -> "Authorization":
        """Construct an authorization from an accepted ISR delta."""
        from tiannara.application.evolution.ledger import stable_isr_hash  # noqa: deferred import
        parent_hash = stable_isr_hash(parent_isr)
        candidate_hash = stable_isr_hash(candidate_isr)
        from constitutional_architecture.isr.serialization.serializer import ISRSerializer
        delta_hash = canonical_hash(
            (parent_hash, candidate_hash)
        )
        authorized = projector.project(parent_isr, candidate_isr)
        return cls(
            parent_isr_hash=parent_hash,
            candidate_isr_hash=candidate_hash,
            delta_hash=delta_hash,
            authorized_test_ids=authorized,
        )


class TestSurfaceProjector(Protocol):
    """Deterministic ISR delta -> authorized test-identity changes."""

    def project(self, parent_isr: ISR, candidate_isr: ISR) -> frozenset[str]:
        ...


class FSMTestSurfaceProjector:
    """Narrow, Docker-free, deterministic ISR -> test-impact projection.

    A behavior transition ``<from>_to_<to>`` is "touched" by a delta when the
    set of ``(from, to)`` transition pairs changes between the parent and
    candidate ISR. Each touched behavior authorizes the matching **evolvable**
    test id ``ev::<from>_to_<to>``.

    Protected regression anchors are NEVER authorized by the projection --
    only the evolvable surface may be touched, which is what makes Attack D
    (unauthorized weakening elsewhere) structurally detectable.
    """

    __test__ = False

    def project(self, parent_isr: ISR, candidate_isr: ISR) -> frozenset[str]:
        changed = self._behavior_diff(parent_isr, candidate_isr)
        return frozenset(f"ev::{b}" for b in changed)

    @staticmethod
    def _behaviors(isr: ISR) -> frozenset[str]:
        keys: set[str] = set()
        for module in getattr(isr.system, "modules", ()) or ():
            for wf in getattr(module, "workflows", ()) or ():
                for t in getattr(wf, "transitions", ()) or ():
                    keys.add(f"{t.from_state_id}_to_{t.to_state_id}")
        return frozenset(keys)

    def _behavior_diff(self, parent: ISR, candidate: ISR) -> set[str]:
        return set(self._behaviors(candidate)) ^ set(self._behaviors(parent))


def regression_infeasible_with_auth(reg, authorization: Authorization | None) -> bool:
    """Shared auth-exemption used by both RegressionGate and the adversarial decider.

    A candidate is regression-infeasible unless the *only* regression rejection
    is content-gutting of test ids that the ISR-derived authorization permits
    (the R2.7.5-G evolvable + legitimate-edit path). Everything else -- protected
    regression, protected gutting, vanish, skip, flake, failures -- is infeasible.
    When ``authorization`` is None the original uncompromising R2.7 semantics
    apply (no exemptions).
    """
    from tiannara.domain.models.evidence import RegressionClass, REGRESSION_REJECT_CLASSES
    keys = set(reg.class_counts)
    reject_present = any(
        RegressionClass(k) in REGRESSION_REJECT_CLASSES for k in keys
    )
    if not reject_present:
        return False
    authorized = authorization.authorized_test_ids if authorization else frozenset()
    reject_classes = {
        RegressionClass(k) for k in keys
        if RegressionClass(k) in REGRESSION_REJECT_CLASSES
    }
    only_content_gutting = reject_classes == {RegressionClass.CONTENT_GUTTING}
    all_gutting_authorized = set(reg.gutting) <= set(authorized)
    return reject_present and not (only_content_gutting and all_gutting_authorized)
