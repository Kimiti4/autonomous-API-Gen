"""
Phase 1 — Intent Schema
Pass 2 Output: Technology-neutral representation of human intent.

Constitutional Alignment:
- ISR is the canonical source of truth (Intent Model feeds ISR, never bypasses it)
- No technology coupling (enforced by ConstitutionValidator/IntentValidator)
- Security by Design (security requirements are first-class)
- Observability by Design (observability requirements are first-class)
- Multi-objective optimization (quality attributes map to Pareto dimensions)
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from constitutional_architecture.core.constitution import FORBIDDEN_LEXICON


# ─── Enumerations ────────────────────────────────────────────────────────────

class QualityAttribute(str, Enum):
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    EVOLVABILITY = "evolvability"
    EXTENSIBILITY = "extensibility"
    MODULARITY = "modularity"
    RELIABILITY = "reliability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    TESTABILITY = "testability"
    OBSERVABILITY = "observability"
    ACCESSIBILITY = "accessibility"
    COGNITIVE_LOAD = "cognitive_load"
    COST_EFFICIENCY = "cost_efficiency"
    DEPLOYMENT_READINESS = "deployment_readiness"
    AI_READINESS = "ai_readiness"


class BusinessArchetype(str, Enum):
    B2B_SAAS = "b2b_saas"
    B2C_SAAS = "b2c_saas"
    MARKETPLACE = "marketplace"
    E_COMMERCE = "e_commerce"
    INTERNAL_TOOL = "internal_tool"
    DATA_PLATFORM = "data_platform"
    AI_APPLICATION = "ai_application"
    IOT_SYSTEM = "iot_system"
    EMBEDDED_SYSTEM = "embedded_system"
    SCIENTIFIC_PLATFORM = "scientific_platform"
    MOBILE_APPLICATION = "mobile_application"
    API_PLATFORM = "api_platform"
    CONTENT_PLATFORM = "content_platform"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    ERP = "erp"
    CRM = "crm"


class ComplianceStandard(str, Enum):
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    FEDRAMP = "fedramp"
    CCPA = "ccpa"
    SOX = "sox"


class OperationalConstraint(str, Enum):
    OFFLINE_FIRST = "offline_first"
    MULTI_REGION = "multi_region"
    EDGE_COMPUTING = "edge_computing"
    AIR_GAPPED = "air_gapped"
    LOW_LATENCY = "low_latency"
    HIGH_THROUGHPUT = "high_throughput"
    REAL_TIME = "real_time"
    BATCH_PROCESSING = "batch_processing"
    MULTI_TENANT = "multi_tenant"
    SINGLE_TENANT = "single_tenant"


# ─── Sub-Models ──────────────────────────────────────────────────────────────

class Persona(BaseModel):
    name: str
    role: str
    primary_goals: List[str]
    technical_proficiency: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced|expert)$")
    accessibility_needs: List[str] = Field(default_factory=list)


class Capability(BaseModel):
    name: str
    description: str
    priority: float = Field(ge=0.0, le=1.0, default=0.5)
    dependencies: List[str] = Field(default_factory=list)
    security_classification: str = Field(default="standard", pattern="^(public|internal|confidential|restricted)$")


class DataDomain(BaseModel):
    name: str
    entities: List[str]
    consistency_requirement: str = Field(default="eventual", pattern="^(strong|eventual|causal)$")
    retention_policy: Optional[str] = None


class IntegrationPoint(BaseModel):
    name: str
    direction: str = Field(pattern="^(inbound|outbound|bidirectional)$")
    protocol_semantics: str = Field(default="rest", pattern="^(rest|graphql|event_stream|rpc|file_transfer|webhook)$")
    data_format: str = Field(default="json", pattern="^(json|xml|protobuf|avro|csv|binary)$")
    latency_requirement_ms: Optional[int] = None


# ─── Sanitization (Option 1 constitutional gate) ─────────────────────────────

class ForbiddenTermFound(ValueError):
    pass


def sanitize_forbidden_terms(text: str) -> str:
    """Replace forbidden technology terms with their abstract equivalents.

    Constitutional: This is the ONLY function permitted to transform
    forbidden terms into abstractions. It must run BEFORE the IntentModel
    is constructed (Pass 1 boundary).
    """
    replacements: dict[str, str] = {
        "react": "component_framework",
        "vue": "component_framework",
        "svelte": "component_framework",
        "angular": "component_framework",
        "tailwind": "styling_framework",
        "bootstrap": "styling_framework",
        "material-ui": "component_library",
        "chakra": "component_library",
        "fastapi": "api_framework",
        "express": "api_framework",
        "django": "web_framework",
        "flask": "web_framework",
        "postgresql": "relational_database",
        "postgres": "relational_database",
        "mysql": "relational_database",
        "mongodb": "document_database",
        "redis": "key_value_store",
        "aws": "cloud_provider",
        "azure": "cloud_provider",
        "gcp": "cloud_provider",
        "docker": "container_runtime",
        "kubernetes": "container_orchestrator",
        "k8s": "container_orchestrator",
    }
    result = text
    for term, replacement in sorted(replacements.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        result = pattern.sub(replacement, result)
    return result


# ─── The Canonical Intent Model ──────────────────────────────────────────────

class IntentModel(BaseModel):
    project_name: str
    problem_statement: str
    version: str = "1.0.0"

    personas: List[Persona] = Field(min_length=1)

    business_archetype: BusinessArchetype
    core_capabilities: List[Capability] = Field(min_length=1)

    data_domains: List[DataDomain] = Field(default_factory=list)
    integration_points: List[IntegrationPoint] = Field(default_factory=list)

    quality_priorities: Dict[QualityAttribute, float] = Field(
        default_factory=lambda: {attr: 0.5 for attr in QualityAttribute}
    )

    authentication_required: bool = True
    authorization_model: str = Field(default="rbac", pattern="^(rbac|abac|pbac|acl|none)$")
    encryption_at_rest: bool = True
    encryption_in_transit: bool = True
    audit_logging_required: bool = True

    structured_logging_required: bool = True
    metrics_required: bool = True
    distributed_tracing_required: bool = False
    health_checks_required: bool = True

    compliance_standards: List[ComplianceStandard] = Field(default_factory=list)

    operational_constraints: List[OperationalConstraint] = Field(default_factory=list)
    expected_user_scale: str = Field(default="thousands", pattern="^(hundreds|thousands|tens_of_thousands|hundreds_of_thousands|millions)$")

    enrichment_agents: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)

    @field_validator("quality_priorities")
    @classmethod
    def validate_quality_weights(cls, v: Dict[QualityAttribute, float]) -> Dict[QualityAttribute, float]:
        for attr, weight in v.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Quality weight for {attr} must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_security_consistency(self) -> IntentModel:
        if ComplianceStandard.HIPAA in self.compliance_standards:
            if not self.encryption_at_rest or not self.encryption_in_transit:
                raise ValueError("HIPAA compliance requires encryption at rest and in transit.")
            if not self.audit_logging_required:
                raise ValueError("HIPAA compliance requires audit logging.")
        if ComplianceStandard.PCI_DSS in self.compliance_standards:
            if not self.encryption_in_transit:
                raise ValueError("PCI-DSS compliance requires encryption in transit.")
        return self
