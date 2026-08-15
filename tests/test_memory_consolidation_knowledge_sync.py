"""
Tests for Phase 22.5 memory consolidation and Knowledge Graph sync.
"""

from datetime import timedelta

from civilization.memory_consolidation.engine import MemoryConsolidationEngine
from civilization.memory_consolidation.gateway import (
    InMemoryKnowledgeGraphGateway,
)
from civilization.memory_consolidation.models import (
    MemoryConsolidationPolicy,
    MemoryRecordStatus,
    MemorySensitivity,
    MemorySourceType,
    KGSyncStatus,
)
from civilization.utils import utcnow


def build_engine():
    gateway = InMemoryKnowledgeGraphGateway()

    policy = MemoryConsolidationPolicy(
        default_sensitivity=MemorySensitivity.INTERNAL,
        default_ttl_days=365,
        redact_restricted=True,
        dedupe_enabled=True,
        require_evidence_for_sync=True,
        allow_restricted_sync=False,
    )

    engine = MemoryConsolidationEngine(
        kg_gateway=gateway,
        policy=policy,
    )

    return engine, gateway


def test_ingest_consolidate_sync():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="task_1_decision",
        title="Use event-driven billing notifications",
        summary="Billing notifications will be emitted as domain events.",
        content={
            "decision": "Use event-driven notifications",
            "alternatives": [
                "Polling",
                "Scheduled batch",
            ],
        },
        organization_id="organization_billing",
        subject_type="TASK",
        subject_id="task_1",
        evidence_refs=[
            "task:task_1",
            "decision:billing_notifications",
        ],
        tags=["billing", "events"],
    )

    consolidated = engine.consolidate_record(record.id)

    assert consolidated.status == MemoryRecordStatus.CONSOLIDATED

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SYNCED
    assert result.entity_id is not None
    assert len(gateway.entities) >= 1

    entity_count_before = len(gateway.entities)

    result_again = engine.sync_record(record.id, force=True)

    assert result_again.status == KGSyncStatus.SYNCED
    assert len(gateway.entities) == entity_count_before


def test_duplicate_detection():
    engine, gateway = build_engine()

    first = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="decision_1",
        title="Adopt hexagonal architecture",
        summary="Use hexagonal architecture for billing service.",
        content={
            "decision": "hexagonal",
        },
        organization_id="organization_billing",
        evidence_refs=["task:task_1"],
    )

    second = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="decision_1_copy",
        title="Adopt hexagonal architecture",
        summary="Use hexagonal architecture for billing service.",
        content={
            "decision": "hexagonal",
        },
        organization_id="organization_billing",
        evidence_refs=["task:task_1"],
    )

    engine.consolidate_record(first.id)
    duplicated = engine.consolidate_record(second.id)

    assert duplicated.status == MemoryRecordStatus.DUPLICATE
    assert duplicated.properties["duplicate_of"] == first.id


def test_restricted_memory_is_not_synced():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.OVERSIGHT_ACTION,
        source_id="oversight_1",
        title="Restricted security suspension",
        summary="Organization suspended due to security issue.",
        content={
            "reason": "security violation",
        },
        organization_id="organization_billing",
        evidence_refs=["oversight:oversight_1"],
        sensitivity=MemorySensitivity.RESTRICTED,
    )

    consolidated = engine.consolidate_record(record.id)

    assert consolidated.properties.get("redacted") is True

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SKIPPED_SENSITIVITY
    assert len(gateway.entities) == 0


def test_missing_evidence_blocks_sync():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.RECOMMENDATION,
        source_id="recommendation_1",
        title="Recommend caching",
        summary="Add caching layer.",
        content={},
        organization_id="organization_billing",
        evidence_refs=[],
    )

    engine.consolidate_record(record.id)

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SKIPPED_MISSING_EVIDENCE
    assert len(gateway.entities) == 0


