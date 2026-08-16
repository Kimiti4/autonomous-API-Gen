"""R2.10.3-A — temporal semantics primitive (timing INTENT on behavior).

The first primitive landed through the R2.10.2 extension protocol. The
primitive expresses *duration, ordering, deadline* — never timer
mechanisms (no asyncio.sleep, no scheduler, no liveness probe). Realization
is a compiler-backend concern, downstream of the backend-independent
semantic projection ``project_temporal_semantics``.

Boundary with ``behavior_await_surface`` (the R2.10.1 EXPRESSED gene):
temporal constraints REFERENCE behavior genes by id and never alter them.
A transition can be awaited AND carry a deadline; mutating the deadline
must leave the await surface and the transition genes byte-identical.

Landing rule (Option A): an ISR with no temporal constraints omits the
carrier entirely — existing FSM hashes are untouched. A constraint is
identity-changing only when present and meaningful.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class TemporalValidationError(ValueError):
    """A temporal constraint violates its construction or structural contract."""


@unique
class TemporalConstraintKind(str, Enum):
    TRANSITION_DEADLINE = "TRANSITION_DEADLINE"  # must complete within duration of trigger
    STATE_MIN_DURATION = "STATE_MIN_DURATION"    # must persist at least duration
    EVENT_ORDERING = "EVENT_ORDERING"            # following within duration of preceding


@dataclass(frozen=True)
class TemporalConstraint:
    """Timing INTENT on behavior. References behavior genes by id; never alters them.

    Technology-agnostic by construction: expresses duration/ordering/deadline,
    not timer mechanisms. Realization is a compiler-backend concern.
    """

    constraint_id: str
    kind: TemporalConstraintKind
    target_ref: str  # id of the transition/state/event constrained
    duration_ms: int  # semantic duration (intent, not a timer)
    reference_ref: Optional[str] = None  # for EVENT_ORDERING: the preceding event

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise TemporalValidationError("constraint_id must be non-empty")
        if self.duration_ms < 0:
            raise TemporalValidationError("duration must be non-negative")
        if (
            self.kind is TemporalConstraintKind.EVENT_ORDERING
            and self.reference_ref is None
        ):
            raise TemporalValidationError("EVENT_ORDERING requires a reference_ref")


def _module_target_ids(module: Any) -> tuple[set[str], set[str], set[str]]:
    """Resolve the id spaces a constraint may reference within one module:
    (transition ids, state ids, event ids)."""
    transition_ids: set[str] = set()
    state_ids: set[str] = set()
    for workflow in module.workflows:
        transition_ids.update(t.id for t in workflow.transitions)
        state_ids.update(s.id for s in workflow.states)
    event_ids = {e.id for e in module.events}
    return transition_ids, state_ids, event_ids


def validate_module_temporal_constraints(module: Any) -> tuple[str, ...]:
    """Structural validation for one module's temporal constraints.

    Returns human-readable violations; empty tuple means valid. Dangling
    targets, dangling ordering references, and duplicate constraint ids are
    rejected — pre-execution, before any compiler or runtime sees them.
    """
    errors: list[str] = []
    transition_ids, state_ids, event_ids = _module_target_ids(module)
    seen: set[str] = set()
    for constraint in module.temporal_constraints:
        if constraint.constraint_id in seen:
            errors.append(
                f"duplicate temporal constraint id '{constraint.constraint_id}' "
                f"in module '{module.id}'"
            )
        seen.add(constraint.constraint_id)
        if constraint.target_ref not in transition_ids | state_ids | event_ids:
            errors.append(
                f"temporal constraint '{constraint.constraint_id}' targets unknown "
                f"gene '{constraint.target_ref}' in module '{module.id}'"
            )
        if (
            constraint.kind is TemporalConstraintKind.EVENT_ORDERING
            and constraint.reference_ref is not None
            and constraint.reference_ref not in event_ids
        ):
            errors.append(
                f"temporal constraint '{constraint.constraint_id}' references unknown "
                f"preceding event '{constraint.reference_ref}' in module '{module.id}'"
            )
    return tuple(errors)


def project_temporal_semantics(isr: ISR) -> tuple[str, ...]:
    """Backend-independent semantic projection (the compile surface).

    Lowers each constraint into deterministic timing intent. This is the
    artifact the temporal gene compiles into; a backend realizes these
    intents with its own timer machinery — or not at all. The ISR never
    names a mechanism, so the projection never does either.
    """
    intents: list[str] = []
    for module in isr.system.modules:
        for constraint in sorted(
            module.temporal_constraints, key=lambda c: (c.kind.value, c.constraint_id)
        ):
            if constraint.kind is TemporalConstraintKind.TRANSITION_DEADLINE:
                intents.append(
                    f"transition {constraint.target_ref} must complete within "
                    f"{constraint.duration_ms}ms of its trigger"
                )
            elif constraint.kind is TemporalConstraintKind.STATE_MIN_DURATION:
                intents.append(
                    f"state {constraint.target_ref} must persist at least "
                    f"{constraint.duration_ms}ms"
                )
            else:
                intents.append(
                    f"event {constraint.target_ref} must follow event "
                    f"{constraint.reference_ref} within {constraint.duration_ms}ms"
                )
    return tuple(intents)


def project_temporal_evidence(isr: ISR) -> tuple[str, ...]:
    """Evidence projection: the observable, deterministic footprint of the
    temporal gene in an ISR — used by the audit's evidence and observability
    gates, and by evolution evaluation.
    """
    lines: list[str] = []
    for module in isr.system.modules:
        for constraint in sorted(
            module.temporal_constraints, key=lambda c: (c.kind.value, c.constraint_id)
        ):
            lines.append(
                f"module {module.id}: temporal constraint {constraint.constraint_id} "
                f"({constraint.kind.value}) on {constraint.target_ref} "
                f"duration_ms={constraint.duration_ms}"
            )
    return tuple(lines)