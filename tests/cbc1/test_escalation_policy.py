"""Tests for the escalation policy (Phase 31 gap #6).

The escalation policy is the constitutional missing piece: it defines
when autonomy yields to human judgment. The default state is
autonomous. Six triggers are the only paths to escalation:

  1. LOW_CONFIDENCE       confidence below configured threshold
  2. POLICY_CONFLICT      two policy decisions contradict
  3. HIGH_STAKES_OP       operation is in the explicit allow-list
  4. RETRY_EXHAUSTED      bounded retries are exhausted
  5. EVIDENCE_CORRUPTED   the evidence chain is broken
  6. UNKNOWN_SCHEMA       the input shape is not recognized

These tests enforce:
  - Default state is autonomous (PROCEED for the simple happy path)
  - All six triggers correctly ESCALATE under their conditions
  - All six triggers correctly PROCEED when their conditions are not met
  - The policy is data-driven (thresholds overridable, high-stakes
    allow-list extendable)
  - The decision primitive is synchronous, deterministic, and
    auditable (escalation events are immutable records)
  - Unknown contexts are treated conservatively (ESCALATE rather
    than silently PROCEED)
"""
import pytest

from certification.governance.escalation_policy import (
    Decision,
    EscalationContext,
    EscalationPolicy,
    HIGH_STAKES_OPERATIONS,
    POLICY_VERSION,
    SCHEMA_ID,
    Trigger,
)


# ---- Default state: autonomous ----


def test_default_policy_proceeds_for_known_safe_op():
    """The default policy is autonomous: a routine operation with high
    confidence and no conflict is PROCEED, not ESCALATE."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.LOW_CONFIDENCE, "trial-1", "compile this trial",
        EscalationContext(confidence=0.9),
    )
    assert d is Decision.PROCEED


def test_default_policy_does_not_escalate_known_schema():
    """A schema the system recognizes is PROCEED, not ESCALATE."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.UNKNOWN_SCHEMA, "trial-1", "compile this trial",
        EscalationContext(
            schema_name="known.schema",
            known_schemas=frozenset({"known.schema"}),
        ),
    )
    assert d is Decision.PROCEED


# ---- LOW_CONFIDENCE ----


def test_low_confidence_below_threshold_escalates():
    p = EscalationPolicy(low_confidence_threshold=0.6)
    d = p.decide(
        Trigger.LOW_CONFIDENCE, "decision-1", "accept this gate",
        EscalationContext(confidence=0.5),
    )
    assert d is Decision.ESCALATE


def test_low_confidence_at_threshold_proceeds():
    """Confidence exactly at the threshold does not escalate. The
    threshold is the floor for PROCEED; below is ESCALATE."""
    p = EscalationPolicy(low_confidence_threshold=0.6)
    d = p.decide(
        Trigger.LOW_CONFIDENCE, "decision-1", "accept this gate",
        EscalationContext(confidence=0.6),
    )
    assert d is Decision.PROCEED


def test_low_confidence_missing_confidence_escalates():
    """If confidence is not supplied, the policy cannot verify the
    threshold and MUST escalate (defense in depth — never silently
    proceed on missing data)."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.LOW_CONFIDENCE, "decision-1", "accept this gate",
        EscalationContext(),
    )
    assert d is Decision.ESCALATE


# ---- POLICY_CONFLICT ----


def test_policy_conflict_accepted_and_rejected_escalates():
    """When two policy decisions accept and reject the same subject,
    the system must NOT silently pick one — it must escalate."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.POLICY_CONFLICT, "gate-1", "gate resolution",
        EscalationContext(policy_decisions=(
            {"gate_id": "compile", "accepted": True, "reason": "ok"},
            {"gate_id": "verify", "accepted": False, "reason": "fail"},
        )),
    )
    assert d is Decision.ESCALATE


