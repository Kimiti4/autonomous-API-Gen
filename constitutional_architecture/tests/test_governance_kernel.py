"""
Phase 28 — Governance Kernel v0.1 tests.

Acceptance tests (from Task 28.1):
  A1  Deny Unsafe ISR Promotion       — no rollback plan + no evidence -> DENY
  A2  Require Approval High-Risk      — evidence present + arch review -> REQUIRE_APPROVAL
  A3  Allow After Approval            — approved + audited -> ALLOW + audit event
Plus unit coverage for every v0.1 manager and the safety properties.
"""

from datetime import datetime, timedelta, timezone

import pytest

from constitutional_architecture.governance import (
    ALL_POLICY_PACKS,
    Actor,
    ActorType,
    ApprovalDecision,
    ApproverType,
    ConstitutionStatus,
    Decision,
    ExceptionScope,
    GovernanceEvaluationRequest,
    GovernanceKernel,
    Invariant,
    InvariantSeverity,
)


def make_kernel() -> GovernanceKernel:
    kernel = GovernanceKernel()
    constitution = kernel.create_constitution(
        name="Platform Constitution",
        description="Root constitutional governance.",
        policy_domains=[
            "isr_integrity",
            "autonomy_bounds",
            "safety_verification",
            "reversibility",
            "auditability",
        ],
        invariants=[
            Invariant(
                id="inv_immutable_isr",
                name="ISR artifacts must be immutable",
                severity=InvariantSeverity.BLOCKING,
            )
        ],
    )
    kernel.activate_constitution(constitution.id)
    for pack_name, rules in ALL_POLICY_PACKS.items():
        policy_set = kernel.create_policy_set(
            name=pack_name,
            constitution_id=constitution.id,
            constitution_version=constitution.version,
            rule_definitions=rules,
        )
        kernel.activate_policy_set(policy_set.id)
    return kernel


def make_request(**overrides) -> GovernanceEvaluationRequest:
    params = dict(
        subject_type="ISR_REVISION",
        subject_id="isr_rev_9823",
        action="PROMOTE_ISR_REVISION",
        actor=Actor(
            actor_type=ActorType.AUTONOMOUS_AGENT,
            actor_id="evolution_agent_01",
            roles=["evolution_proposer"],
            delegated_authority=["propose_isr_changes"],
        ),
        context={
            "environment": "staging",
            "has_rollback_plan": True,
            "verification_status": "passed",
            "parent_hash": "h_parent",
            "content_hash": "h_content",
        },
        evidence_refs=["evidence:verification:8723", "evidence:simulation:1982"],
    )
    params.update(overrides)
    return GovernanceEvaluationRequest(**params)


def agent_actor(actor_id: str = "evolution_agent_01") -> Actor:
    return Actor(
        actor_type=ActorType.AUTONOMOUS_AGENT,
        actor_id=actor_id,
        roles=["evolution_proposer"],
        delegated_authority=["propose_isr_changes"],
    )