def test_retention_expires_old_records():
    engine, gateway = build_engine()

    old_time = (utcnow() - timedelta(days=10)).isoformat()

    record = engine.ingest_record(
        source_type=MemorySourceType.REPUTATION_EVENT,
        source_id="reputation_old",
        title="Old reputation event",
        summary="Old positive task outcome.",
        content={},
        organization_id="organization_billing",
        evidence_refs=["task:task_old"],
        ttl_days=1,
        occurred_at=old_time,
    )

    engine.consolidate_record(record.id)

    expired_ids = engine.apply_retention()

    assert record.id in expired_ids

    refreshed = engine.records[record.id]

    assert refreshed.status == MemoryRecordStatus.EXPIRED

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SKIPPED_EXPIRED


def test_pii_detection_classifies_sensitivity():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="task_with_pii",
        title="Decision about user data",
        summary="Contains PII: user@example.com",
        content={},
        organization_id="organization_billing",
        evidence_refs=["task:task_pii"],
        sensitivity=MemorySensitivity.INTERNAL,
    )

    consolidated = engine.consolidate_record(record.id)

    assert consolidated.properties["pii_detected"] is True
    assert consolidated.sensitivity == MemorySensitivity.CONFIDENTIAL


def test_consolidate_all_processes_raw_records():
    engine, gateway = build_engine()

    record1 = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="decision_1",
        title="Architecture decision 1",
        content={"decision": "event-driven"},
        organization_id="org_a",
        evidence_refs=["task:t1"],
    )

    record2 = engine.ingest_record(
        source_type=MemorySourceType.RECOMMENDATION,
        source_id="rec_1",
        title="Recommendation 1",
        content={},
        organization_id="org_b",
        evidence_refs=["task:t2"],
    )

    results = engine.consolidate_all()

    assert len(results) == 2
    assert all(r.status == MemoryRecordStatus.CONSOLIDATED for r in results)


def test_expired_record_not_synced():
    engine, gateway = build_engine()

    old_time = (utcnow() - timedelta(days=400)).isoformat()

    record = engine.ingest_record(
        source_type=MemorySourceType.REPUTATION_EVENT,
        source_id="old_event",
        title="Old event",
        content={},
        organization_id="org_a",
        evidence_refs=["task:t1"],
        ttl_days=1,
        occurred_at=old_time,
    )

    engine.consolidate_record(record.id)
    engine.apply_retention()

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SKIPPED_EXPIRED


def test_duplicate_record_not_synced():
    engine, gateway = build_engine()

    first = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="decision_1",
        title="Same decision",
        content={"decision": "same"},
        organization_id="org_a",
        evidence_refs=["task:t1"],
    )

    second = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="decision_2",
        title="Same decision",
        content={"decision": "same"},
        organization_id="org_a",
        evidence_refs=["task:t1"],
    )

    engine.consolidate_record(first.id)
    engine.consolidate_record(second.id)

    result = engine.sync_record(second.id)

    assert result.status == KGSyncStatus.SKIPPED_DUPLICATE


def test_idempotent_sync_already_synced():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="task_1_decision",
        title="Decision",
        summary="A decision.",
        content={},
        organization_id="org_a",
        evidence_refs=["task:t1"],
    )

    engine.consolidate_record(record.id)

    first_result = engine.sync_record(record.id)
    second_result = engine.sync_record(record.id)

    assert first_result.status == KGSyncStatus.SYNCED
    assert second_result.status == KGSyncStatus.ALREADY_SYNCED


def test_redacted_record_can_sync():
    engine, gateway = build_engine()

    record = engine.ingest_record(
        source_type=MemorySourceType.OVERSIGHT_ACTION,
        source_id="oversight_1",
        title="Restricted action",
        summary="Security review.",
        content={},
        organization_id="org_a",
        evidence_refs=["oversight:o1"],
        sensitivity=MemorySensitivity.RESTRICTED,
    )

    engine.consolidate_record(record.id)

    result = engine.sync_record(record.id)

    assert result.status == KGSyncStatus.SKIPPED_SENSITIVITY


def test_memory_report():
    engine, gateway = build_engine()

    engine.ingest_record(
        source_type=MemorySourceType.TASK_DECISION,
        source_id="task_1",
        title="Decision 1",
        content={},
        organization_id="org_a",
        evidence_refs=["task:t1"],
    )

    engine.consolidate_all()

    report = engine.report()

    assert report["record_count"] == 1
    assert report["status_counts"]["CONSOLIDATED"] == 1
    assert "sensitivity_counts" in report
