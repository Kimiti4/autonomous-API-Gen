"""
Tests for Phase 22.7 security, privacy, and audit hardening.
"""

from civilization.security_hardening.engine import SecurityHardeningEngine
from civilization.security_hardening.models import (
    AccessRequest,
    Principal,
    PrincipalType,
    SecurityHardeningPolicy,
)


def build_engine() -> SecurityHardeningEngine:
    policy = SecurityHardeningPolicy(
        require_authentication=True,
        allow_unauthenticated_read=False,
        high_impact_requires_approval=True,
        redact_secrets=True,
        repeated_denial_threshold=3,
    )

    return SecurityHardeningEngine(policy=policy)


def make_principal(
    authenticated: bool = True,
    roles=None,
) -> Principal:
    return Principal(
        id="agent_1",
        type=PrincipalType.AGENT,
        roles=roles or [],
        authenticated=authenticated,
    )


def test_unauthenticated_mutation_denied():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(authenticated=False),
        action="civilization.task.run",
    )

    decision = engine.authorize(request)

    assert decision.allowed is False


def test_authenticated_read_allowed():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(authenticated=True),
        action="oversight.dashboard.read",
    )

    decision = engine.authorize(request)

    assert decision.allowed is True


def test_security_action_requires_security_role():
    engine = build_engine()

    denied_request = AccessRequest(
        principal=make_principal(authenticated=True, roles=[]),
        action="security.policy.update",
    )

    denied_decision = engine.authorize(denied_request)

    assert denied_decision.allowed is False

    allowed_request = AccessRequest(
        principal=make_principal(
            authenticated=True,
            roles=["security_engineer"],
        ),
        action="security.policy.update",
    )

    allowed_decision = engine.authorize(allowed_request)

    assert allowed_decision.allowed is True


def test_high_impact_requires_approval():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(
            authenticated=True,
            roles=["admin"],
        ),
        action="evolution.candidate.promote",
        high_impact=True,
    )

    decision = engine.authorize(request)

    assert decision.allowed is False
    assert decision.required_human_approval is True


def test_secret_redaction():
    engine = build_engine()

    payload = {
        "username": "platform_agent",
        "password": "super_secret_password_123",
        "api_key": "api_key_abcdef123456789",
        "nested": {
            "token": "token_abcdef123456789",
        },
    }

    report = engine.redact_payload(payload)

    assert report.redacted is True
    assert report.redacted_payload["password"] == "[REDACTED]"
    assert report.redacted_payload["api_key"] == "[REDACTED]"
    assert report.redacted_payload["nested"]["token"] == "[REDACTED]"

    assert report.classification.value in {
        "CONFIDENTIAL",
        "RESTRICTED",
    }


def test_audit_chain_and_tamper_detection():
    engine = build_engine()

    engine.record_audit(
        actor_id="agent_1",
        actor_type="AGENT",
        action="civilization.task.run",
        decision="ALLOW",
        reason="Allowed by policy.",
        payload={"task_id": "task_1"},
    )

    engine.record_audit(
        actor_id="agent_2",
        actor_type="AGENT",
        action="civilization.task.finalize",
        decision="DENY",
        reason="Denied by resilience policy.",
        payload={"task_id": "task_2"},
    )

    verification = engine.verify_audit()

    assert verification["valid"] is True

    engine.audit_events[0].payload["task_id"] = "tampered"

    tampered_verification = engine.verify_audit()

    assert tampered_verification["valid"] is False
    assert tampered_verification["first_invalid_event_id"] is not None


def test_repeated_denials_create_alert():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(authenticated=True, roles=[]),
        action="security.policy.update",
    )

    for _ in range(3):
        engine.authorize(request)

    alert_types = {alert.alert_type for alert in engine.alerts}

    assert "REPEATED_DENIALS" in alert_types
    assert "POSSIBLE_PRIVILEGE_ESCALATION" in alert_types


def test_pii_detection_in_redaction():
    engine = build_engine()

    payload = {
        "user_id": "user_1",
        "contact_email": "user@example.com",
    }

    findings = engine.scan_payload(payload)

    assert any(f.is_pii for f in findings)


def test_aws_key_detection():
    engine = build_engine()

    payload = {"key": "AKIAIOSFODNN7EXAMPLE"}

    report = engine.redact_payload(payload)

    assert report.redacted is True
    assert any(
        f.pattern_name == "aws_access_key_id" for f in report.findings
    )


