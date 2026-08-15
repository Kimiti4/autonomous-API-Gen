"""
Tests for Phase 26.3 Knowledge Graph Learning Sync.
"""

from datetime import timedelta

from learning.analytics.engine import AnomalyCorrelationEngine
from learning.analytics.models import AnomalyDetectionPolicy
from learning.engine import ContinuousLearningEngine
from learning.knowledge_sync.engine import KnowledgeSyncEngine
from learning.knowledge_sync.models import (
    KGEntityPayload,
    KGRelationPayload,
    KnowledgeGraphGateway,
)
from learning.models import LearningSignal, LearningSignalType, Severity
from learning.utils import utcnow


class InMemoryKGGateway(KnowledgeGraphGateway):
    def __init__(self):
        self.entities = {}
        self.relations = {}

    def upsert_entity(self, entity: KGEntityPayload):
        self.entities[entity.id] = entity
        return {"id": entity.id, "status": "UPSERTED"}

    def upsert_relation(self, relation: KGRelationPayload):
        self.relations[relation.id] = relation
        return {"id": relation.id, "status": "UPSERTED"}


def test_knowledge_sync_creates_traceable_lineage():
    learning_engine = ContinuousLearningEngine()
    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
        policy=AnomalyDetectionPolicy(
            min_samples=1,
            cluster_window_minutes=60,
            correlation_threshold=0.3,
            min_cluster_signals=2,
        ),
    )

    kg_gateway = InMemoryKGGateway()

    sync_engine = KnowledgeSyncEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        kg_gateway=kg_gateway,
    )

    now = utcnow()

    learning_engine.ingest_signal(
        LearningSignal(
            id="sig_1",
            source="observability",
            subject_ref="billing_service",
            signal_type=LearningSignalType.PERFORMANCE,
            severity=Severity.HIGH,
            metric="p95_latency_ms",
            value=900.0,
            timestamp=now.isoformat(),
        )
    )

    learning_engine.ingest_signal(
        LearningSignal(
            id="sig_2",
            source="incident_manager",
            subject_ref="billing_service",
            signal_type=LearningSignalType.INCIDENT,
            severity=Severity.CRITICAL,
            message="Billing API outage.",
            timestamp=(now + timedelta(minutes=1)).isoformat(),
        )
    )

    analytics_engine.analyze()

    report = sync_engine.sync()

    assert report.signals_synced == 2
    assert report.clusters_synced >= 1
    assert report.insights_synced >= 1
    assert report.entities_upserted > 0
    assert report.relations_upserted > 0

    assert "signal:sig_1" in kg_gateway.entities
    assert "signal:sig_2" in kg_gateway.entities

    cluster_entities = [
        entity
        for entity in kg_gateway.entities.values()
        if entity.entity_type == "INCIDENT_CLUSTER"
    ]
    assert len(cluster_entities) >= 1

    insight_entities = [
        entity
        for entity in kg_gateway.entities.values()
        if entity.entity_type == "LEARNING_INSIGHT"
    ]
    assert len(insight_entities) >= 1

    supports_relations = [
        rel
        for rel in kg_gateway.relations.values()
        if rel.relation_type == "SUPPORTS"
    ]
    assert len(supports_relations) >= 1

    affects_relations = [
        rel
        for rel in kg_gateway.relations.values()
        if rel.relation_type == "AFFECTS"
    ]
    assert len(affects_relations) >= 1


def test_knowledge_sync_is_idempotent():
    learning_engine = ContinuousLearningEngine()
    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
    )
    kg_gateway = InMemoryKGGateway()

    sync_engine = KnowledgeSyncEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        kg_gateway=kg_gateway,
    )

    learning_engine.ingest_signal(
        LearningSignal(
            id="sig_idempotent",
            source="test",
            signal_type=LearningSignalType.USAGE,
            severity=Severity.INFO,
            value=1.0,
        )
    )

    first_report = sync_engine.sync()
    assert first_report.signals_synced == 1

    second_report = sync_engine.sync()
    assert second_report.signals_synced == 0
