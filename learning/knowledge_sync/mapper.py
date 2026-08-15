"""
Maps learning artifacts to Knowledge Graph payloads.
"""

from __future__ import annotations

from typing import List, Tuple

from ..analytics.models import AnomalyRecord, IncidentCluster
from ..models import LearningInsight, LearningSignal
from ..utils import deterministic_id
from .models import (
    KGEntityPayload,
    KGEntityType,
    KGRelationPayload,
    KGRelationType,
)


class LearningKnowledgeMapper:
    """Converts learning models into Knowledge Graph entities and relations."""

    def map_signal(self, signal: LearningSignal) -> KGEntityPayload:
        return KGEntityPayload(
            id=f"signal:{signal.id}",
            entity_type=KGEntityType.TELEMETRY_SIGNAL.value,
            name=signal.metric or signal.signal_type.value,
            properties={
                "signal_type": signal.signal_type.value,
                "severity": signal.severity.value,
                "value": signal.value,
                "subject_ref": signal.subject_ref,
                "timestamp": signal.timestamp,
            },
            source_refs=[f"signal:{signal.id}"],
        )

    def map_anomaly(
        self,
        anomaly: AnomalyRecord,
    ) -> Tuple[KGEntityPayload, KGRelationPayload]:
        entity = KGEntityPayload(
            id=f"anomaly:{anomaly.id}",
            entity_type=KGEntityType.ANOMALY.value,
            name=anomaly.detection_method,
            properties={
                "score": anomaly.anomaly_score,
                "severity": anomaly.severity.value,
                "baseline_mean": anomaly.baseline_mean,
                "timestamp": anomaly.timestamp,
            },
            source_refs=[f"anomaly:{anomaly.id}"],
        )

        relation = KGRelationPayload(
            id=deterministic_id(
                "rel",
                {
                    "source": entity.id,
                    "target": f"signal:{anomaly.signal_id}",
                    "type": KGRelationType.DERIVED_FROM.value,
                },
            ),
            relation_type=KGRelationType.DERIVED_FROM.value,
            source_entity_id=entity.id,
            target_entity_id=f"signal:{anomaly.signal_id}",
        )

        return entity, relation

    def map_cluster(
        self,
        cluster: IncidentCluster,
    ) -> Tuple[KGEntityPayload, List[KGRelationPayload]]:
        entity = KGEntityPayload(
            id=f"cluster:{cluster.id}",
            entity_type=KGEntityType.INCIDENT_CLUSTER.value,
            name="Correlated Incident Cluster",
            properties={
                "confidence": cluster.confidence,
                "severity": cluster.severity.value,
                "affected_subjects": cluster.affected_subjects,
                "objectives": cluster.objectives,
            },
            source_refs=[f"cluster:{cluster.id}"],
        )

        relations: List[KGRelationPayload] = []

        for signal_id in cluster.signal_ids:
            relations.append(
                KGRelationPayload(
                    id=deterministic_id(
                        "rel",
                        {
                            "source": f"signal:{signal_id}",
                            "target": entity.id,
                            "type": KGRelationType.GROUPED_INTO.value,
                        },
                    ),
                    relation_type=KGRelationType.GROUPED_INTO.value,
                    source_entity_id=f"signal:{signal_id}",
                    target_entity_id=entity.id,
                )
            )

        for candidate in cluster.root_cause_candidates:
            relations.append(
                KGRelationPayload(
                    id=deterministic_id(
                        "rel",
                        {
                            "source": f"signal:{candidate.signal_id}",
                            "target": entity.id,
                            "type": KGRelationType.ROOT_CAUSE_OF.value,
                        },
                    ),
                    relation_type=KGRelationType.ROOT_CAUSE_OF.value,
                    source_entity_id=f"signal:{candidate.signal_id}",
                    target_entity_id=entity.id,
                    properties={"score": candidate.score},
                )
            )

        return entity, relations

    def map_insight(
        self,
        insight: LearningInsight,
    ) -> Tuple[KGEntityPayload, List[KGRelationPayload]]:
        entity = KGEntityPayload(
            id=f"insight:{insight.id}",
            entity_type=KGEntityType.LEARNING_INSIGHT.value,
            name=insight.title,
            properties={
                "severity": insight.severity.value,
                "confidence": insight.confidence,
                "recommendations": insight.recommendations,
            },
            source_refs=[f"insight:{insight.id}"],
        )

        relations: List[KGRelationPayload] = []

        for signal_id in insight.signal_ids:
            relations.append(
                KGRelationPayload(
                    id=deterministic_id(
                        "rel",
                        {
                            "source": f"signal:{signal_id}",
                            "target": entity.id,
                            "type": KGRelationType.SUPPORTS.value,
                        },
                    ),
                    relation_type=KGRelationType.SUPPORTS.value,
                    source_entity_id=f"signal:{signal_id}",
                    target_entity_id=entity.id,
                )
            )

        for objective in insight.objectives:
            relations.append(
                KGRelationPayload(
                    id=deterministic_id(
                        "rel",
                        {
                            "source": entity.id,
                            "target": f"objective:{objective}",
                            "type": KGRelationType.AFFECTS.value,
                        },
                    ),
                    relation_type=KGRelationType.AFFECTS.value,
                    source_entity_id=entity.id,
                    target_entity_id=f"objective:{objective}",
                )
            )

        return entity, relations

    def map_objective(self, objective: str) -> KGEntityPayload:
        return KGEntityPayload(
            id=f"objective:{objective}",
            entity_type=KGEntityType.FITNESS_OBJECTIVE.value,
            name=objective,
            properties={},
            source_refs=[f"objective:{objective}"],
        )
