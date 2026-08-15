"""
Pass 2: Intent Analysis.

Constitutional Role:
- Transforms validated requirements into the canonical IntentModel.
- Technology-NEUTRAL output. Enforced by IntentValidator/ConstitutionValidator.
- Supports multi-agent enrichment (each agent refines specific fields).

Merges Option 2's rich extraction with Option 1's multi-agent enrichment.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, ComplianceStandard, DataDomain,
    IntentModel, IntegrationPoint, OperationalConstraint, Persona,
    QualityAttribute,
)
from constitutional_architecture.engine.passes.intent_validation_pass import ValidatedRequirement


class RequirementsValidationError(Exception):
    def __init__(self, violations: List[str]) -> None:
        self.violations = violations
        super().__init__(
            f"Requirements validation failed with {len(violations)} violation(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class IntentAnalysisError(Exception):
    pass


class IntentAnalyzer:
    """Pass 2: Produces the IntentModel from validated requirements.

    Constitutional Constraints:
    - Output MUST pass IntentValidator (no forbidden lexicon).
    - Output feeds ONLY into Pass 3 (Topology Resolver), never into compilers.
    - Each enrichment step is traceable (multi-agent accountability).
    """

    def analyze(
        self,
        validated_req: ValidatedRequirement,
        archetype_hint: Optional[BusinessArchetype] = None,
    ) -> IntentModel:
        if not validated_req.is_valid:
            raise ValueError(
                f"Cannot analyze invalid requirements. "
                f"Issues: {[i.message for i in validated_req.issues if i.severity == 'error']}"
            )

        req = validated_req.sanitized_input
        lower = req.lower()

        archetype = archetype_hint or self._infer_archetype(lower, req)
        personas = self._extract_personas(lower)
        capabilities = self._extract_capabilities(lower)
        quality_priorities = self._infer_quality_priorities(archetype)
        data_domains = self._extract_data_domains(lower)
        integrations = self._extract_integrations(lower)
        compliance = self._extract_compliance(lower)
        ops = self._extract_operational(lower)
        domain_context = self._infer_domain(lower)

        intent = IntentModel(
            project_name=validated_req.requirement_id,
            problem_statement=req,
            version="1.0.0",
            personas=personas,
            business_archetype=archetype,
            core_capabilities=capabilities,
            data_domains=data_domains,
            integration_points=integrations,
            quality_priorities=quality_priorities,
            compliance_standards=compliance,
            operational_constraints=ops,
            enrichment_agents=["IntentAnalyzer"],
            confidence_score=0.7,
        )

        return intent

    def enrich(self, intent: IntentModel, agent_name: str, updates: Dict[str, Any]) -> IntentModel:
        """Multi-agent enrichment. Each agent refines specific fields."""
        enriched = intent.model_copy(update=updates)
        enriched.enrichment_agents = intent.enrichment_agents + [agent_name]
        enriched.confidence_score = min(1.0, intent.confidence_score + (1.0 - intent.confidence_score) * 0.15)
        return enriched

    def analyze_from_dict(self, requirements: Dict[str, Any]) -> IntentModel:
        """Pass 1 + Pass 2 combined: validates dict requirements directly."""
        from constitutional_architecture.engine.passes.intent_validation_pass import RequirementsValidator

        validator = RequirementsValidator()
        raw_text = requirements.get("problem_statement", "")
        req_id = requirements.get("project_name", f"req-{uuid.uuid4().hex[:8]}")

        vresult = validator.validate(req_id, raw_text)
        if not vresult.is_valid:
            raise RequirementsValidationError(
                [i.message for i in vresult.issues if i.severity == "error"]
            )

        intent = self.analyze(vresult)
        return intent

    def _infer_archetype(self, lower: str, original: str) -> BusinessArchetype:
        if "saas" in lower or "subscription" in lower or "b2b" in lower:
            return BusinessArchetype.B2B_SAAS
        if "marketplace" in lower or "buyer" in lower:
            return BusinessArchetype.MARKETPLACE
        if "ecommerce" in lower or "shop" in lower or "store" in lower:
            return BusinessArchetype.E_COMMERCE
        if "internal" in lower or "admin" in lower or "back-office" in lower:
            return BusinessArchetype.INTERNAL_TOOL
        if "dashboard" in lower or "analytics" in lower or "kpi" in lower:
            return BusinessArchetype.DATA_PLATFORM
        if "ai" in lower or "ml" in lower or "machine learning" in lower or "model" in lower:
            return BusinessArchetype.AI_APPLICATION
        if "iot" in lower or "sensor" in lower or "device" in lower:
            return BusinessArchetype.IOT_SYSTEM
        if "mobile" in lower or "app" in lower:
            return BusinessArchetype.MOBILE_APPLICATION
        if "api" in lower or "integration" in lower:
            return BusinessArchetype.API_PLATFORM
        if "fintech" in lower or "payment" in lower or "banking" in lower:
            return BusinessArchetype.FINTECH
        if "health" in lower or "patient" in lower or "clinical" in lower:
            return BusinessArchetype.HEALTHCARE
        if "erp" in lower or "enterprise resource" in lower:
            return BusinessArchetype.ERP
        if "crm" in lower or "customer relationship" in lower:
            return BusinessArchetype.CRM
        if "content" in lower or "blog" in lower or "media" in lower:
            return BusinessArchetype.CONTENT_PLATFORM
        return BusinessArchetype.B2B_SAAS

    def _extract_personas(self, lower: str) -> List[Persona]:
        personas: List[Persona] = []
        if "admin" in lower:
            personas.append(Persona(
                name="Administrator", role="admin",
                primary_goals=["Manage system", "Configure settings"],
                technical_proficiency="intermediate",
            ))
        if "developer" in lower or "engineer" in lower:
            personas.append(Persona(
                name="Developer", role="developer",
                primary_goals=["Integrate with system", "Access API"],
                technical_proficiency="advanced",
            ))
        if "analyst" in lower or "analytics" in lower:
            personas.append(Persona(
                name="Analyst", role="analyst",
                primary_goals=["View reports", "Analyze data"],
                technical_proficiency="intermediate",
            ))
        if not personas:
            personas.append(Persona(
                name="End User", role="end_user",
                primary_goals=["Use the system", "Complete tasks"],
                technical_proficiency="intermediate",
            ))
        return personas

    def _extract_capabilities(self, lower: str) -> List[Capability]:
        caps: List[Capability] = []
        keyword_map: Dict[str, str] = {
            "auth": "User Authentication", "login": "User Authentication", "signup": "User Authentication",
            "billing": "Billing Management", "payment": "Billing Management", "invoice": "Billing Management",
            "search": "Search", "filter": "Search",
            "notification": "Notifications", "email": "Notifications", "alert": "Notifications",
            "report": "Reporting", "analytics": "Reporting", "dashboard": "Reporting",
            "workflow": "Workflow", "approval": "Workflow", "pipeline": "Workflow",
            "collaboration": "Collaboration", "share": "Collaboration", "team": "Collaboration",
            "import": "Data Import/Export", "export": "Data Import/Export", "sync": "Data Import/Export",
        }
        added: set[str] = set()
        for keyword, cap_name in keyword_map.items():
            if keyword in lower and cap_name not in added:
                caps.append(Capability(
                    name=cap_name,
                    description=f"Support for {cap_name.lower()}",
                    priority=0.8 if len(caps) == 0 else 0.5,
                ))
                added.add(cap_name)
        if not caps:
            caps.append(Capability(name="Core Function", description="Primary business capability", priority=1.0))
        return caps

    def _infer_quality_priorities(self, archetype: BusinessArchetype) -> Dict[QualityAttribute, float]:
        base = {attr: 0.5 for attr in QualityAttribute}
        saas_like = (
            BusinessArchetype.B2B_SAAS, BusinessArchetype.B2C_SAAS,
            BusinessArchetype.ERP, BusinessArchetype.CRM, BusinessArchetype.FINTECH,
        )
        if archetype in saas_like:
            base[QualityAttribute.SECURITY] = 0.9
            base[QualityAttribute.SCALABILITY] = 0.8
            base[QualityAttribute.RELIABILITY] = 0.85
        elif archetype in (BusinessArchetype.AI_APPLICATION,):
            base[QualityAttribute.PERFORMANCE] = 0.9
            base[QualityAttribute.SCALABILITY] = 0.85
        elif archetype in (BusinessArchetype.MOBILE_APPLICATION,):
            base[QualityAttribute.ACCESSIBILITY] = 0.9
            base[QualityAttribute.COGNITIVE_LOAD] = 0.85
        elif archetype in (BusinessArchetype.HEALTHCARE,):
            base[QualityAttribute.SECURITY] = 0.95
            base[QualityAttribute.OBSERVABILITY] = 0.85
        return base

    def _infer_domain(self, lower: str) -> str:
        domain_keywords = {
            "health": "Healthcare", "patient": "Healthcare", "medical": "Healthcare",
            "financ": "Fintech", "banking": "Fintech", "payment": "Fintech",
            "logistics": "Logistics", "supply chain": "Logistics",
            "educat": "Education", "learning": "Education",
            "retail": "Retail", "ecommerce": "Retail",
        }
        for kw, domain in domain_keywords.items():
            if kw in lower:
                return domain
        return "General"

    def _extract_data_domains(self, lower: str) -> List[DataDomain]:
        return []  # Placeholder for structured extraction

    def _extract_integrations(self, lower: str) -> List[IntegrationPoint]:
        return []  # Placeholder

    def _extract_compliance(self, lower: str) -> List[ComplianceStandard]:
        detected: List[ComplianceStandard] = []
        if "gdpr" in lower:
            detected.append(ComplianceStandard.GDPR)
        if "hipaa" in lower:
            detected.append(ComplianceStandard.HIPAA)
        if "pci" in lower or "payment" in lower:
            detected.append(ComplianceStandard.PCI_DSS)
        if "soc2" in lower:
            detected.append(ComplianceStandard.SOC2)
        if "sox" in lower:
            detected.append(ComplianceStandard.SOX)
        return detected

    def _extract_operational(self, lower: str) -> List[OperationalConstraint]:
        detected: List[OperationalConstraint] = []
        if "offline" in lower:
            detected.append(OperationalConstraint.OFFLINE_FIRST)
        if "multi-region" in lower or "global" in lower:
            detected.append(OperationalConstraint.MULTI_REGION)
        if "realtime" in lower or "real-time" in lower:
            detected.append(OperationalConstraint.REAL_TIME)
        if "multi-tenant" in lower or "multi_tenant" in lower:
            detected.append(OperationalConstraint.MULTI_TENANT)
        if "low latency" in lower:
            detected.append(OperationalConstraint.LOW_LATENCY)
        return detected
