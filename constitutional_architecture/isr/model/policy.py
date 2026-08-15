"""
ISR Policy Model — security, governance, or operational rule sets.
Technology-neutral: no OAuth libraries, no JWT implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


@unique
class PolicyType(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    RATE_LIMITING = "rate_limiting"
    AUDIT = "audit"
    DATA_RETENTION = "data_retention"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class PolicyRule:
    id: str
    name: str
    description: str = ""
    rule_type: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass(frozen=True)
class Permission:
    id: str
    name: str
    description: str = ""
    resource: str = ""
    actions: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Policy:
    id: str
    name: str
    policy_type: PolicyType
    description: str = ""
    strategy: str = ""
    roles: tuple[str, ...] = ()
    rules: tuple[PolicyRule, ...] = ()
    permissions: tuple[Permission, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)