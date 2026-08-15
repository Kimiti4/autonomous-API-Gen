"""
Phase 28 — Governance Dashboard configuration.

v0.1 defaults for the dashboard BFF. Users, roles, and permissions are
declarative and replaceable; the Governance Kernel remains the authority
for governance decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping


@dataclass
class DashboardConfig:
    app_name: str = "Governance Console"
    session_cookie: str = "gov_session"
    session_ttl_seconds: int = 3600
    csrf_header: str = "X-CSRF-Token"
    # Sensitive context keys are redacted before rendering.
    redact_keys: tuple = (
        "secret",
        "token",
        "password",
        "passwd",
        "credential",
        "api_key",
        "private_key",
    )
    # role -> permissions
    role_permissions: Mapping[str, tuple] = field(
        default_factory=lambda: {
            "governance_viewer": ("read",),
            "governance_auditor": ("read", "verify_integrity"),
            "governance_approver": ("read", "approve", "reject"),
            "governance_operator": (
                "read",
                "approve",
                "reject",
                "revoke_exception",
                "verify_integrity",
            ),
            "governance_admin": ("read", "approve", "reject", "revoke_exception", "verify_integrity"),
        }
    )
    # web role -> kernel-side roles (kernel authorization stays authoritative)
    kernel_role_map: Mapping[str, tuple] = field(
        default_factory=lambda: {
            "governance_viewer": ("platform_operator",),
            "governance_auditor": ("auditor",),
            "governance_approver": ("auditor", "architecture_reviewer"),
            "governance_operator": ("platform_operator", "auditor"),
            "governance_admin": ("platform_operator", "auditor", "architecture_reviewer"),
        }
    )
    # test/demo users: username -> (password, roles)
    users: Mapping[str, tuple] = field(
        default_factory=lambda: {
            "alice": ("alice-pw", ("governance_auditor", "governance_operator")),
            "bob": ("bob-pw", ("governance_viewer",)),
            "carol": ("carol-pw", ("governance_approver",)),
            "dave": ("dave-pw", ("governance_admin",)),
        }
    )


def default_config() -> DashboardConfig:
    return DashboardConfig()