class TestAcceptanceDenyUnsafePromotion:
    """A1 — unsafe promotion is denied with an explanation."""

    def test_no_rollback_plan_and_no_hashes_is_denied(self):
        kernel = make_kernel()
        request = make_request(
            context={
                "has_rollback_plan": False,
                "verification_status": "failed",
            },
            evidence_refs=[],
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.DENY
        assert "rollback" in decision.reason.lower()
        assert decision.decision_hash

    def test_missing_parent_hash_is_denied(self):
        kernel = make_kernel()
        decision = kernel.evaluate(
            make_request(context={"has_rollback_plan": True})
        )
        assert decision.decision is Decision.DENY
        assert any(
            pe.rule_id == "isr_revision_requires_parent_hash"
            and pe.outcome.value == "MATCHED_DENY"
            for pe in decision.evaluated_policies
        )

    def test_no_rollback_plan_blocks(self):
        kernel = make_kernel()
        decision = kernel.evaluate(
            make_request(
                context={"has_rollback_plan": False},
                evidence_refs=["evidence:verification:8723"],
            )
        )
        assert decision.decision is Decision.DENY
        assert any(
            pe.rule_id == "isr_promotion_requires_rollback_plan"
            for pe in decision.evaluated_policies
        )

    def test_deny_overrides_allow(self):
        kernel = make_kernel()
        constitution = kernel.constitutions.active()[0]
        policy_set = kernel.create_policy_set(
            name="allow_all",
            constitution_id=constitution.id,
            constitution_version=constitution.version,
            rule_definitions=[
                {
                    "id": "allow_anything",
                    "effect": "ALLOW",
                    "subject_types": ["ISR_REVISION"],
                    "actions": ["PROMOTE_ISR_REVISION"],
                }
            ],
        )
        # allow_all was created as DRAFT; activation is required for
        # enforcement — verify DRAFT sets are not evaluated.
        request = make_request(
            context={"has_rollback_plan": True, "parent_hash": "p", "content_hash": "c"}
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.ALLOW  # draft not enforced
        kernel.activate_policy_set(policy_set.id)
        bad = kernel.evaluate(
            make_request(context={"has_rollback_plan": False})
        )
        assert bad.decision is Decision.DENY  # deny still wins over allow


class TestAcceptanceRequireApproval:
    """A2 — high-risk change with evidence requires architecture review."""

    def test_evolution_promotion_requires_approval(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_42",
            action="PROMOTE",
            context={
                "has_rollback_plan": True,
                "audit_commitment": True,
            },
            evidence_refs=["verification_report", "simulation_report"],
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.REQUIRE_APPROVAL
        assert any(
            a.approver_type is ApproverType.ROLE
            and a.approver_id == "architecture_reviewer"
            for a in decision.required_approvals
        )

    def test_missing_evidence_produces_require_evidence(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            action="PROMOTE",
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report"],  # simulation missing
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.REQUIRE_EVIDENCE
        assert "simulation_report" in decision.required_evidence


class TestAcceptanceAllowAfterApproval:
    """A3 — approval finalizes to ALLOW and an audit event is recorded."""

    def test_full_approval_flow_allows_and_audits(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_7",
            action="PROMOTE",
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )
        evaluation = kernel.evaluate(request)
        assert evaluation.decision is Decision.REQUIRE_APPROVAL
        approval_ids = kernel.create_approvals(evaluation)
        for approval_id in approval_ids:
            kernel.submit_approval(
                approval_id, ApprovalDecision.APPROVED,
                comments="Rollback plan verified.",
            )
        final = kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
        assert final.decision is Decision.ALLOW
        events = kernel.audit_events(subject_id="proposal_7")
        assert any(e.event_type == "ACTION_FINALIZED" for e in events)

    def test_rejection_blocks_execution(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            action="PROMOTE",
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )
        evaluation = kernel.evaluate(request)
        approval_ids = kernel.create_approvals(evaluation)
        kernel.submit_approval(
            approval_ids[0], ApprovalDecision.REJECTED,
            comments="Risk not acceptable.",
        )
        final = kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
        assert final.decision is Decision.DENY

    def test_timeout_denies_by_default(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            action="PROMOTE",
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )
        evaluation = kernel.evaluate(request)
        kernel.create_approvals(evaluation)
        now = datetime.now(timezone.utc) + timedelta(hours=72)
        kernel.approvals.set_clock(now)
        final = kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
        assert final.decision is Decision.DENY  # DENY_ON_TIMEOUT default


class TestConstitutionManager:
    def test_create_and_activate(self):
        kernel = make_kernel()
        constitution = kernel.get_constitution(
            kernel.constitutions.active()[0].id
        )
        assert constitution.status is ConstitutionStatus.ACTIVE
        assert constitution.effective_at is not None
        assert constitution.content_hash

    def test_content_hash_changes_with_content(self):
        kernel = make_kernel()
        a = kernel.constitutions.list()[0]
        b = kernel.create_constitution(name="Second Constitution")
        assert a.content_hash != b.content_hash

    def test_invariants_recorded(self):
        kernel = make_kernel()
        constitution = kernel.constitutions.list()[0]
        assert any(
            inv.id == "inv_immutable_isr"
            and inv.severity is InvariantSeverity.BLOCKING
            for inv in constitution.invariants
        )

    def test_revoked_cannot_activate(self):
        kernel = make_kernel()
        constitution = kernel.create_constitution(name="Doomed")
        kernel.constitutions.revoke(constitution.id)
        with pytest.raises(ValueError):
            kernel.activate_constitution(constitution.id)


class TestPolicyCompiler:
    def test_compiler_rejects_unknown_operator(self):
        kernel = make_kernel()
        with pytest.raises(ValueError):
            kernel.policy_sets.compiler.compile_rule(
                {
                    "id": "bad",
                    "effect": "DENY",
                    "subject_types": ["X"],
                    "actions": ["Y"],
                    "conditions": [
                        {"field": "context.a", "operator": "NO_SUCH_OP"}
                    ],
                }
            )

    def test_compiler_rejects_bad_field_prefix(self):
        kernel = make_kernel()
        with pytest.raises(ValueError):
            kernel.policy_sets.compiler.compile_rule(
                {
                    "id": "bad2",
                    "effect": "DENY",
                    "subject_types": ["X"],
                    "actions": ["Y"],
                    "conditions": [
                        {"field": "request.role", "operator": "EQUALS", "value": "x"}
                    ],
                }
            )

    def test_approval_rule_requires_approvals(self):
        kernel = make_kernel()
        with pytest.raises(ValueError):
            kernel.policy_sets.compiler.compile_rule(
                {
                    "id": "bad3",
                    "effect": "REQUIRE_APPROVAL",
                    "subject_types": ["X"],
                    "actions": ["Y"],
                }
            )

    def test_consistency_report_flags_shadowed_allow(self):
        kernel = make_kernel()
        findings = kernel.policy_sets.compiler.consistency_report(
            [
                kernel.policy_sets.compiler.compile_rule(
                    {"id": "a1", "effect": "ALLOW",
                     "subject_types": ["ISR_REVISION"],
                     "actions": ["PROMOTE_ISR_REVISION"]}
                ),
                kernel.policy_sets.compiler.compile_rule(
                    {"id": "d1", "effect": "DENY",
                     "subject_types": ["ISR_REVISION"],
                     "actions": ["PROMOTE_ISR_REVISION"]}
                ),
            ]
        )
        assert any("shadowed" in f for f in findings)


class TestAutonomousAuthority:
    def test_agent_cannot_grant_itself_authority(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="AGENT_PERMISSION",
            subject_id="perm_1",
            action="GRANT_AUTHORITY",
            actor=agent_actor("agent_1"),
            context={"target_agent_id": "agent_1"},
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.DENY
        assert any(
            pe.rule_id == "no_self_authority_expansion"
            for pe in decision.evaluated_policies
            if pe.outcome.value == "MATCHED_DENY"
        )

    def test_agent_can_grant_authority_to_another(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="AGENT_PERMISSION",
            action="GRANT_AUTHORITY",
            actor=agent_actor("agent_1"),
            context={"target_agent_id": "agent_2"},
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.ALLOW


class TestAudit:
    def test_hash_chain_is_tamper_evident(self):
        kernel = make_kernel()
        kernel.evaluate(make_request())
        kernel.evaluate(make_request(subject_id="isr_rev_9999"))
        assert kernel.audit_chain_intact()
        events = kernel.audit_events()
        assert len(events) >= 2
        assert events[0].previous_event_hash == ""
        assert events[1].previous_event_hash == events[0].event_hash

    def test_query_by_subject_and_action(self):
        kernel = make_kernel()
        kernel.evaluate(make_request(subject_id="isr_rev_100"))
        kernel.evaluate(make_request(subject_id="isr_rev_200"))
        hits = kernel.audit_events(subject_id="isr_rev_100")
        assert len(hits) == 1
        assert hits[0].subject_id == "isr_rev_100"

    def test_decision_reconstruction(self):
        kernel = make_kernel()
        request = make_request(
            subject_type="EVOLUTION_PROPOSAL",
            action="PROMOTE",
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )
        evaluation = kernel.evaluate(request)
        approval_ids = kernel.create_approvals(evaluation)
        for aid in approval_ids:
            kernel.submit_approval(aid, ApprovalDecision.APPROVED)
        kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
        from constitutional_architecture.governance.audit import decision_id_of

        dossier = kernel.reconstruct(decision_id_of(evaluation))
        assert dossier["request"]["action"] == "PROMOTE"
        assert dossier["decision"]["decision"] == "REQUIRE_APPROVAL"
        assert len(dossier["approvals"]) == len(approval_ids)
        assert any(
            e["event_type"] == "ACTION_FINALIZED"
            for e in dossier["lineage"]
        )


class TestLineage:
    def test_forward_and_backward_trace(self):
        kernel = make_kernel()
        kernel.record_lineage(
            parent_artifact_type="ISR_REVISION",
            parent_artifact_id="rev_a",
            parent_artifact_hash="hash_a",
            child_artifact_type="BUNDLE",
            child_artifact_id="bundle_1",
            child_artifact_hash="hash_b",
            change_type="COMPILED",
            decision_ref="decision_x",
            rollback_plan_ref="rollback:1",
        )
        kernel.record_lineage(
            parent_artifact_type="BUNDLE",
            parent_artifact_id="bundle_1",
            parent_artifact_hash="hash_b",
            child_artifact_type="DEPLOYMENT",
            child_artifact_id="dep_1",
            child_artifact_hash="hash_c",
            change_type="DEPLOYED",
            decision_ref="decision_y",
        )
        chain = kernel.lineage.ancestors("DEPLOYMENT", "dep_1")
        assert [link.change_type for link in chain] == ["DEPLOYED", "COMPILED"]
        assert kernel.lineage.by_decision("decision_x")[0].rollback_plan_ref == "rollback:1"


class TestExceptions:
    def test_exception_is_bounded_and_temporary(self):
        kernel = make_kernel()
        exception = kernel.create_exception(
            "temporary parent-hash waiver",
            justification="legacy import batch; mitigated by manual review",
            scope=ExceptionScope(
                subject_types=["ISR_REVISION"],
                actions=["PROMOTE_ISR_REVISION"],
                subject_ids=["isr_rev_legacy_1"],
            ),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        request = make_request(
            subject_id="isr_rev_legacy_1",
            context={"has_rollback_plan": True},
        )
        decision = kernel.evaluate(request)
        assert decision.decision is Decision.ALLOW
        assert exception.id in decision.exceptions_applied

    def test_exception_does_not_leak_outside_scope(self):
        kernel = make_kernel()
        kernel.create_exception(
            "narrow waiver",
            justification="only for legacy batch",
            scope=ExceptionScope(
                subject_types=["ISR_REVISION"],
                actions=["PROMOTE_ISR_REVISION"],
                subject_ids=["isr_rev_legacy_1"],
            ),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        decision = kernel.evaluate(
            make_request(
                subject_id="isr_rev_other",
                context={"has_rollback_plan": True},
            )
        )
        assert decision.decision is Decision.DENY

    def test_revoked_exception_is_immediately_invalid(self):
        kernel = make_kernel()
        exception = kernel.create_exception(
            "waiver",
            justification="testing revocation",
            scope=ExceptionScope(
                subject_types=["ISR_REVISION"],
                actions=["PROMOTE_ISR_REVISION"],
                subject_ids=["isr_rev_legacy_1"],
            ),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        kernel.revoke_exception(exception.id)
        decision = kernel.evaluate(
            make_request(
                subject_id="isr_rev_legacy_1",
                context={"has_rollback_plan": True},
            )
        )
        assert decision.decision is Decision.DENY

    def test_expired_exception_does_not_apply(self):
        kernel = make_kernel()
        kernel.create_exception(
            "expired waiver",
            justification="already expired",
            scope=ExceptionScope(
                subject_types=["ISR_REVISION"],
                actions=["PROMOTE_ISR_REVISION"],
                subject_ids=["isr_rev_legacy_1"],
            ),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        decision = kernel.evaluate(
            make_request(
                subject_id="isr_rev_legacy_1",
                context={"has_rollback_plan": True},
            )
        )
        assert decision.decision is Decision.DENY

    def test_exception_requires_justification(self):
        kernel = make_kernel()
        with pytest.raises(ValueError):
            kernel.create_exception(
                "no justification",
                justification="",
                scope=ExceptionScope(
                    subject_types=["ISR_REVISION"], actions=["PROMOTE_ISR_REVISION"]
                ),
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )


class TestDeterminism:
    def test_identical_requests_yield_identical_decisions(self):
        kernel = make_kernel()
        a = kernel.compliance.evaluate(make_request())
        b = kernel.compliance.evaluate(make_request())
        assert a.decision == b.decision
        assert a.reason == b.reason
        assert a.decision_hash == b.decision_hash

    def test_rule_order_is_deterministic(self):
        kernel = make_kernel()
        request = make_request()
        evaluations = kernel.compliance.evaluate(request).evaluated_policies
        rule_ids = [e.rule_id for e in evaluations]
        assert rule_ids == sorted(rule_ids)