def test_jwt_token_detection():
    engine = build_engine()

    payload = {
        "data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dQw4w9WgXcQ"
    }

    findings = engine.scan_payload(payload)

    assert any(f.pattern_name == "jwt_token" for f in findings)


def test_private_key_detection():
    engine = build_engine()

    payload = {
        "key_data": "-----BEGIN RSA PRIVATE KEY-----\nfake_key_data\n-----END RSA PRIVATE KEY-----"
    }

    findings = engine.scan_payload(payload)

    assert any(f.pattern_name == "private_key" for f in findings)


def test_classification_public_payload():
    engine = build_engine()

    payload = {"name": "public_document", "value": "no_sensitive_data"}

    classification = engine.classify_payload(payload)

    assert classification.value == "INTERNAL"


def test_classification_with_pii():
    engine = build_engine()

    payload = {"user_email": "test@example.com"}

    classification = engine.classify_payload(payload)

    assert classification.value == "CONFIDENTIAL"


def test_audit_no_tampering():
    engine = build_engine()

    engine.record_audit(
        actor_id="agent_1",
        actor_type="AGENT",
        action="civilization.task.run",
        decision="ALLOW",
        reason="Allowed.",
    )

    verification = engine.verify_audit()

    assert verification["valid"] is True
    assert verification["event_count"] == 1


def test_alert_acknowledgment_and_resolution():
    engine = build_engine()

    engine.record_failure_alert = engine._raise_alert(
        alert_type="TEST_ALERT",
        severity="LOW",
        message="Test message",
    )

    alert = engine.acknowledge_alert(engine.record_failure_alert.id)
    assert alert.status == "ACKNOWLEDGED"

    alert = engine.resolve_alert(engine.record_failure_alert.id)
    assert alert.status == "RESOLVED"


def test_security_report():
    engine = build_engine()

    engine.record_audit(
        actor_id="agent_1",
        actor_type="AGENT",
        action="civilization.task.run",
        decision="ALLOW",
        reason="Allowed.",
    )

    report = engine.report()

    assert report["audit_event_count"] == 1
    assert report["audit_chain_valid"] is True
    assert report["alert_count"] == 0
    assert report["denial_tracked_principal_count"] == 0


def test_unauthenticated_high_impact_generates_alert():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(authenticated=False),
        action="evolution.candidate.promote",
        high_impact=True,
    )

    decision = engine.authorize(request)

    assert decision.allowed is False

    alert_types = [alert.alert_type for alert in engine.alerts]
    assert "UNAUTHENTICATED_HIGH_IMPACT" in alert_types


def test_secret_in_request_generates_alert():
    engine = build_engine()

    request = AccessRequest(
        principal=make_principal(authenticated=True, roles=["admin"]),
        action="civilization.task.run",
        context={"password": "super_secret_password_123"},
    )

    decision = engine.authorize(request)

    alert_types = [alert.alert_type for alert in engine.alerts]
    assert "SECRET_IN_REQUEST" in alert_types


def test_policy_engine_failure_fails_closed():
    class BrokenPolicyEngine:
        def evaluate(self, request):
            raise RuntimeError("Engine explosion")

    engine = build_engine()
    engine.policy_engine = BrokenPolicyEngine()

    request = AccessRequest(
        principal=make_principal(authenticated=True, roles=[]),
        action="civilization.task.run",
    )

    decision = engine.authorize(request)

    assert decision.allowed is False
    assert decision.required_human_approval is True
    assert "fail closed" in decision.reason


def test_allow_unauthenticated_read():
    policy = SecurityHardeningPolicy(
        require_authentication=True,
        allow_unauthenticated_read=True,
    )
    engine = SecurityHardeningEngine(policy=policy)

    request = AccessRequest(
        principal=make_principal(authenticated=False),
        action="oversight.dashboard.read",
    )

    decision = engine.authorize(request)

    assert decision.allowed is True


def test_admin_bypass_least_privilege():
    engine = build_engine()

    request = AccessRequest(
        principal=Principal(
            id="admin_1",
            type=PrincipalType.HUMAN,
            roles=["admin"],
            authenticated=True,
        ),
        action="civilization.organization.create",
    )

    decision = engine.authorize(request)

    assert decision.allowed is True
