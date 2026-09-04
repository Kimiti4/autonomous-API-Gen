"""Escalation Policy — when autonomy yields to human judgment.

Phase 31 spec's "Cross-Cutting Gaps to Close Before Phase 31" item #6:
  "Escalation policy: Defines the conditions under which autonomy
   yields to human judgment, across all phases."

Default state: autonomous. Six triggers (below) are the only paths to
escalation. Every escalation event is recorded in the evidence chain as
an immutable record, so an auditor can reconstruct exactly when, why,
and to what the system deferred.

Triggers (each is a Predicate, not a magic value):

  1. LOW_CONFIDENCE       the policy's confidence on a decision is
                           below the configured threshold. The system
                           must NOT proceed on low confidence.
  2. POLICY_CONFLICT      two policy decisions contradict (e.g. two
                           gates reject each other). The system must
                           NOT silently pick one.
  3. HIGH_STAKES_OP       the operation would change a durable external
                           state (e.g. publish, deploy, governance
                           ratification). Listed explicitly in
                           HIGH_STAKES_OPERATIONS.
  4. RETRY_EXHAUSTED      N bounded retries of the same operation have
                           all failed. The system must NOT silently
                           retry N+1 times.
  5. EVIDENCE_CORRUPTED   the evidence chain (hash) is broken, or a
                           signature is missing. The system must NOT
                           proceed with a broken chain.
  6. UNKNOWN_SCHEMA       an input shape or contract is unrecognized.
                           The system must NOT silently invent a
                           behavior for an unknown contract.

Each EscalationEvent carries:

  - trigger           the policy trigger (one of the six)
  - subject_ref       the entity the system was operating on
  - context           the policy-relevant data (varies by trigger)
  - occurred_at       ISO timestamp
  - policy_version    the policy that fired
  - request           the action the system wanted to take
                      (what would happen if autonomy continued)

The policy has a `decide()` method that takes a Trigger and a Context
and returns a Decision. A Decision is one of:

  - ESCALATE          the system stops; a human review is required
  - PROCEED           the system continues; the trigger is logged

The policy is intentionally minimal: no retry, no queue, no async. It
is a synchronous decision primitive that callers can use at any
decision boundary. Callers (the campaign runner, the evolution
controller, the publisher, the governance kernel) call `decide()` and
respect the result.

A future design can add a "review queue" abstraction (events are queued
for human review) and an "approval handoff" (a webhook or file that
holds the autonomous system in wait). For Phase 31, the policy is the
boundary that PREVENTS the system from taking an action it should not
take autonomously; the actual review queue is out of scope.
"""
from __future__ import annotations

import datetime as _dt
import enum
from dataclasses import dataclass, field
from typing import Any, Mapping


POLICY_VERSION = "1.0.0"
SCHEMA_ID = "tiannara.escalation.event"


class Trigger(str, enum.Enum):
    """The six escalation triggers. Adding a new trigger requires
    updating this enum AND the predicates in EscalationPolicy.decide
    AND the documentation here. The system has no way to invent a
    new trigger at runtime."""

    LOW_CONFIDENCE = "low_confidence"
    POLICY_CONFLICT = "policy_conflict"
    HIGH_STAKES_OP = "high_stakes_op"
    RETRY_EXHAUSTED = "retry_exhausted"
    EVIDENCE_CORRUPTED = "evidence_corrupted"
    UNKNOWN_SCHEMA = "unknown_schema"


# Trigger: HIGH_STAKES_OP — explicit allow-list of operations that
# must NOT proceed autonomously. Adding to this list is the only way
# to require human review for a new operation type; absent from the
# list, the operation runs autonomously (default).
HIGH_STAKES_OPERATIONS: frozenset[str] = frozenset({
    "publish_to_remote",
    "deploy_to_production",
    "ratify_governance_decision",
    "revoke_certification",
    "merge_cross_cutting_evolution",
})


# Default thresholds. Per-deployment overrides can be passed to
# EscalationPolicy.
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_MAX_BOUNDED_RETRIES = 2


class Decision(str, enum.Enum):
    ESCALATE = "escalate"
    PROCEED = "proceed"


@dataclass(frozen=True)
class EscalationContext:
    """The data the policy needs to make its decision.

    Fields are optional — only the relevant ones for the trigger
    need to be supplied. The policy reads the right one for each
    trigger. Unknown keys are ignored (forward-compatible).

    Attributes:
        confidence             the policy's confidence in [0, 1] for
                                LOW_CONFIDENCE. Lower = more uncertain.
        policy_decisions       list of decision dicts for POLICY_CONFLICT.
                                Each has at least {gate_id, accepted, reason}.
        operation              the operation name for HIGH_STAKES_OP.
        retry_count            the number of retries already attempted
                                for RETRY_EXHAUSTED.
        max_retries            the configured retry bound (caller-known).
        evidence_hash_intact   boolean for EVIDENCE_CORRUPTED.
        schema_name            the schema identifier for UNKNOWN_SCHEMA.
        known_schemas          frozenset of schema names the caller
                                recognizes.
    """

    confidence: float | None = None
    policy_decisions: tuple[dict, ...] = ()
    operation: str | None = None
    retry_count: int | None = None
    max_retries: int | None = None
    evidence_hash_intact: bool | None = None
    schema_name: str | None = None
    known_schemas: frozenset[str] = frozenset()

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "EscalationContext":
        """Build a context from a plain dict. Unknown keys are ignored."""
        kw: dict = {}
        if "confidence" in d:
            kw["confidence"] = float(d["confidence"])
        if "policy_decisions" in d:
            kw["policy_decisions"] = tuple(d["policy_decisions"])
        if "operation" in d:
            kw["operation"] = str(d["operation"])
        if "retry_count" in d:
            kw["retry_count"] = int(d["retry_count"])
        if "max_retries" in d:
            kw["max_retries"] = int(d["max_retries"])
        if "evidence_hash_intact" in d:
            kw["evidence_hash_intact"] = bool(d["evidence_hash_intact"])
        if "schema_name" in d:
            kw["schema_name"] = str(d["schema_name"])
        if "known_schemas" in d:
            kw["known_schemas"] = frozenset(d["known_schemas"])
        return cls(**kw)