def test_policy_conflict_all_accepted_proceeds():
    p = EscalationPolicy()
    d = p.decide(
        Trigger.POLICY_CONFLICT, "gate-1", "gate resolution",
        EscalationContext(policy_decisions=(
            {"gate_id": "a", "accepted": True},
            {"gate_id": "b", "accepted": True},
        )),
    )
    assert d is Decision.PROCEED


def test_policy_conflict_all_rejected_proceeds():
    """All-rejected is a clear verdict (no contradiction); the system
    acts on it (the all-rejected verdict)."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.POLICY_CONFLICT, "gate-1", "gate resolution",
        EscalationContext(policy_decisions=(
            {"gate_id": "a", "accepted": False},
            {"gate_id": "b", "accepted": False},
        )),
    )
    assert d is Decision.PROCEED


def test_policy_conflict_no_decisions_proceeds():
    p = EscalationPolicy()
    d = p.decide(
        Trigger.POLICY_CONFLICT, "gate-1", "gate resolution",
        EscalationContext(policy_decisions=()),
    )
    assert d is Decision.PROCEED


# ---- HIGH_STAKES_OP ----


def test_high_stakes_op_in_default_allow_list_escalates():
    """The default allow-list contains the high-stakes operations the
    master prompt calls out (publish, deploy, ratify, revoke, etc.)."""
    p = EscalationPolicy()
    for op in ["publish_to_remote", "deploy_to_production", "ratify_governance_decision",
               "revoke_certification", "merge_cross_cutting_evolution"]:
        d = p.decide(
            Trigger.HIGH_STAKES_OP, f"subject-{op}", f"do {op}",
            EscalationContext(operation=op),
        )
        assert d is Decision.ESCALATE, f"op={op} should escalate"


def test_high_stakes_op_not_in_allow_list_proceeds():
    """An operation not on the allow-list runs autonomously (default
    state)."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.HIGH_STAKES_OP, "trial-1", "compile trial",
        EscalationContext(operation="compile_trial"),
    )
    assert d is Decision.PROCEED


def test_high_stakes_op_allow_list_extendable():
    """Operators can extend the allow-list at policy construction time
    to add new high-stakes operations."""
    p = EscalationPolicy(
        high_stakes_operations=frozenset({"rotate_signing_key"}),
    )
    d = p.decide(
        Trigger.HIGH_STAKES_OP, "rotation-1", "rotate signing key",
        EscalationContext(operation="rotate_signing_key"),
    )
    assert d is Decision.ESCALATE


# ---- RETRY_EXHAUSTED ----


def test_retry_exhausted_at_bound_escalates():
    p = EscalationPolicy(max_bounded_retries=2)
    d = p.decide(
        Trigger.RETRY_EXHAUSTED, "trial-1", "retry compile",
        EscalationContext(retry_count=2, max_retries=2),
    )
    assert d is Decision.ESCALATE


def test_retry_exhausted_below_bound_proceeds():
    p = EscalationPolicy(max_bounded_retries=2)
    d = p.decide(
        Trigger.RETRY_EXHAUSTED, "trial-1", "retry compile",
        EscalationContext(retry_count=1, max_retries=2),
    )
    assert d is Decision.PROCEED


# ---- EVIDENCE_CORRUPTED ----


def test_evidence_corrupted_false_escalates():
    p = EscalationPolicy()
    d = p.decide(
        Trigger.EVIDENCE_CORRUPTED, "ledger-1", "append to ledger",
        EscalationContext(evidence_hash_intact=False),
    )
    assert d is Decision.ESCALATE


def test_evidence_intact_proceeds():
    p = EscalationPolicy()
    d = p.decide(
        Trigger.EVIDENCE_CORRUPTED, "ledger-1", "append to ledger",
        EscalationContext(evidence_hash_intact=True),
    )
    assert d is Decision.PROCEED


