"""
Security, privacy, and audit hardening engine.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils import canonical_json, deterministic_id, sha256_hex, utcnow
from .models import (
    AccessDecision,
    AccessRequest,
    PrincipalType,
    RedactionReport,
    SecuredAuditEvent,
    SecretFinding,
    SecurityAlert,
    SecurityClassification,
    SecurityHardeningPolicy,
)


GENESIS_HASH = "genesis"


ROLE_PERMISSIONS = {
    "READ": ["*"],
    "RECOMMEND": [
        "requirements_analyst",
        "domain_expert",
        "software_architect",
        "backend_engineer",
        "frontend_engineer",
        "database_engineer",
        "security_engineer",
        "infrastructure_engineer",
        "devops_engineer",
        "qa_engineer",
        "performance_engineer",
        "documentation_engineer",
        "reviewer",
        "evolution_coordinator",
    ],
    "MUTATE": [
        "operator",
        "devops_engineer",
        "backend_engineer",
        "frontend_engineer",
        "database_engineer",
        "infrastructure_engineer",
        "evolution_coordinator",
    ],
    "GOVERN": [
        "governance_admin",
        "human_operator",
        "federation_council",
    ],
    "SECURITY": [
        "security_engineer",
        "security_admin",
    ],
    "AUDIT": [
        "auditor",
        "security_admin",
    ],
}


class SecurityHardeningError(Exception):
    """Base error for security hardening operations."""


class SecurityHardeningEngine:
    """Engine for security, privacy, and audit hardening."""

    def __init__(
        self,
        policy: Optional[SecurityHardeningPolicy] = None,
        policy_engine=None,
        oversight_engine=None,
    ) -> None:
        self.policy = policy or SecurityHardeningPolicy()

        self.policy_engine = policy_engine
        self.oversight = oversight_engine

        self.audit_events: List[SecuredAuditEvent] = []
        self.last_hash: str = GENESIS_HASH

        self.alerts: List[SecurityAlert] = []

        self.denial_counts: Dict[str, int] = {}

        self.secret_patterns = self._default_secret_patterns()

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def authorize(self, request: AccessRequest) -> AccessDecision:
        alerts: List[str] = []

        secret_findings = self.scan_payload(request.context)

        if secret_findings and self.policy.alert_on_secret_detection:
            alert = self._raise_alert(
                alert_type="SECRET_IN_REQUEST",
                severity="HIGH",
                principal_id=request.principal.id,
                action=request.action,
                message=(
                    "Secret or sensitive data detected in request context."
                ),
            )

            alerts.append(alert.id)

        if self.policy_engine and hasattr(self.policy_engine, "evaluate"):
            decision = self._authorize_with_policy_engine(request)
        else:
            decision = self._fallback_authorize(request)

        if decision.alerts:
            alerts.extend(decision.alerts)

        decision.alerts = alerts

        self._detect_threats(request, decision, secret_findings)

        if self.policy.audit_all_access:
            self.record_audit(
                actor_id=request.principal.id,
                actor_type=request.principal.type.value,
                action=request.action,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                decision="ALLOW" if decision.allowed else "DENY",
                reason=decision.reason,
                payload=request.context,
            )

        return decision

    # ------------------------------------------------------------------
    # Secret detection and redaction
    # ------------------------------------------------------------------

    def scan_payload(self, payload: Any) -> List[SecretFinding]:
        _, findings = self._redact_value(
            value=copy.deepcopy(payload),
            path="$",
            findings=[],
            collect_only=True,
        )

        return findings

    def redact_payload(self, payload: Any) -> RedactionReport:
        redacted_payload, findings = self._redact_value(
            value=copy.deepcopy(payload),
            path="$",
            findings=[],
            collect_only=False,
        )

        classification = self._classify_findings(findings, payload)

        return RedactionReport(
            redacted=len(findings) > 0,
            classification=classification,
            findings=findings,
            redacted_payload=redacted_payload,
        )

    def classify_payload(self, payload: Any) -> SecurityClassification:
        findings = self.scan_payload(payload)
        return self._classify_findings(findings, payload)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def record_audit(
        self,
        actor_id: str,
        actor_type: str,
        action: str,
        decision: str,
        reason: str = "",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> SecuredAuditEvent:
        occurred_at = utcnow().isoformat()

        if self.policy.redact_secrets and payload is not None:
            redaction = self.redact_payload(payload)
            safe_payload = redaction.redacted_payload
        else:
            safe_payload = payload or {}

        event_id = deterministic_id(
            "secured_audit_event",
            {
                "actor_id": actor_id,
                "action": action,
                "occurred_at": occurred_at,
                "event_count": len(self.audit_events),
            },
        )

        event_data = {
            "id": event_id,
            "occurred_at": occurred_at,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "decision": decision,
            "reason": reason,
            "payload": safe_payload,
            "previous_hash": self.last_hash,
        }

        event_hash = sha256_hex(canonical_json(event_data))

        event = SecuredAuditEvent(
            id=event_id,
            occurred_at=occurred_at,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            reason=reason,
            payload=safe_payload,
            previous_hash=self.last_hash,
            event_hash=event_hash,
        )

        self.audit_events.append(event)
        self.last_hash = event_hash

        return event

    def verify_audit(self) -> Dict:
        previous_hash = GENESIS_HASH

        for event in self.audit_events:
            if event.previous_hash != previous_hash:
                return {
                    "valid": False,
                    "event_count": len(self.audit_events),
                    "first_invalid_event_id": event.id,
                    "reason": "Broken previous-hash chain.",
                }

            expected_data = {
                "id": event.id,
                "occurred_at": event.occurred_at,
                "actor_id": event.actor_id,
                "actor_type": event.actor_type,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "decision": event.decision,
                "reason": event.reason,
                "payload": event.payload,
                "previous_hash": event.previous_hash,
            }

            expected_hash = sha256_hex(canonical_json(expected_data))

            if event.event_hash != expected_hash:
                return {
                    "valid": False,
                    "event_count": len(self.audit_events),
                    "first_invalid_event_id": event.id,
                    "reason": "Event hash mismatch.",
                }

            previous_hash = event.event_hash

        return {
            "valid": True,
            "event_count": len(self.audit_events),
            "first_invalid_event_id": None,
            "reason": "Audit chain valid.",
        }

    # ------------------------------------------------------------------
    # Alerts and reporting
    # ------------------------------------------------------------------

    def list_alerts(self, status: Optional[str] = None) -> List[SecurityAlert]:
        if not status:
            return list(self.alerts)

        return [alert for alert in self.alerts if alert.status == status]

    def acknowledge_alert(self, alert_id: str) -> SecurityAlert:
        alert = self._get_alert(alert_id)
        alert.status = "ACKNOWLEDGED"
        return alert

    def resolve_alert(self, alert_id: str) -> SecurityAlert:
        alert = self._get_alert(alert_id)
        alert.status = "RESOLVED"
        return alert

    def report(self) -> Dict:
        audit_verification = self.verify_audit()

        return {
            "generated_at": utcnow().isoformat(),
            "audit_event_count": len(self.audit_events),
            "audit_chain_valid": audit_verification["valid"],
            "alert_count": len(self.alerts),
            "open_alert_count": len(self.list_alerts(status="OPEN")),
            "denial_tracked_principal_count": len(self.denial_counts),
        }

    # ------------------------------------------------------------------
    # Internal authorization helpers
    # ------------------------------------------------------------------

    def _authorize_with_policy_engine(
        self,
        request: AccessRequest,
    ) -> AccessDecision:
        try:
            from ..policy.models import PolicyEvaluationRequest

            policy_request = PolicyEvaluationRequest(
                subject_type=request.principal.type.value,
                subject_id=request.principal.id,
                roles=request.principal.roles,
                action=request.action,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                high_impact=request.high_impact,
                approval_refs=request.context.get("approval_refs", []),
                context=request.context,
            )

            result = self.policy_engine.evaluate(policy_request)

            allowed = result.decision.value == "ALLOW"

            required_human_approval = (
                result.decision.value == "REQUIRE_APPROVAL"
            )

            return AccessDecision(
                allowed=allowed,
                reason=result.reason,
                required_human_approval=required_human_approval,
                decision_id=result.evaluated_policy_id,
                timestamp=utcnow().isoformat(),
            )

        except Exception as exc:
            return AccessDecision(
                allowed=False,
                reason=f"Policy engine failure; fail closed: {exc}",
                required_human_approval=True,
                timestamp=utcnow().isoformat(),
            )

    def _fallback_authorize(self, request: AccessRequest) -> AccessDecision:
        principal = request.principal
        category = self._action_category(request.action)

        timestamp = utcnow().isoformat()

        if (
            self.policy.require_authentication
            and not principal.authenticated
        ):
            if not (
                category == "READ"
                and self.policy.allow_unauthenticated_read
            ):
                return AccessDecision(
                    allowed=False,
                    reason="Principal is not authenticated.",
                    timestamp=timestamp,
                )

        if (
            request.high_impact
            and self.policy.high_impact_requires_approval
            and not request.context.get("approval_refs")
        ):
            return AccessDecision(
                allowed=False,
                reason="High-impact action requires approval evidence.",
                required_human_approval=True,
                timestamp=timestamp,
            )

        if category == "READ":
            if principal.authenticated or self.policy.allow_unauthenticated_read:
                return AccessDecision(
                    allowed=True,
                    reason="Read action allowed.",
                    timestamp=timestamp,
                )

            return AccessDecision(
                allowed=False,
                reason="Read action requires authentication.",
                timestamp=timestamp,
            )

        if category in ROLE_PERMISSIONS:
            allowed_roles = ROLE_PERMISSIONS[category]

            if "*" in allowed_roles and principal.authenticated:
                return AccessDecision(
                    allowed=True,
                    reason=f"Authenticated principal allowed for {category}.",
                    timestamp=timestamp,
                )

            if "admin" in principal.roles:
                return AccessDecision(
                    allowed=True,
                    reason="Admin role allowed.",
                    timestamp=timestamp,
                )

            if any(role in allowed_roles for role in principal.roles):
                return AccessDecision(
                    allowed=True,
                    reason=f"Role authorized for {category}.",
                    timestamp=timestamp,
                )

        return AccessDecision(
            allowed=False,
            reason="No matching least-privilege authorization rule.",
            timestamp=timestamp,
        )

    def _action_category(self, action: str) -> str:
        normalized = action.lower()

        if normalized.startswith("security."):
            return "SECURITY"

        if normalized.startswith("audit."):
            return "AUDIT"

        if normalized.startswith("governance."):
            return "GOVERN"

        if normalized.endswith(".read") or ".read." in normalized:
            return "READ"

        if "recommend" in normalized:
            return "RECOMMEND"

        if "dashboard" in normalized and "read" in normalized:
            return "READ"

        return "MUTATE"

    # ------------------------------------------------------------------
    # Threat detection
    # ------------------------------------------------------------------

    def _detect_threats(
        self,
        request: AccessRequest,
        decision: AccessDecision,
        secret_findings: List[SecretFinding],
    ) -> None:
        principal_key = request.principal.id

        if not decision.allowed:
            self.denial_counts[principal_key] = (
                self.denial_counts.get(principal_key, 0) + 1
            )

            if (
                self.denial_counts[principal_key]
                >= self.policy.repeated_denial_threshold
            ):
                self._raise_alert(
                    alert_type="REPEATED_DENIALS",
                    severity="MEDIUM",
                    principal_id=principal_key,
                    action=request.action,
                    message=(
                        "Principal has exceeded the repeated denial "
                        "threshold."
                    ),
                )

            category = self._action_category(request.action)

            if (
                self.policy.alert_on_privilege_escalation
                and category in {"SECURITY", "GOVERN", "AUDIT"}
            ):
                self._raise_alert(
                    alert_type="POSSIBLE_PRIVILEGE_ESCALATION",
                    severity="HIGH",
                    principal_id=principal_key,
                    action=request.action,
                    message=(
                        "Denied access to a privileged action category."
                    ),
                )

        else:
            self.denial_counts.pop(principal_key, None)

        if (
            self.policy.alert_on_unauthenticated_high_impact
            and request.high_impact
            and not request.principal.authenticated
        ):
            self._raise_alert(
                alert_type="UNAUTHENTICATED_HIGH_IMPACT",
                severity="CRITICAL",
                principal_id=principal_key,
                action=request.action,
                message="Unauthenticated high-impact action attempted.",
            )

        if secret_findings and self.policy.alert_on_secret_detection:
            self._raise_alert(
                alert_type="SECRET_OR_PII_DETECTED",
                severity="HIGH",
                principal_id=principal_key,
                action=request.action,
                message="Secret or sensitive data detected.",
            )

    def _raise_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        principal_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> SecurityAlert:
        created_at = utcnow().isoformat()

        alert_id = deterministic_id(
            "security_alert",
            {
                "alert_type": alert_type,
                "principal_id": principal_id,
                "action": action,
                "created_at": created_at,
                "alert_count": len(self.alerts),
            },
        )

        alert = SecurityAlert(
            id=alert_id,
            alert_type=alert_type,
            severity=severity,
            principal_id=principal_id,
            action=action,
            message=message,
            created_at=created_at,
        )

        self.alerts.append(alert)

        return alert

    def _get_alert(self, alert_id: str) -> SecurityAlert:
        for alert in self.alerts:
            if alert.id == alert_id:
                return alert

        raise SecurityHardeningError(f"Alert not found: {alert_id}")

    # ------------------------------------------------------------------
    # Redaction internals
    # ------------------------------------------------------------------

    def _default_secret_patterns(self):
        return [
            {
                "name": "private_key",
                "pattern": re.compile(
                    r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"
                ),
                "severity": "CRITICAL",
                "is_pii": False,
            },
            {
                "name": "aws_access_key_id",
                "pattern": re.compile(r"AKIA[0-9A-Z]{16}"),
                "severity": "CRITICAL",
                "is_pii": False,
            },
            {
                "name": "jwt_token",
                "pattern": re.compile(
                    r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
                ),
                "severity": "HIGH",
                "is_pii": False,
            },
            {
                "name": "generic_secret",
                "pattern": re.compile(
                    r"(?i)(api[_-]?key|token|secret|password|credential)"
                    r"\s*[:=]\s*[\w\-\.]{8,}"
                ),
                "severity": "HIGH",
                "is_pii": False,
            },
            {
                "name": "email_address",
                "pattern": re.compile(
                    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                ),
                "severity": "LOW",
                "is_pii": True,
            },
        ]

    def _is_sensitive_key(self, key: str) -> bool:
        normalized = key.lower()

        sensitive_substrings = (
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "credential",
            "private_key",
            "privatekey",
            "authorization",
        )

        return any(item in normalized for item in sensitive_substrings)

    def _redact_value(
        self,
        value: Any,
        path: str,
        findings: List[SecretFinding],
        collect_only: bool,
    ) -> Tuple[Any, List[SecretFinding]]:
        if isinstance(value, dict):
            result: Dict[str, Any] = {}

            for key, item in value.items():
                child_path = f"{path}.{key}"

                if self._is_sensitive_key(key) and not isinstance(
                    item,
                    (dict, list),
                ):
                    findings.append(
                        SecretFinding(
                            path=child_path,
                            pattern_name="sensitive_key",
                            severity="HIGH",
                            is_pii=False,
                        )
                    )

                    result[key] = "[REDACTED]"
                    continue

                redacted_child, findings = self._redact_value(
                    value=item,
                    path=child_path,
                    findings=findings,
                    collect_only=collect_only,
                )

                result[key] = redacted_child

            return result, findings

        if isinstance(value, list):
            result_list: List[Any] = []

            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"

                redacted_child, findings = self._redact_value(
                    value=item,
                    path=child_path,
                    findings=findings,
                    collect_only=collect_only,
                )

                result_list.append(redacted_child)

            return result_list, findings

        if isinstance(value, str):
            redacted_text = value

            for secret_pattern in self.secret_patterns:
                matcher = secret_pattern["pattern"]

                if matcher.search(value):
                    findings.append(
                        SecretFinding(
                            path=path,
                            pattern_name=secret_pattern["name"],
                            severity=secret_pattern["severity"],
                            is_pii=secret_pattern["is_pii"],
                        )
                    )

                    if not collect_only:
                        redacted_text = matcher.sub(
                            "[REDACTED]",
                            redacted_text,
                        )

            return redacted_text, findings

        return value, findings

    def _classify_findings(
        self,
        findings: List[SecretFinding],
        payload: Any,
    ) -> SecurityClassification:
        if isinstance(payload, dict):
            declared = payload.get("classification")

            if declared:
                try:
                    return SecurityClassification(str(declared).upper())
                except ValueError:
                    pass

        has_critical = any(
            finding.severity == "CRITICAL"
            for finding in findings
        )

        has_high = any(
            finding.severity == "HIGH"
            for finding in findings
        )

        has_pii = any(finding.is_pii for finding in findings)

        if has_critical:
            return SecurityClassification.RESTRICTED

        if has_high:
            return SecurityClassification.RESTRICTED

        if has_pii:
            return SecurityClassification.CONFIDENTIAL

        if findings:
            return SecurityClassification.CONFIDENTIAL

        return SecurityClassification.INTERNAL
