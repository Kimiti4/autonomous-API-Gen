"""Canonical governance design baseline — R1-D.3 migration of F-C10-01.

This module provides a minimal-viable governance design for the canonical
evolution runtime. It is the canonical equivalent of
``constitutional_architecture.governance.governance_design_fitness.baseline_governance_design``
but uses plain dicts (no constitutional schema dependencies).

The function returns a fresh dict each call (never shared/mutated).

Security-by-design fundamentals are maxed so a brand-new architecture never
starts below the fail-closed gate. Every component clears the 0.2 selection
gate with margin.
"""
from __future__ import annotations

from typing import Any


def baseline_governance_design() -> dict[str, Any]:
    """Minimal-viable governance design — the floor every candidate is born under.

    R1-D.3 migration of F-C10-01. The canonical equivalent of
    ``constitutional_architecture.governance.governance_design_fitness.baseline_governance_design``.

    Security-by-design fundamentals are maxed so a brand-new architecture never
    starts below the fail-closed gate; amendment rigor, policy breadth and
    exception tolerance start modest so the variation operators have selection
    headroom to strengthen them.
    """
    return {
        "design_id": "baseline_governance_v1",
        "voting_rule": "simple_majority",
        "quorum": 1,
        "approval_stage_count": 1,
        "policy_rule_count": 3,
        "fail_closed_default": True,
        "exception_max_severity": "high",
        "exception_review_required": True,
        "audit_chaining_required": True,
        "compliance_evaluation_required": True,
        "versioning_strategy": "semver_chain",
    }
