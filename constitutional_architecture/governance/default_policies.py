"""
Phase 28 — Initial Policy Packs 001-005.

The first enforceable rules that make the platform safer immediately.
Each rule is a declarative definition compiled by the PolicyCompiler.
"""

from __future__ import annotations

from typing import Any, Dict, List

POLICY_PACK_001_ISR_INTEGRITY: List[Dict[str, Any]] = [
    {
        "id": "isr_revision_requires_parent_hash",
        "name": "ISR revision requires parent hash",
        "effect": "DENY",
        "subject_types": ["ISR_REVISION"],
        "actions": ["PROMOTE_ISR_REVISION"],
        "conditions": [
            {"field": "context.parent_hash", "operator": "EXISTS", "value": False}
        ],
    },
    {
        "id": "isr_revision_requires_content_hash",
        "name": "ISR revision requires content hash",
        "effect": "DENY",
        "subject_types": ["ISR_REVISION"],
        "actions": ["PROMOTE_ISR_REVISION"],
        "conditions": [
            {"field": "context.content_hash", "operator": "EXISTS", "value": False}
        ],
    },
]

POLICY_PACK_002_REVERSIBILITY: List[Dict[str, Any]] = [
    {
        "id": "promotion_requires_rollback_plan",
        "name": "Promotion requires rollback plan",
        "description": "No promoted change may occur without a rollback plan.",
        "effect": "DENY",
        "subject_types": [
            "ISR_REVISION",
            "EVOLUTION_PROPOSAL",
            "DEPLOYMENT",
            "PRODUCT_RELEASE",
        ],
        "actions": ["PROMOTE", "DEPLOY", "LAUNCH"],
        "conditions": [
            {"field": "context.has_rollback_plan", "operator": "EQUALS", "value": False}
        ],
    },
    {
        "id": "isr_promotion_requires_rollback_plan",
        "name": "ISR promotion requires rollback plan",
        "effect": "DENY",
        "subject_types": ["ISR_REVISION"],
        "actions": ["PROMOTE_ISR_REVISION"],
        "conditions": [
            {"field": "context.has_rollback_plan", "operator": "EQUALS", "value": False}
        ],
    },
]

POLICY_PACK_003_VERIFICATION: List[Dict[str, Any]] = [
    {
        "id": "high_impact_change_requires_verification",
        "name": "High-impact change requires verification",
        "effect": "REQUIRE_EVIDENCE",
        "subject_types": ["EVOLUTION_PROPOSAL", "COMPILER_BACKEND", "PRODUCT_RELEASE"],
        "actions": ["PROMOTE", "DEPLOY", "LAUNCH"],
        "required_evidence": ["verification_report", "simulation_report"],
    },
    {
        "id": "isr_promotion_requires_verification",
        "name": "ISR promotion requires verification evidence",
        "effect": "DENY",
        "subject_types": ["ISR_REVISION"],
        "actions": ["PROMOTE_ISR_REVISION"],
        "conditions": [
            {
                "field": "context.verification_status",
                "operator": "NOT_EQUALS",
                "value": "passed",
            }
        ],
    },
]

POLICY_PACK_004_AUTONOMOUS_AUTHORITY: List[Dict[str, Any]] = [
    {
        "id": "no_self_authority_expansion",
        "name": "No self authority expansion",
        "description": "Autonomous agents may not grant themselves new authority.",
        "effect": "DENY",
        "subject_types": ["AGENT_PERMISSION"],
        "actions": ["GRANT_AUTHORITY"],
        "conditions": [
            {
                "field": "actor.actor_id",
                "operator": "EQUALS",
                "value": "context.target_agent_id",
            }
        ],
    },
]

POLICY_PACK_005_AUDITABILITY: List[Dict[str, Any]] = [
    {
        "id": "action_requires_audit_commitment",
        "name": "Action requires audit commitment",
        "effect": "DENY",
        "subject_types": [
            "ISR_REVISION",
            "EVOLUTION_PROPOSAL",
            "PLUGIN_INSTALLATION",
            "PRODUCT_RELEASE",
        ],
        "actions": ["PROMOTE", "INSTALL", "LAUNCH"],
        "conditions": [
            {
                "field": "context.audit_commitment",
                "operator": "EQUALS",
                "value": False,
            }
        ],
    },
]

POLICY_PACK_006_APPROVALS: List[Dict[str, Any]] = [
    {
        "id": "high_impact_change_requires_architecture_review",
        "name": "High-impact change requires architecture review",
        "effect": "REQUIRE_APPROVAL",
        "subject_types": ["EVOLUTION_PROPOSAL", "COMPILER_BACKEND", "PRODUCT_RELEASE"],
        "actions": ["PROMOTE", "DEPLOY", "LAUNCH"],
        "required_approvals": [
            {
                "approver_type": "ROLE",
                "approver_id": "architecture_reviewer",
                "required": True,
                "timeout_policy": "DENY_ON_TIMEOUT",
            }
        ],
    },
]

ALL_POLICY_PACKS: Dict[str, List[Dict[str, Any]]] = {
    "pack_001_isr_integrity": POLICY_PACK_001_ISR_INTEGRITY,
    "pack_002_reversibility": POLICY_PACK_002_REVERSIBILITY,
    "pack_003_verification": POLICY_PACK_003_VERIFICATION,
    "pack_004_autonomous_authority": POLICY_PACK_004_AUTONOMOUS_AUTHORITY,
    "pack_005_auditability": POLICY_PACK_005_AUDITABILITY,
    "pack_006_approvals": POLICY_PACK_006_APPROVALS,
}
