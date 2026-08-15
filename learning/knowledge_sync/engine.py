"""
Knowledge Graph synchronization engine.
"""

from __future__ import annotations

from typing import Optional

from ..analytics.engine import AnomalyCorrelationEngine
from ..engine import ContinuousLearningEngine
from .mapper import LearningKnowledgeMapper
from .models import (
    KnowledgeGraphGateway,
    LearningSyncReport,
    SyncRegistry,
)


class KnowledgeSyncEngine:
    """Orchestrates the synchronization of learning evidence to the KG."""

    def __init__(
        self,
        learning_engine: ContinuousLearningEngine,
        analytics_engine: AnomalyCorrelationEngine,
        kg_gateway: KnowledgeGraphGateway,
        mapper: Optional[LearningKnowledgeMapper] = None,
    ) -> None:
        self.learning_engine = learning_engine
        self.analytics_engine = analytics_engine
        self.kg_gateway = kg_gateway
        self.mapper = mapper or LearningKnowledgeMapper()

        self.registry = SyncRegistry()

    def sync(self) -> LearningSyncReport:
        report = LearningSyncReport()

        # 1. Sync Signals
        for signal in self.learning_engine.pipeline.signals:
            if not signal.id or signal.id in self.registry.synced_signal_ids:
                continue

            entity = self.mapper.map_signal(signal)
            self.kg_gateway.upsert_entity(entity)

            self.registry.synced_signal_ids.add(signal.id)
            report.signals_synced += 1
            report.entities_upserted += 1

        # 2. Sync Anomalies
        for anomaly in self.analytics_engine.anomalies.values():
            if anomaly.id in self.registry.synced_anomaly_ids:
                continue

            entity, relation = self.mapper.map_anomaly(anomaly)
            self.kg_gateway.upsert_entity(entity)
            self.kg_gateway.upsert_relation(relation)

            self.registry.synced_anomaly_ids.add(anomaly.id)
            report.anomalies_synced += 1
            report.entities_upserted += 1
            report.relations_upserted += 1

        # 3. Sync Clusters
        for cluster in self.analytics_engine.clusters.values():
            if cluster.id in self.registry.synced_cluster_ids:
                continue

            entity, relations = self.mapper.map_cluster(cluster)
            self.kg_gateway.upsert_entity(entity)

            for relation in relations:
                self.kg_gateway.upsert_relation(relation)
                report.relations_upserted += 1

            self.registry.synced_cluster_ids.add(cluster.id)
            report.clusters_synced += 1
            report.entities_upserted += 1

        # 4. Sync Insights and Objectives
        for insight in self.analytics_engine.insights.values():
            if insight.id in self.registry.synced_insight_ids:
                continue

            entity, relations = self.mapper.map_insight(insight)
            self.kg_gateway.upsert_entity(entity)

            for relation in relations:
                self.kg_gateway.upsert_relation(relation)
                report.relations_upserted += 1

                if relation.relation_type == "AFFECTS":
                    objective_name = relation.target_entity_id.replace(
                        "objective:",
                        "",
                    )

                    if objective_name not in self.registry.synced_objectives:
                        objective_entity = self.mapper.map_objective(
                            objective_name
                        )
                        self.kg_gateway.upsert_entity(objective_entity)
                        self.registry.synced_objectives.add(objective_name)
                        report.entities_upserted += 1

            self.registry.synced_insight_ids.add(insight.id)
            report.insights_synced += 1
            report.entities_upserted += 1

        return report

    def get_registry_state(self) -> SyncRegistry:
        return self.registry