@dataclass(frozen=True)
class EscalationEvent:
    """A single recorded escalation. Immutable; the policy emits these
    in ESCALATE decisions. Every event carries enough context for an
    auditor to reconstruct the decision."""

    schema_id: str
    policy_version: str
    trigger: Trigger
    subject_ref: str
    request: str
    context: Mapping[str, Any]
    occurred_at: str
    decision: Decision

    def to_record(self) -> dict:
        return {
            "schema_id": self.schema_id,
            "policy_version": self.policy_version,
            "trigger": self.trigger.value,
            "subject_ref": self.subject_ref,
            "request": self.request,
            "context": dict(self.context),
            "occurred_at": self.occurred_at,
            "decision": self.decision.value,
        }


@dataclass
class EscalationPolicy:
    """The escalation policy. Stateless except for the configured
    thresholds. The `decide()` method is the single decision primitive.

    Threshold overrides:
      - low_confidence_threshold: confidence below this is ESCALATE.
        Default 0.6 (matches the master prompt's "0.6 or above to
        proceed autonomously on routine decisions" rule of thumb).
      - max_bounded_retries: RETRY_EXHAUSTED fires when retry_count
        meets or exceeds this. Default 2.
    """

    policy_version: str = POLICY_VERSION
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD
    max_bounded_retries: int = DEFAULT_MAX_BOUNDED_RETRIES
    high_stakes_operations: frozenset[str] = field(
        default_factory=lambda: HIGH_STAKES_OPERATIONS,
    )

    def decide(
        self,
        trigger: Trigger,
        subject_ref: str,
        request: str,
        context: EscalationContext | Mapping[str, Any] | None = None,
    ) -> Decision:
        """Decide whether to ESCALATE or PROCEED for a given trigger.

        Returns Decision.ESCALATE or Decision.PROCEED. Does NOT raise,
        does NOT log — callers record the EscalationEvent when they
        escalate.
        """
        if context is None:
            ctx = EscalationContext()
        elif isinstance(context, EscalationContext):
            ctx = context
        else:
            ctx = EscalationContext.from_dict(context)

        if trigger is Trigger.LOW_CONFIDENCE:
            if ctx.confidence is None or ctx.confidence < self.low_confidence_threshold:
                return Decision.ESCALATE
            return Decision.PROCEED

        if trigger is Trigger.POLICY_CONFLICT:
            # Two decisions reject each other (or two accepted, two rejected)
            accepted = [d for d in ctx.policy_decisions if d.get("accepted")]
            rejected = [d for d in ctx.policy_decisions if not d.get("accepted")]
            if len(accepted) > 0 and len(rejected) > 0:
                return Decision.ESCALATE
            # If all decisions agree, proceed; if no decisions, proceed
            return Decision.PROCEED

        if trigger is Trigger.HIGH_STAKES_OP:
            if ctx.operation in self.high_stakes_operations:
                return Decision.ESCALATE
            return Decision.PROCEED

        if trigger is Trigger.RETRY_EXHAUSTED:
            if ctx.retry_count is not None and ctx.retry_count >= self.max_bounded_retries:
                return Decision.ESCALATE
            # Below the bound: do not escalate yet
            return Decision.PROCEED

        if trigger is Trigger.EVIDENCE_CORRUPTED:
            if ctx.evidence_hash_intact is False:
                return Decision.ESCALATE
            if ctx.evidence_hash_intact is True:
                return Decision.PROCEED
            # Unknown — treat as corrupted (conservative)
            return Decision.ESCALATE

        if trigger is Trigger.UNKNOWN_SCHEMA:
            if ctx.schema_name and ctx.schema_name not in ctx.known_schemas:
                return Decision.ESCALATE
            return Decision.PROCEED

        # Unknown trigger: treat as escalation (defense in depth)
        return Decision.ESCALATE

    def build_event(
        self,
        trigger: Trigger,
        subject_ref: str,
        request: str,
        context: EscalationContext | Mapping[str, Any] | None = None,
        decision: Decision | None = None,
    ) -> EscalationEvent:
        """Build an EscalationEvent. Calls decide() internally. Used by
        callers that want to log the decision in a single call."""
        if context is None:
            ctx = EscalationContext()
        elif isinstance(context, EscalationContext):
            ctx = context
        else:
            ctx = EscalationContext.from_dict(context)
        d = decision if decision is not None else self.decide(
            trigger, subject_ref, request, ctx,
        )
        return EscalationEvent(
            schema_id=SCHEMA_ID,
            policy_version=self.policy_version,
            trigger=trigger,
            subject_ref=subject_ref,
            request=request,
            context={
                "confidence": ctx.confidence,
                "policy_decisions": list(ctx.policy_decisions),
                "operation": ctx.operation,
                "retry_count": ctx.retry_count,
                "max_retries": ctx.max_retries,
                "evidence_hash_intact": ctx.evidence_hash_intact,
                "schema_name": ctx.schema_name,
                "known_schemas": sorted(ctx.known_schemas),
            },
            occurred_at=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decision=d,
        )
