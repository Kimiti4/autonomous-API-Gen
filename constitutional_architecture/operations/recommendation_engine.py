"""
Recommendation Engine.

Produces evolution, deployment, and requirement recommendations
based on accumulated observations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.incident_engine import IncidentEngine
from constitutional_architecture.operations.observation_model import (
    Incident,
    Observation,
    ObservationClassification,
    Recommendation,
)


class RecommendationEngine:

    def __init__(self, incident_engine: Optional[IncidentEngine] = None) -> None:
        self._incident_engine = incident_engine or IncidentEngine()
        self._recommendations: list[Recommendation] = []

    def generate_recommendations(
        self, observations: list[Observation], incidents: list[Incident],
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        arch_incidents = [
            i for i in incidents
            if i.classification == ObservationClassification.ARCHITECTURAL_DEFICIENCY
        ]
        for incident in arch_incidents:
            recommendations.extend(self._recommend_evolution(incident, observations))

        ops_incidents = [
            i for i in incidents
            if i.classification == ObservationClassification.OPERATIONAL_MISCONFIGURATION
        ]
        for incident in ops_incidents:
            recommendations.extend(self._recommend_deployment(incident))

        req_incidents = [
            i for i in incidents
            if i.classification == ObservationClassification.REQUIREMENT_GAP
        ]
        for incident in req_incidents:
            recommendations.extend(self._recommend_requirement(incident))

        recommendations.extend(self._recommend_knowledge(incidents))

        self._recommendations.extend(recommendations)
        return recommendations

    def _recommend_evolution(
        self, incident: Incident, observations: list[Observation],
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        description = incident.description.lower()

        if "coupling" in description or "dependency" in description:
            mutation_type = "extract_interface"
            title = "Reduce coupling via interface extraction"
        elif "cohesion" in description:
            mutation_type = "merge_services"
            title = "Improve cohesion via service merge"
        elif "scalability" in description or "bottleneck" in description:
            mutation_type = "introduce_cache"
            title = "Address scalability via caching"
        elif "stateful" in description:
            mutation_type = "convert_to_stateless"
            title = "Convert stateful service to stateless"
        else:
            mutation_type = "structural_refactor"
            title = "Architectural refactor recommended"

        recommendations.append(Recommendation(
            id=f"rec-{uuid.uuid4().hex[:12]}",
            category="evolution", title=title,
            description=(
                f"Incident '{incident.title}' suggests architectural improvement. "
                f"{incident.description}"
            ),
            reasoning=incident.classification_reasoning,
            confidence=incident.classification_confidence,
            priority=0 if incident.severity.value == "critical" else 1,
            target_subsystem="evolution_engine",
            target_isr_node_id=incident.isr_hash,
            target_deployment_id=incident.deployment_id,
            observation_ids=incident.observation_ids,
            suggested_mutation_type=mutation_type,
            suggested_action=f"Apply '{mutation_type}' mutation to address incident",
        ))

        return recommendations

    def _recommend_deployment(self, incident: Incident) -> list[Recommendation]:
        return [Recommendation(
            id=f"rec-{uuid.uuid4().hex[:12]}",
            category="deployment", title="Deployment configuration update",
            description=f"Incident '{incident.title}' suggests deployment adjustment",
            reasoning=incident.classification_reasoning,
            confidence=incident.classification_confidence,
            priority=1, target_subsystem="deployment_engine",
            target_deployment_id=incident.deployment_id,
            observation_ids=incident.observation_ids,
            suggested_action="Review and update deployment configuration",
        )]

    def _recommend_requirement(self, incident: Incident) -> list[Recommendation]:
        return [Recommendation(
            id=f"rec-{uuid.uuid4().hex[:12]}",
            category="requirement", title="Requirement gap identified",
            description=f"Incident '{incident.title}' indicates requirement gap",
            reasoning=incident.classification_reasoning,
            confidence=incident.classification_confidence,
            priority=2, target_subsystem="requirement_intelligence",
            observation_ids=incident.observation_ids,
            suggested_action="Review and update IRR to address gap",
        )]

    def _recommend_knowledge(self, incidents: list[Incident]) -> list[Recommendation]:
        from collections import Counter
        classification_counts = Counter(i.classification for i in incidents)

        recommendations: list[Recommendation] = []
        for classification, count in classification_counts.items():
            if count >= 3:
                recommendations.append(Recommendation(
                    id=f"rec-knowledge-{uuid.uuid4().hex[:8]}",
                    category="knowledge",
                    title=f"Recurring pattern: {classification.value}",
                    description=(
                        f"Classification '{classification.value}' occurred {count} times. "
                        f"This pattern should be recorded in the Knowledge Engine."
                    ),
                    reasoning="Recurring pattern indicates systematic issue",
                    confidence=0.8, priority=3,
                    target_subsystem="knowledge_engine",
                    suggested_action=f"Record '{classification.value}' pattern in knowledge base",
                ))

        return recommendations

    @property
    def recommendations(self) -> list[Recommendation]:
        return list(self._recommendations)

    def get_by_category(self, category: str) -> list[Recommendation]:
        return [r for r in self._recommendations if r.category == category]
