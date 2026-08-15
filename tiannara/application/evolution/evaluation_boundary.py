"""R2.7.5-G -- Evaluation Trust Boundary.

Establishes the **evaluation authority** as structurally distinct from the
evolution/mutation engine: the protected test core (regression anchors +
hidden holdout) is authored by the authority, anchored as an ``EvolutionEvent``
in the canonical chain, and is immutable during evolution. Mutation operators
can only mint ``ISR_GENERATED`` identities (never protected).

The boundary makes four guarantees (proven under *honest* operation here; R2.8
attacks them adversarially):

  1. A non-empty protected core exists (hard invariant).
  2. Protected tests are immutable: content drift or deletion -> reject.
  3. Hidden tests are invisible to evolution (excluded from the visible set).
  4. Evolvable (ISR-generated) drift is flagged for causal justification, not
     auto-rejected -- so a legitimate repair adjusting a derived test survives.

The drift classifier consumes normalized ``TestExecution`` records (each carrying
a ``test_id`` + ``content_hash``) against a ``ProtectedTestSet``. The
``test_id`` survives rename (name-only signal); ``content_hash`` is SHA-256 over
the test body+assertions, so a same-named altered test is *gutting*. For
tests whose content hash is unavailable the classifier preserves them
(conservative: absence of evidence is not grounds to reject).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tiannara.application.evolution.ledger import (
    EvolutionEvent,
    EvolutionLedger,
    EventType,
)
from tiannara.domain.models.evidence import (
    DriftResult,
    Provenance,
    TestExecution,
    TestIdentity,
    Visibility,
)
from tiannara.domain.services.canonical import canonical_hash

# -- privileged provenance (authority-only) ------------------------------------

class EvaluationAuthority:
    """The privileged layer that mints protected test identities.

    This object has no representation inside the Evolution Engine's mutation
    surface; it is supplied by the outer constitution (the calibration harness /
    constitutional executive). Its existence is the mechanism for "protection is a
    privilege the engine cannot grant itself."
    """

    __test__ = False

    def identity(self, test_id: str, content_hash: str,
                 *, visibility: Visibility = Visibility.VISIBLE,
                 anchor_event_id: str = "") -> TestIdentity:
        return TestIdentity.from_provenance(
            test_id,
            Provenance.EVALUATION_AUTHORITY,
            content_hash=content_hash,
            visibility=visibility,
            anchor_event_id=anchor_event_id,
        )


# -- protected set / anchor -----------------------------------------------------

@dataclass(frozen=True)
class ProtectedTestSet:
    """The authoritative protected core, anchored as an ``EvolutionEvent``.

    ``identities`` is the full surface (protected + evolvable); ``anchor_event_id``
    binds the whole set to the canonical ledger so the anchor set itself inherits
    cascade-on-tamper integrity from R2.7.5-C/D.
    """

    identities: tuple[TestIdentity, ...]
    anchor_event_id: str
    environment_fingerprint: str
    content_hash: str

    @property
    def protected_core(self) -> tuple[TestIdentity, ...]:
        return tuple(t for t in self.identities if t.is_protected())

    @property
    def has_protected_core(self) -> bool:
        """R2.7.5-G hard invariant: a non-empty protected core must exist.

        An empty protected core means there is no ground truth the evolution
        process cannot move -- the boundary is vacuous and R2.8 would produce
        uninterpretable results.
        """
        return len(self.protected_core) > 0

    def by_id(self) -> dict[str, TestIdentity]:
        return {t.test_id: t for t in self.identities}

    def visible_to_evolution(self) -> tuple[TestIdentity, ...]:
        """The subset evolution may observe (excludes HIDDEN holdout tests)."""
        return tuple(t for t in self.identities if not t.is_hidden())


@dataclass(frozen=True)
class HoldoutSurface:
    """Read-isolated hidden holdout material (R2.8.7).

    The evaluation authority runs these tests *separately*, against the compiled
    candidate artifact, only after selection. The evolution / operator layer
    never observes them -- visibility controls observation, protection controls
    mutation, and hidden is strictly an observation constraint.

    ``content_hash`` commits the full holdout set (ids + body hashes) so any
    tampering with the holdout material is a detectable break of the anchor.
    """

    __test__ = False

    hidden_ids: tuple[str, ...]
    hidden_hashes: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True)
class ReadIsolationResult:
    """R2.8.7 read-isolation report for an operator's observed test surface.

    ``accept`` is False iff the surface an operator worked with contains a
    hidden test id -- i.e. evolution observed holdout material it is not
    permitted to see. This is the epistemic line, distinct from write-protection.
    """

    __test__ = False

    accept: bool
    leaked_hidden: tuple[str, ...]
    detail: str = ""


@dataclass
class EvaluationBoundary:
    """The R2.7.5-G boundary: anchor a protected core, then classify drift."""

    authority: EvaluationAuthority
    ledger: EvolutionLedger
    evolution_id: str

    def anchor(self, identities: Iterable[TestIdentity],
               environment_fingerprint: str = "") -> ProtectedTestSet:
        """Anchor the protected core as an authoritative EvolutionEvent.

        Raises if the supplied identities contain no protected tests -- the
        non-empty protected core is the foundational guarantee R2.8 depends on.
        """
        identities = tuple(identities)
        if not any(t.is_protected() for t in identities):
            raise ValueError(
                "R2.7.5-G invariant violated: a non-empty protected core is "
                "required (EvaluationAuthority must anchor ground truth); an "
                "evaluation with an empty protected core is vacuous"
            )
        event = EvolutionEvent(
            event_id="",
            evolution_id=self.evolution_id,
            sequence=0,
            event_type=EventType.ANCHOR,
            subject_id="",
            payload={
                "identities": [t.model_dump(mode="json") for t in identities],
                "environment_fingerprint": environment_fingerprint,
            },
            environment_hash=environment_fingerprint,
        )
        anchor_event_id = self.ledger.append_event(event, evolution_id=self.evolution_id)
        anchored = tuple(
            t.model_copy(update={"anchor_event_id": anchor_event_id})
            if isinstance(t, TestIdentity) else t
            for t in identities
        )
        content_hash = canonical_hash(
            {t.test_id: t.content_hash for t in anchored}
        )
        return ProtectedTestSet(
            identities=anchored,
            anchor_event_id=anchor_event_id,
            environment_fingerprint=environment_fingerprint,
            content_hash=content_hash,
        )

    def classify_drift(
        self,
        protected: ProtectedTestSet,
        candidate_tests: tuple[TestExecution, ...],
        *,
        causal_justification: bool = False,
    ) -> DriftResult:
        """Policy-driven drift classification against the anchored protected core.

        - Protected test body altered  -> CONTENT_GUTTING (reject)
        - Protected test vanished      -> REMOVED_TEST (reject)
        - A hidden test was observed    -> HIDDEN_LEAK (reject)
        - Evolvable test altered, no causal justification -> REQUIRES_JUSTIFICATION
        - Evolvable test altered, causality shown         -> ALLOWED_DRIFT
        - Content unchanged             -> PRESERVED
        """
        baseline = protected.by_id()
        seen: set[str] = set()
        rejected: list[str] = []
        removed: list[str] = []
        leaks: list[str] = []
        needs_just: list[str] = []
        allowed: list[str] = []
        preserved: list[str] = []

        for exec_ in candidate_tests:
            seen.add(exec_.test_id)
            ident = baseline.get(exec_.test_id)
            if ident is not None:
                if ident.is_hidden():
                    # Evolution is not supposed to observe hidden tests at all.
                    leaks.append(exec_.test_id)
                    continue
                if not exec_.content_hash:
                    # No content hash available -> be conservative, preserve.
                    preserved.append(exec_.test_id)
                    continue
                if ident.is_protected():
                    if exec_.content_hash != ident.content_hash:
                        rejected.append(exec_.test_id)
                    else:
                        preserved.append(exec_.test_id)
                else:
                    # Evolvable test: drift needs causal justification.
                    if exec_.content_hash != ident.content_hash:
                        if causal_justification:
                            allowed.append(exec_.test_id)
                        else:
                            needs_just.append(exec_.test_id)
                    else:
                        preserved.append(exec_.test_id)
            else:
                # Candidate test not in the anchored surface -> new/evolvable.
                preserved.append(exec_.test_id)

        # Protected tests that disappeared from the candidate run.
        for tid, ident in baseline.items():
            if ident.is_protected() and not ident.is_hidden() and tid not in seen:
                removed.append(tid)

        accept = not (rejected or removed or leaks)
        return DriftResult(
            protected_rejected=tuple(rejected),
            removed=tuple(removed),
            hidden_leaks=tuple(leaks),
            requires_justification=tuple(needs_just),
            allowed_drift=tuple(allowed),
            preserved=tuple(preserved),
            accept=accept,
            detail=(
                f"protected_gutted={rejected} protected_removed={removed} "
                f"hidden_leaks={leaks} needs_justification={needs_just} "
                f"allowed_drift={allowed}"
            ),
        )

    def holdout_surface(self, protected: ProtectedTestSet) -> HoldoutSurface:
        """R2.8.7: the read-isolated holdout material the authority runs separately.

        Evolution must never receive these identities; their content hashes are
        already anchored inside the ANCHOR event payload (see ``anchor``), so the
        returned ``content_hash`` additionally commits the holdout set as a
        unit -- a swap/subtract of any holdout test is a detectable break.
        """
        hidden = tuple(t for t in protected.identities if t.is_hidden())
        hashes = tuple(t.content_hash for t in hidden)
        ids = tuple(t.test_id for t in hidden)
        return HoldoutSurface(
            hidden_ids=ids,
            hidden_hashes=hashes,
            content_hash=canonical_hash(
                {"ids": list(ids), "hashes": list(hashes)}
            ),
        )

    def read_isolation_report(
        self, protected: ProtectedTestSet, observed_test_ids: tuple[str, ...]
    ) -> ReadIsolationResult:
        """R2.8.7: assert an operator's observed test surface contained no hidden id."""
        hidden_ids = self.holdout_surface(protected).hidden_ids
        leaked = tuple(tid for tid in observed_test_ids if tid in hidden_ids)
        return ReadIsolationResult(
            accept=not leaked,
            leaked_hidden=leaked,
            detail=(f"hidden_leaked={list(leaked)}" if leaked
                    else "no hidden tests observed by operator"),
        )


def visible_test_ids(identities: Iterable[TestIdentity]) -> tuple[str, ...]:
    """Helper: the test_ids evolution is allowed to observe (excludes hidden)."""
    return tuple(t.test_id for t in identities if not t.is_hidden())
