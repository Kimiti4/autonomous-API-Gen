"""
Phase 19 — Specialized Engineering Agents.

The Security Engineer and Domain Expert agents review requirement drafts,
relying on the Constitution and the CKB for evidence. They raise Critiques
with proposed ArchitecturalDirectives — never code.
"""

from __future__ import annotations

from typing import Any, Dict, List

from constitutional_architecture.core.agents.base import (
    Agent, ArchitecturalDirective, Critique, ObjectionSeverity,
)
from constitutional_architecture.core.models.intent import QualityAttribute

SENSITIVE_DATA_KEYWORDS = ("payment", "health", "ssn", "pii", "medical",
                           "financial", "credit", "card")

GOD_BLOB_ENTITY_THRESHOLD = 10


class SecurityEngineerAgent(Agent):
    """Reviews capabilities for sensitive-data classification gaps."""

    role: str = "Security Engineer"

    def analyze(self, draft_intent: Dict[str, Any],
                context: Dict[str, Any]) -> List[Critique]:
        critiques: List[Critique] = []
        capabilities = draft_intent.get("capabilities", [])

        for cap in capabilities:
            description = str(cap.get("description", "")).lower()
            if any(kw in description for kw in SENSITIVE_DATA_KEYWORDS):
                classification = cap.get("security_classification")
                if classification != "restricted":
                    critiques.append(Critique(
                        agent_role=self.role,
                        severity=ObjectionSeverity.FATAL,
                        message=(
                            f"Capability '{cap.get('name')}' handles "
                            "sensitive data but is not classified as "
                            "'restricted'."
                        ),
                        proposed_directives=[
                            ArchitecturalDirective(
                                target_node=f"CAPABILITY:{cap.get('name')}",
                                attribute="security_classification",
                                value="restricted",
                                rationale=(
                                    "Constitution: Security by Design. "
                                    "Sensitive data requires strict "
                                    "isolation and encryption."
                                ),
                            )
                        ],
                        pareto_impact={
                            QualityAttribute.SECURITY: 0.3,
                            QualityAttribute.PERFORMANCE: -0.1,
                        },
                    ))
        return critiques


class DomainExpertAgent(Agent):
    """Reviews data domains for DDD structural violations."""

    role: str = "Domain Expert"

    def analyze(self, draft_intent: Dict[str, Any],
                context: Dict[str, Any]) -> List[Critique]:
        critiques: List[Critique] = []
        domains = draft_intent.get("data_domains", [])

        for domain in domains:
            entity_count = len(domain.get("entities", []))
            if entity_count > GOD_BLOB_ENTITY_THRESHOLD:
                critiques.append(Critique(
                    agent_role=self.role,
                    severity=ObjectionSeverity.WARNING,
                    message=(
                        f"Domain '{domain.get('name')}' has {entity_count} "
                        "entities. Risk of God-Blob."
                    ),
                    proposed_directives=[],
                    pareto_impact={
                        QualityAttribute.MODULARITY: -0.2,
                        QualityAttribute.MAINTAINABILITY: -0.2,
                    },
                ))
        return critiques
