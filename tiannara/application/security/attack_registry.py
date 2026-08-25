"""33.3 Registry -- declarative, immutable."""
from __future__ import annotations

from tiannara.application.security.attack_taxonomy import AttackDefinition, Criticality

REGISTRY = (
    AttackDefinition("sql-injection-001", "sql_injection", "union", "1.0.0", "db_interface_present", ("DB_INTERFACE",), Criticality.CRITICAL, ("db",), ("observation",), ("sandbox",), ("blocked",)),
    AttackDefinition("xss-001", "xss", "reflected", "1.0.0", "http_endpoint", ("HTTP_ENDPOINT",), Criticality.HIGH, ("http",), ("observation",), ("sandbox",), ("blocked",)),
    AttackDefinition("ssrf-001", "ssrf", "internal", "1.0.0", "external_network", ("EXTERNAL_NETWORK",), Criticality.HIGH, ("network",), ("observation",), ("sandbox",), ("blocked",)),
    AttackDefinition("auth-bypass-001", "broken_authentication", "credential_replay", "1.0.0", "auth_flow", ("AUTH_FLOW",), Criticality.CRITICAL, ("auth",), ("observation",), ("sandbox",), ("blocked",)),
    AttackDefinition("idor-001", "privilege_escalation", "idor", "1.0.0", "authorization_boundary", ("AUTHORIZATION_BOUNDARY",), Criticality.HIGH, ("authz",), ("observation",), ("sandbox",), ("blocked",)),
)

class AttackRegistry:
    def __init__(self, attacks=REGISTRY):
        ids = [a.attack_id for a in attacks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate attack identities")
        self._attacks = tuple(attacks)
        self._by_id = {a.attack_id: a for a in attacks}

    def get(self, attack_id: str) -> AttackDefinition:
        if attack_id not in self._by_id:
            raise KeyError(f"unknown attack {attack_id}")
        return self._by_id[attack_id]

    def all(self):
        return self._attacks

    def content_hash(self) -> str:
        from tiannara.domain.services.canonical import canonical_hash
        return canonical_hash([a.canonical_hash() for a in self._attacks])
