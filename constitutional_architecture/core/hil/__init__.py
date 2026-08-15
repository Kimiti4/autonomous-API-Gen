"""
Phase 16.1 — Human Interaction Layer (HIL) Projection Engine.

Implements the four ratified decisions (ESAP-HIL-ARCH-001):
  D-1 capability-based navigation projection (deny-by-default,
      explainable denials) — core/hil/capabilities.py + policy_engine.py
  D-2 immutable ISR snapshots (content-addressed; snapshot_id consumed
      by the projection request) — via projection_ref
  D-3 constitutional arbitration (append-only, re-derivable records;
      UI notices surface arbitration events) — events surface
  D-4 renderer-agnostic UIPM v1 (renderer equivalence is a test
      property; latency budgets nav <= 16ms, layout <= 100ms)
      — core/hil/uipm.py
"""

from constitutional_architecture.core.hil.capabilities import (
    Capability,
    CapabilityAlias,
    CapabilityRegistry,
    CapabilityStatus,
)
from constitutional_architecture.core.hil.policy_engine import (
    AuthorizationDecision,
    Denial,
    NavigationEntry,
    NavigationProjection,
    PolicyEngine,
)
from constitutional_architecture.core.hil.uipm import (
    LAYOUT_LATENCY_BUDGET_MS,
    NAV_LATENCY_BUDGET_MS,
    UIPM_VERSION,
    Command,
    EventSurface,
    ProjectionRequest,
    UIPMDocument,
    UIPMSerializer,
    projection_ref,
)

__all__ = [
    "Capability", "CapabilityAlias", "CapabilityRegistry", "CapabilityStatus",
    "AuthorizationDecision", "Denial", "NavigationEntry", "NavigationProjection",
    "PolicyEngine",
    "LAYOUT_LATENCY_BUDGET_MS", "NAV_LATENCY_BUDGET_MS", "UIPM_VERSION",
    "Command", "EventSurface", "ProjectionRequest", "UIPMDocument",
    "UIPMSerializer", "projection_ref",
]
