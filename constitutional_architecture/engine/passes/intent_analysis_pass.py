from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from constitutional_architecture.core.models.intent import (
    BusinessArchetype, IntentModel, QualityAttribute,
    sanitize_forbidden_terms,
)


@dataclass
class IntentAnalysisResult:
    model: IntentModel
    pass_1_validation_issues: List[str] = field(default_factory=list)
    sanitized_terms: List[str] = field(default_factory=list)
    confidence: float = 1.0
    analysis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExtractedIntent:
    problem_statement: str
    target_personas: List[str]
    core_capabilities: List[str]
    business_archetype: BusinessArchetype
    quality_priorities: Optional[Dict[QualityAttribute, float]] = None
    regulatory_constraints: Optional[List[str]] = None
    operational_constraints: Optional[List[str]] = None


class IIntentAnalyzer(ABC):
    """Pass 2: Intent Analysis interface.

    Transforms validated raw input into a technology-neutral IntentModel.
    Every implementation MUST run sanitize_forbidden_terms() on text fields
    before constructing the IntentModel.
    """

    @abstractmethod
    def analyze(self, raw_input: str, **kwargs: Any) -> IntentAnalysisResult:
        ...


class DeterministicIntentAnalyzer(IIntentAnalyzer):
    """Keyword-pattern-based Intent Analyzer.

    Extracts structured intent from plain text using regex/heuristics.
    Does NOT use an LLM — fully deterministic for auditability.
    """

    ARCHETYPE_KEYWORDS: dict[BusinessArchetype, list[str]] = {
        BusinessArchetype.B2B_SAAS: [
            "saas", "subscription", "multi-tenant", "b2b", "enterprise",
            "business software", "tenant", "workspace", "organization",
        ],
        BusinessArchetype.MARKETPLACE: [
            "marketplace", "buyer", "seller", "listing", "vendor",
            "transaction", "classified", "exchange",
        ],
        BusinessArchetype.INTERNAL_TOOL: [
            "internal", "admin panel", "back-office", "dashboard",
            "employee", "workflow", "approval", "operation",
        ],
        BusinessArchetype.E_COMMERCE: [
            "ecommerce", "e-commerce", "shop", "store", "product",
            "cart", "checkout", "inventory", "order", "payment",
        ],
        BusinessArchetype.DATA_DASHBOARD: [
            "dashboard", "analytics", "report", "metric", "kpi",
            "visualization", "monitoring", "insight", "chart",
        ],
    }

    CAPABILITY_KEYWORDS: dict[str, list[str]] = {
        "user_authentication": ["login", "signup", "auth", "authentication", "oauth", "sso"],
        "billing_management": ["billing", "payment", "invoice", "subscription", "pricing", "plan"],
        "user_management": ["user management", "profile", "account", "role", "permission"],
        "content_management": ["cms", "content", "article", "blog", "document", "media"],
        "notification": ["notification", "email", "alert", "push", "message"],
        "search": ["search", "filter", "query", "discovery", "find"],
        "reporting": ["report", "analytics", "dashboard", "kpi", "metric"],
        "data_import_export": ["import", "export", "csv", "sync", "migration", "backup"],
        "workflow": ["workflow", "approval", "pipeline", "automation", "orchestration"],
        "collaboration": ["collaboration", "share", "comment", "team", "real-time"],
    }

    PERSONA_KEYWORDS: dict[str, list[str]] = {
        "end_user": ["user", "customer", "visitor", "consumer"],
        "admin": ["admin", "administrator", "operator", "manager"],
        "developer": ["developer", "engineer", "technical", "api"],
        "analyst": ["analyst", "data scientist", "business user", "reporter"],
    }

    QUALITY_KEYWORDS: dict[QualityAttribute, list[str]] = {
        QualityAttribute.SECURITY: ["security", "secure", "encrypt", "auth", "gdpr", "hipaa"],
        QualityAttribute.SCALABILITY: ["scale", "scalable", "high traffic", "performance", "concurrent"],
        QualityAttribute.MAINTAINABILITY: ["maintainable", "clean", "modular", "extensible", "testable"],
        QualityAttribute.PERFORMANCE: ["fast", "performant", "low latency", "speed", "response time"],
        QualityAttribute.ACCESSIBILITY: ["accessible", "a11y", "wcag", "screen reader", "inclusive"],
        QualityAttribute.COGNITIVE_LOAD: ["intuitive", "simple", "easy to use", "ux", "user experience"],
    }

    def analyze(self, raw_input: str, **kwargs: Any) -> IntentAnalysisResult:
        sanitized_terms: list[str] = []
        text_before = raw_input.lower()
        text_after = sanitize_forbidden_terms(raw_input)
        if text_before != text_after.lower():
            changed = set(text_before.split()) & set(text_after.lower().split())
            sanitized_terms = list(changed)

        extracted = self._extract(text_after)
        model = IntentModel(
            problem_statement=extracted.problem_statement,
            target_personas=extracted.target_personas,
            core_capabilities=extracted.core_capabilities,
            quality_priorities=extracted.quality_priorities or {},
            business_archetype=extracted.business_archetype,
            regulatory_constraints=extracted.regulatory_constraints or [],
            operational_constraints=extracted.operational_constraints or [],
        )

        return IntentAnalysisResult(
            model=model,
            sanitized_terms=sanitized_terms,
        )

    def _extract(self, text: str) -> ExtractedIntent:
        text_lower = text.lower()
        problem = text.strip()

        archetype = self._detect_archetype(text_lower)
        capabilities = self._detect_capabilities(text_lower)
        personas = self._detect_personas(text_lower)
        quality_priorities = self._detect_quality_priorities(text_lower)
        regulatory = self._detect_regulatory(text_lower)
        operational = self._detect_operational(text_lower)

        return ExtractedIntent(
            problem_statement=problem,
            target_personas=personas or ["end_user"],
            core_capabilities=capabilities or ["user_authentication"],
            business_archetype=archetype,
            quality_priorities=quality_priorities,
            regulatory_constraints=regulatory,
            operational_constraints=operational,
        )

    def _detect_archetype(self, text: str) -> BusinessArchetype:
        scores: dict[BusinessArchetype, int] = {}
        for archetype, keywords in self.ARCHETYPE_KEYWORDS.items():
            scores[archetype] = sum(1 for kw in keywords if kw in text)
        if not scores or all(v == 0 for v in scores.values()):
            return BusinessArchetype.B2B_SAAS
        return max(scores, key=scores.get)

    def _detect_capabilities(self, text: str) -> list[str]:
        detected: list[str] = []
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(capability)
        return detected

    def _detect_personas(self, text: str) -> list[str]:
        detected: list[str] = []
        for persona, keywords in self.PERSONA_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(persona)
        return detected

    def _detect_quality_priorities(self, text: str) -> dict[QualityAttribute, float]:
        priorities: dict[QualityAttribute, float] = {attr: 0.3 for attr in QualityAttribute}
        for attr, keywords in self.QUALITY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                priorities[attr] = min(1.0, 0.3 + matches * 0.15)
        return priorities

    def _detect_regulatory(self, text: str) -> list[str]:
        keywords = {
            "gdpr": "GDPR", "hipaa": "HIPAA", "pci": "PCI-DSS",
            "sox": "SOX", "ccpa": "CCPA", "soc2": "SOC2",
            "iso27001": "ISO-27001",
        }
        text_lower = text.lower()
        return [keywords[kw] for kw, name in keywords.items() if kw in text_lower]

    def _detect_operational(self, text: str) -> list[str]:
        keywords = {
            "offline": "Offline-first",
            "realtime": "Real-time",
            "multi-region": "Multi-region",
            "global": "Global deployment",
            "high availability": "High availability",
            "disaster recovery": "Disaster recovery",
        }
        text_lower = text.lower()
        return [desc for kw, desc in keywords.items() if kw in text_lower]
