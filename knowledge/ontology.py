"""
Knowledge Graph ontology registry.

This is the v0.1 ontology. It intentionally remains simple and explicit.

Constitutional rule:
- Ontology evolution must be governed.
- Invalid entity or relation types must be rejected.
"""

from __future__ import annotations

from .errors import OntologyViolation


ENTITY_TYPES: set[str] = {
    # Requirements and capabilities
    "REQUIREMENT",
    "BUSINESS_CAPABILITY",
    "USER_NEED",
    "ACCEPTANCE_CRITERIA",

    # Architecture and ISR
    "ISR_REVISION",
    "ARCHITECTURE_DECISION",
    "DOMAIN",
    "SERVICE",
    "COMPONENT",
    "MODULE",
    "API",
    "EVENT",
    "DATA_MODEL",
    "INTERFACE",

    # Governance
    "CONSTITUTION",
    "POLICY_SET",
    "POLICY_RULE",
    "APPROVAL_RECORD",
    "AUDIT_EVENT",
    "GOVERNANCE_EXCEPTION",
    "LINEAGE_RECORD",

    # Evolution
    "EVOLUTION_PROPOSAL",
    "MUTATION",
    "FITNESS_EVALUATION",
    "CANDIDATE_ARCHITECTURE",
    "SIMULATION_RESULT",

    # Compilation and deployment
    "COMPILER_BACKEND",
    "COMPILATION_JOB",
    "GENERATED_ARTIFACT",
    "DEPLOYMENT",
    "DEPLOYMENT_ENVIRONMENT",
    "INFRASTRUCTURE_RESOURCE",

    # Operations
    "TELEMETRY_SIGNAL",
    "INCIDENT",
    "ALERT",
    "PERFORMANCE_OBSERVATION",
    "COST_OBSERVATION",
    "SECURITY_FINDING",
    "OPERATIONAL_POLICY",

    # Product and feedback
    "PRODUCT",
    "FEATURE",
    "CUSTOMER_FEEDBACK",
    "MARKET_OPPORTUNITY",
    "USAGE_METRIC",

    # Testing
    "TEST_SUITE",
    "TEST_CASE",
    "TEST_RUN",
    "TEST_EVIDENCE",

    # Documentation
    "DOCUMENT",
    "ARCHITECTURE_DOC",
    "OPERATOR_GUIDE",
    "SECURITY_DOC",
    "RUNBOOK",

    # Organization
    "ORGANIZATION",
    "TEAM",
    "ROLE",
    "AGENT",
    "HUMAN_USER",

    # Knowledge graph administration
    "ONTOLOGY_CLASS",
    "RELATION_TYPE",
    "PROPERTY_DEFINITION",
    "INGESTION_JOB",
    "GRAPH_SNAPSHOT",
    "RECOMMENDATION",
}


RELATION_TYPES: set[str] = {
    # Structural
    "PART_OF",
    "CONTAINS",
    "DEPENDS_ON",
    "IMPLEMENTS",
    "REALIZES",
    "SATISFIES",
    "REFERENCES",
    "DERIVES_FROM",
    "VERSION_OF",
    "SUPERSEDES",
    "RELATED_TO",

    # Traceability
    "TRACES_TO",
    "TRACES_FROM",
    "IMPACTS",
    "AFFECTED_BY",
    "PRODUCED_BY",
    "PRODUCES",
    "DEPLOYED_AS",
    "MONITORED_BY",
    "VALIDATED_BY",
    "EVIDENCED_BY",

    # Governance
    "GOVERNED_BY",
    "APPROVED_BY",
    "REJECTED_BY",
    "AUDITED_BY",
    "EXEMPTED_BY",
    "CONSTRAINED_BY",

    # Evolution
    "MUTATED_FROM",
    "SELECTED_FROM",
    "EVALUATED_BY",
    "IMPROVES",
    "REGRESSES",
    "COMPETES_WITH",

    # Operational
    "CAUSED_BY",
    "MITIGATES",
    "CORRELATES_WITH",
    "OBSERVED_IN",
    "REPORTED_BY",
    "ESCALATED_TO",

    # Organizational
    "ASSIGNED_TO",
    "OWNED_BY",
    "COLLABORATES_WITH",
    "REVIEWED_BY",
    "AUTHORED_BY",

    # Recommendation
    "SUPPORTS",
    "CONTRADICTS",
    "RECOMMENDS",
    "JUSTIFIES",

    # Common API / event / data relations
    "EXPOSES",
    "CONSUMES",
    "USES",
}


def validate_entity_type(entity_type: str) -> None:
    """Validate that an entity type exists in the ontology."""
    if entity_type not in ENTITY_TYPES:
        raise OntologyViolation(f"Unknown entity type: {entity_type}")


def validate_relation_type(relation_type: str) -> None:
    """Validate that a relation type exists in the ontology."""
    if relation_type not in RELATION_TYPES:
        raise OntologyViolation(f"Unknown relation type: {relation_type}")
