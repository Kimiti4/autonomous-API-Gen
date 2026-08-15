"""
Default engineering role definitions.
"""

from __future__ import annotations

from typing import List

from .models import RoleDefinition


def default_role_definitions() -> List[RoleDefinition]:
    """Return default role definitions aligned with the constitution."""

    return [
        RoleDefinition(
            role_id="requirements_analyst",
            name="Requirements Analyst",
            responsibilities=[
                "Analyze requirements",
                "Clarify intent",
                "Identify missing information",
            ],
            authority_weight=0.70,
            required_evidence_types=["requirement_graph"],
        ),
        RoleDefinition(
            role_id="domain_expert",
            name="Domain Expert",
            responsibilities=[
                "Provide domain context",
                "Validate business capabilities",
            ],
            authority_weight=0.70,
            required_evidence_types=["domain_model"],
        ),
        RoleDefinition(
            role_id="software_architect",
            name="Software Architect",
            responsibilities=[
                "Design ISR-level architecture",
                "Evaluate trade-offs",
                "Preserve architectural integrity",
            ],
            authority_weight=1.00,
            required_evidence_types=["isr", "architecture_decision"],
        ),
        RoleDefinition(
            role_id="backend_engineer",
            name="Backend Engineer",
            responsibilities=[
                "Design service boundaries",
                "Recommend API behavior",
                "Evaluate backend constraints",
            ],
            authority_weight=0.75,
            required_evidence_types=["service_design"],
        ),
        RoleDefinition(
            role_id="frontend_engineer",
            name="Frontend Engineer",
            responsibilities=[
                "Recommend frontend architecture",
                "Evaluate usability constraints",
            ],
            authority_weight=0.75,
            required_evidence_types=["frontend_design"],
        ),
        RoleDefinition(
            role_id="database_engineer",
            name="Database Engineer",
            responsibilities=[
                "Recommend persistence architecture",
                "Evaluate data integrity constraints",
            ],
            authority_weight=0.80,
            required_evidence_types=["data_model"],
        ),
        RoleDefinition(
            role_id="security_engineer",
            name="Security Engineer",
            responsibilities=[
                "Evaluate security posture",
                "Recommend security controls",
            ],
            authority_weight=0.95,
            required_evidence_types=["security_review"],
        ),
        RoleDefinition(
            role_id="infrastructure_engineer",
            name="Infrastructure Engineer",
            responsibilities=[
                "Recommend infrastructure architecture",
                "Evaluate deployment constraints",
            ],
            authority_weight=0.80,
            required_evidence_types=["infrastructure_model"],
        ),
        RoleDefinition(
            role_id="devops_engineer",
            name="DevOps Engineer",
            responsibilities=[
                "Recommend delivery pipelines",
                "Evaluate operational readiness",
            ],
            authority_weight=0.85,
            required_evidence_types=["ci_cd"],
        ),
        RoleDefinition(
            role_id="qa_engineer",
            name="QA Engineer",
            responsibilities=[
                "Recommend testing strategy",
                "Evaluate verification evidence",
            ],
            authority_weight=0.85,
            required_evidence_types=["test_strategy"],
        ),
        RoleDefinition(
            role_id="performance_engineer",
            name="Performance Engineer",
            responsibilities=[
                "Evaluate performance characteristics",
                "Recommend performance controls",
            ],
            authority_weight=0.80,
            required_evidence_types=["performance_analysis"],
        ),
        RoleDefinition(
            role_id="documentation_engineer",
            name="Documentation Engineer",
            responsibilities=[
                "Recommend documentation structure",
                "Ensure traceability",
            ],
            authority_weight=0.60,
            required_evidence_types=["documentation"],
        ),
        RoleDefinition(
            role_id="reviewer",
            name="Reviewer",
            responsibilities=[
                "Review recommendations",
                "Identify conflicts",
                "Validate evidence",
            ],
            authority_weight=0.90,
            required_evidence_types=["review"],
        ),
        RoleDefinition(
            role_id="evolution_coordinator",
            name="Evolution Coordinator",
            responsibilities=[
                "Coordinate evolution campaigns",
                "Recommend genome refinements",
                "Align evolution with governance",
            ],
            authority_weight=0.85,
            required_evidence_types=["evolution_history"],
        ),
    ]
