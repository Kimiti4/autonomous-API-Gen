"""
Incident Engine.

Classifies and routes operational incidents.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.classification import ObservationClassifier
from constitutional_architecture.operations.observation_model import (
    Incident,
    Observation,
    ObservationClassification,
    ObservationSeverity,
)


class IncidentEngine:

    def __init__(self, classifier: Optional[ObservationClassifier] = None) -> None:
        self._classifier = classifier or ObservationClassifier()
        self._incidents: list[Incident] = []
        self._open_incidents: dict[str, Incident] = {}

    def create_incident(self, observations: list[Observation]) -> Incident:
        if not observations:
            raise ValueError("Cannot create incident from empty observations")

        severity_order = {
            ObservationSeverity.INFO: 0,
            ObservationSeverity.WARNING: 1,
            ObservationSeverity.ERROR: 2,
            ObservationSeverity.CRITICAL: 3,
        }
        severity = max(observations, key=lambda o: severity_order[o.severity]).severity

        classifications = [o.classification for o in observations if o.classification != ObservationClassification.UNKNOWN]
        if classifications:
            from collections import Counter
            classification = Counter(classifications).most_common(1)[0][0]
            confidence = 0.8
            reasoning = f"Most common classification among {len(classifications)} observations"
        else:
            most_severe = max(observations, key=lambda o: severity_order[o.severity])
            result = self._classifier.classify(most_severe)
            classification = result.classification
            confidence = result.confidence
            reasoning = result.reasoning

        incident = Incident(
            id=f"incident-{uuid.uuid4().hex[:12]}",
            severity=severity,
            title=f"Incident: {observations[0].title}",
            description=(
                f"Incident composed of {len(observations)} observation(s). "
                f"Primary: {observations[0].description}"
            ),
            classification=classification,
            classification_confidence=confidence,
            classification_reasoning=reasoning,
            affected_services=tuple(set(o.service_name for o in observations if o.service_name)),
            deployment_id=observations[0].deployment_id,
            isr_hash=observations[0].isr_hash,
            observation_ids=tuple(o.id for o in observations),
            status="open",
        )

        self._incidents.append(incident)
        self._open_incidents[incident.id] = incident
        return incident

    def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        lessons_learned: str = "",
    ) -> Optional[Incident]:
        incident = self._open_incidents.get(incident_id)
        if incident is None:
            return None

        resolved = Incident(
            id=incident.id, timestamp=incident.timestamp,
            severity=incident.severity, title=incident.title,
            description=incident.description,
            classification=incident.classification,
            classification_confidence=incident.classification_confidence,
            classification_reasoning=incident.classification_reasoning,
            affected_services=incident.affected_services,
            affected_users=incident.affected_users,
            duration_seconds=incident.duration_seconds,
            estimated_cost=incident.estimated_cost,
            deployment_id=incident.deployment_id,
            isr_hash=incident.isr_hash,
            observation_ids=incident.observation_ids,
            status="resolved",
            resolution=resolution,
            lessons_learned=lessons_learned,
            metadata=incident.metadata,
        )

        self._incidents = [
            resolved if i.id == incident_id else i
            for i in self._incidents
        ]
        del self._open_incidents[incident_id]
        return resolved

    @property
    def open_incidents(self) -> list[Incident]:
        return list(self._open_incidents.values())

    @property
    def all_incidents(self) -> list[Incident]:
        return list(self._incidents)

    def get_by_classification(
        self, classification: ObservationClassification
    ) -> list[Incident]:
        return [i for i in self._incidents if i.classification == classification]