def test_evidence_intact_unknown_conservative_escalates():
    """When the context is missing the integrity flag, the policy
    cannot verify the chain. Conservative default: ESCALATE."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.EVIDENCE_CORRUPTED, "ledger-1", "append to ledger",
        EscalationContext(),
    )
    assert d is Decision.ESCALATE


# ---- UNKNOWN_SCHEMA ----


def test_unknown_schema_not_in_known_set_escalates():
    p = EscalationPolicy()
    d = p.decide(
        Trigger.UNKNOWN_SCHEMA, "input-1", "parse this input",
        EscalationContext(
            schema_name="mystery.v1",
            known_schemas=frozenset({"known.v1", "known.v2"}),
        ),
    )
    assert d is Decision.ESCALATE


def test_unknown_schema_missing_schema_name_proceeds():
    """Without a schema name, the trigger is not applicable. This is
    different from 'an unrecognized schema name' — no schema name means
    the caller did not provide one, which is the caller's
    responsibility. The system proceeds because the trigger
    genuinely didn't fire."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.UNKNOWN_SCHEMA, "input-1", "parse this input",
        EscalationContext(known_schemas=frozenset({"a", "b"})),
    )
    assert d is Decision.PROCEED


def test_unknown_schema_empty_known_set_escalates():
    """An empty known_schemas set means the caller is saying 'I know
    nothing' — any schema_name would be unknown. The system must
    ESCALATE rather than silently invent a behavior."""
    p = EscalationPolicy()
    d = p.decide(
        Trigger.UNKNOWN_SCHEMA, "input-1", "parse this input",
        EscalationContext(schema_name="any.schema", known_schemas=frozenset()),
    )
    assert d is Decision.ESCALATE


# ---- Event record ----


def test_build_event_captures_decision_and_context():
    p = EscalationPolicy()
    evt = p.build_event(
        Trigger.HIGH_STAKES_OP, "release-1", "publish release",
        EscalationContext(operation="publish_to_remote"),
    )
    assert evt.schema_id == SCHEMA_ID
    assert evt.policy_version == POLICY_VERSION
    assert evt.trigger is Trigger.HIGH_STAKES_OP
    assert evt.subject_ref == "release-1"
    assert evt.request == "publish release"
    assert evt.decision is Decision.ESCALATE
    assert "operation" in evt.context
    assert evt.context["operation"] == "publish_to_remote"
    # Occurred_at is a real ISO timestamp
    assert "T" in evt.occurred_at
    assert evt.occurred_at.endswith("Z") or "+" in evt.occurred_at


def test_event_to_record_serializes_for_evidence():
    p = EscalationPolicy()
    evt = p.build_event(
        Trigger.LOW_CONFIDENCE, "decision-1", "accept gate",
        EscalationContext(confidence=0.3),
    )
    rec = evt.to_record()
    assert rec["schema_id"] == SCHEMA_ID
    assert rec["policy_version"] == POLICY_VERSION
    assert rec["trigger"] == "low_confidence"
    assert rec["decision"] == "escalate"
    # Round-trip through JSON
    import json
    serialized = json.dumps(rec, sort_keys=True)
    deserialized = json.loads(serialized)
    assert deserialized == rec


def test_event_is_immutable():
    """An EscalationEvent is frozen — no field can be modified after
    construction. This is the immutability invariant for evidence
    records."""
    p = EscalationPolicy()
    evt = p.build_event(
        Trigger.POLICY_CONFLICT, "g", "x",
        EscalationContext(policy_decisions=(
            {"gate_id": "a", "accepted": True},
            {"gate_id": "b", "accepted": False},
        )),
    )
    with pytest.raises((AttributeError, Exception)):
        evt.trigger = Trigger.LOW_CONFIDENCE  # type: ignore[misc]


# ---- High-stakes allow-list is documented ----


def test_high_stakes_allow_list_documented():
    """The default allow-list contains the operations the master prompt
    requires human review for. If this list is empty, the system would
    silently publish / deploy / ratify."""
    assert "publish_to_remote" in HIGH_STAKES_OPERATIONS
    assert "deploy_to_production" in HIGH_STAKES_OPERATIONS
    assert "ratify_governance_decision" in HIGH_STAKES_OPERATIONS
    assert "revoke_certification" in HIGH_STAKES_OPERATIONS
