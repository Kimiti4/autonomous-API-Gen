"""
Memory consolidation and Knowledge Graph sync engine.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..utils import canonical_json, deterministic_id, sha256_hex, utcnow
from .gateway import KnowledgeGraphGateway
from .models import (
    KGEntityPayload,
    KGRelationPayload,
    KGSyncResult,
    KGSyncStatus,
    MemoryConsolidationPolicy,
    MemoryRecordStatus,
    MemorySensitivity,
    MemorySourceType,
    NormalizedMemoryRecord,
)


MEMORY_SOURCE_TO_ENTITY_TYPE = {
    MemorySourceType.ORGANIZATION_MEMORY: "DOCUMENT",
    MemorySourceType.TASK_DECISION: "DOCUMENT",
    MemorySourceType.RECOMMENDATION: "RECOMMENDATION",
    MemorySourceType.REPUTATION_EVENT: "AUDIT_EVENT",
    MemorySourceType.OVERSIGHT_ACTION: "AUDIT_EVENT",
    MemorySourceType.POLICY_DECISION: "AUDIT_EVENT",
    MemorySourceType.CERTIFICATION: "DOCUMENT",
    MemorySourceType.FEDERATION_DECISION: "DOCUMENT",
    MemorySourceType.CONFLICT_RESOLUTION: "DOCUMENT",
    MemorySourceType.EVOLUTION_EVENT: "AUDIT_EVENT",
    MemorySourceType.PRODUCTION_FEEDBACK: "TELEMETRY_SIGNAL",
}


SUBJECT_TO_ENTITY_TYPE = {
    "ORGANIZATION": "ORGANIZATION",
    "AGENT": "AGENT",
    "FEDERATION": "ORGANIZATION",
    "TASK": "LINEAGE_RECORD",
    "INITIATIVE": "LINEAGE_RECORD",
    "CAMPAIGN": "LINEAGE_RECORD",
    "PROMOTION_REQUEST": "LINEAGE_RECORD",
}


class MemoryConsolidationError(Exception):
    """Base error for memory consolidation operations."""


class MemoryConsolidationEngine:
    """Consolidates organizational memory and syncs it to a Knowledge Graph."""

    def __init__(
        self,
        kg_gateway: KnowledgeGraphGateway,
        policy: Optional[MemoryConsolidationPolicy] = None,
    ) -> None:
        self.kg_gateway = kg_gateway
        self.policy = policy or MemoryConsolidationPolicy()

        self.records: Dict[str, NormalizedMemoryRecord] = {}
        self.sync_results: Dict[str, KGSyncResult] = {}

        self.content_index: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_record(
        self,
        source_type: MemorySourceType,
        source_id: str,
        title: str,
        summary: str = "",
        content: Optional[Dict] = None,
        organization_id: Optional[str] = None,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        sensitivity: Optional[MemorySensitivity] = None,
        ttl_days: Optional[int] = None,
        occurred_at: Optional[str] = None,
    ) -> NormalizedMemoryRecord:
        received_at = utcnow().isoformat()
        occurred = occurred_at or received_at

        content = content or {}
        evidence_refs = evidence_refs or []
        tags = tags or []

        content_hash = sha256_hex(
            canonical_json(
                {
                    "source_type": source_type.value,
                    "organization_id": organization_id,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "evidence_refs": sorted(evidence_refs),
                    "tags": sorted(tags),
                }
            )
        )

        record_id = deterministic_id(
            "memory_record",
            {
                "source_type": source_type.value,
                "source_id": source_id,
                "occurred_at": occurred,
                "received_at": received_at,
                "record_count": len(self.records),
            },
        )

        record = NormalizedMemoryRecord(
            id=record_id,
            source_type=source_type,
            source_id=source_id,
            organization_id=organization_id,
            subject_type=subject_type,
            subject_id=subject_id,
            title=title,
            summary=summary,
            content=content,
            evidence_refs=evidence_refs,
            tags=tags,
            sensitivity=sensitivity or self.policy.default_sensitivity,
            status=MemoryRecordStatus.RAW,
            content_hash=content_hash,
            ttl_days=ttl_days or self.policy.default_ttl_days,
            occurred_at=occurred,
            received_at=received_at,
        )

        self.records[record_id] = record

        return record

    def list_records(
        self,
        status: Optional[MemoryRecordStatus] = None,
        sensitivity: Optional[MemorySensitivity] = None,
        organization_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[NormalizedMemoryRecord]:
        results: List[NormalizedMemoryRecord] = []

        for record in reversed(list(self.records.values())):
            if status and record.status != status:
                continue

            if sensitivity and record.sensitivity != sensitivity:
                continue

            if organization_id and record.organization_id != organization_id:
                continue

            results.append(record)

            if len(results) >= limit:
                break

        return results

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def consolidate_record(self, record_id: str) -> NormalizedMemoryRecord:
        record = self._get_record(record_id)

        if record.status in {
            MemoryRecordStatus.DUPLICATE,
            MemoryRecordStatus.EXPIRED,
        }:
            return record

        self._classify_record(record)

        self._redact_record_if_required(record)

        if self.policy.dedupe_enabled:
            existing_record_id = self.content_index.get(record.content_hash)

            if existing_record_id and existing_record_id != record.id:
                record.status = MemoryRecordStatus.DUPLICATE
                record.properties["duplicate_of"] = existing_record_id
                return record

        self.content_index[record.content_hash] = record.id

        if record.status != MemoryRecordStatus.REDACTED:
            record.status = MemoryRecordStatus.CONSOLIDATED

        return record

    def consolidate_all(self) -> List[NormalizedMemoryRecord]:
        consolidated: List[NormalizedMemoryRecord] = []

        for record in list(self.records.values()):
            if record.status != MemoryRecordStatus.RAW:
                continue

            consolidated.append(self.consolidate_record(record.id))

        return consolidated

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------

    def apply_retention(
        self,
        now: Optional[str] = None,
    ) -> List[str]:
        current_time = self._parse_timestamp(now or utcnow().isoformat())

        expired_ids: List[str] = []

        for record in self.records.values():
            if record.status == MemoryRecordStatus.EXPIRED:
                continue

            if record.ttl_days is None:
                continue

            occurred_at = self._parse_timestamp(record.occurred_at)

            age_days = (current_time - occurred_at).days

            if age_days > record.ttl_days:
                record.status = MemoryRecordStatus.EXPIRED
                record.properties["expired_at"] = current_time.isoformat()
                expired_ids.append(record.id)

        return expired_ids

    # ------------------------------------------------------------------
    # Knowledge Graph sync
    # ------------------------------------------------------------------

    def sync_record(
        self,
        record_id: str,
        force: bool = False,
    ) -> KGSyncResult:
        record = self._get_record(record_id)

        synced_at = utcnow().isoformat()

        if record.status == MemoryRecordStatus.EXPIRED:
            result = KGSyncResult(
                record_id=record_id,
                status=KGSyncStatus.SKIPPED_EXPIRED,
                synced_at=synced_at,
            )

            self.sync_results[record_id] = result

            return result

        if record.status == MemoryRecordStatus.DUPLICATE:
            result = KGSyncResult(
                record_id=record_id,
                status=KGSyncStatus.SKIPPED_DUPLICATE,
                synced_at=synced_at,
            )

            self.sync_results[record_id] = result

            return result

        if not self._sync_allowed_by_sensitivity(record):
            result = KGSyncResult(
                record_id=record_id,
                status=KGSyncStatus.SKIPPED_SENSITIVITY,
                issues=[
                    "Memory sensitivity policy prevents synchronization."
                ],
                synced_at=synced_at,
            )

            self.sync_results[record_id] = result

            return result

        if self.policy.require_evidence_for_sync and not record.evidence_refs:
            result = KGSyncResult(
                record_id=record_id,
                status=KGSyncStatus.SKIPPED_MISSING_EVIDENCE,
                issues=[
                    "Memory record has no evidence references."
                ],
                synced_at=synced_at,
            )

            self.sync_results[record_id] = result

            return result

        if record.status == MemoryRecordStatus.SYNCED and not force:
            previous = self.sync_results.get(record_id)

            if previous:
                result = KGSyncResult(
                    record_id=previous.record_id,
                    status=KGSyncStatus.ALREADY_SYNCED,
                    entity_id=previous.entity_id,
                    relation_ids=previous.relation_ids,
                    issues=previous.issues,
                    synced_at=synced_at,
                )

                self.sync_results[record_id] = result

                return result

        entities, relations = self._build_kg_payloads(record)

        relation_ids: List[str] = []

        memory_entity_id = None

        for entity in entities:
            response = self.kg_gateway.upsert_entity(entity)

            if entity.entity_type == MEMORY_SOURCE_TO_ENTITY_TYPE.get(
                record.source_type,
                "DOCUMENT",
            ):
                memory_entity_id = response.get("id")

        for relation in relations:
            response = self.kg_gateway.upsert_relation(relation)
            relation_ids.append(response.get("id"))

        record.status = MemoryRecordStatus.SYNCED
        record.properties["synced_at"] = synced_at

        result = KGSyncResult(
            record_id=record_id,
            status=KGSyncStatus.SYNCED,
            entity_id=memory_entity_id,
            relation_ids=relation_ids,
            synced_at=synced_at,
        )

        self.sync_results[record_id] = result

        return result

    def sync_all(self, force: bool = False) -> List[KGSyncResult]:
        results: List[KGSyncResult] = []

        for record in list(self.records.values()):
            if record.status not in {
                MemoryRecordStatus.CONSOLIDATED,
                MemoryRecordStatus.SYNCED,
                MemoryRecordStatus.REDACTED,
            }:
                continue

            results.append(self.sync_record(record.id, force=force))

        return results

    def report(self) -> Dict:
        status_counts: Dict[str, int] = {}
        sensitivity_counts: Dict[str, int] = {}

        for record in self.records.values():
            status_counts[record.status.value] = (
                status_counts.get(record.status.value, 0) + 1
            )

            sensitivity_counts[record.sensitivity.value] = (
                sensitivity_counts.get(record.sensitivity.value, 0) + 1
            )

        kg_entity_count = 0
        kg_relation_count = 0

        if hasattr(self.kg_gateway, "entities"):
            kg_entity_count = len(self.kg_gateway.entities)

        if hasattr(self.kg_gateway, "relations"):
            kg_relation_count = len(self.kg_gateway.relations)

        return {
            "generated_at": utcnow().isoformat(),
            "record_count": len(self.records),
            "status_counts": status_counts,
            "sensitivity_counts": sensitivity_counts,
            "sync_result_count": len(self.sync_results),
            "knowledge_graph_entity_count": kg_entity_count,
            "knowledge_graph_relation_count": kg_relation_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_record(self, record_id: str) -> NormalizedMemoryRecord:
        record = self.records.get(record_id)

        if not record:
            raise MemoryConsolidationError(
                f"Memory record not found: {record_id}"
            )

        return record

    def _classify_record(self, record: NormalizedMemoryRecord) -> None:
        pii_detected = self._detect_pii(record)

        record.properties["pii_detected"] = pii_detected

        if pii_detected and record.sensitivity in {
            MemorySensitivity.PUBLIC,
            MemorySensitivity.INTERNAL,
        }:
            record.sensitivity = MemorySensitivity.CONFIDENTIAL

        record.properties["classified_at"] = utcnow().isoformat()

    def _redact_record_if_required(
        self,
        record: NormalizedMemoryRecord,
    ) -> None:
        if not self.policy.redact_restricted:
            return

        if record.sensitivity != MemorySensitivity.RESTRICTED:
            return

        record.summary = "[REDACTED]"
        record.content = {
            "redacted": True,
            "reason": "RESTRICTED memory redacted by consolidation policy.",
        }

        record.properties["redacted"] = True
        record.properties["redacted_at"] = utcnow().isoformat()

        record.status = MemoryRecordStatus.REDACTED

    def _detect_pii(self, record: NormalizedMemoryRecord) -> bool:
        searchable_text = " ".join(
            [
                record.title,
                record.summary,
                canonical_json(record.content),
            ]
        ).lower()

        if "pii" in searchable_text:
            return True

        email_pattern = r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"

        if re.search(email_pattern, searchable_text):
            return True

        return False

    def _sync_allowed_by_sensitivity(
        self,
        record: NormalizedMemoryRecord,
    ) -> bool:
        if record.sensitivity == MemorySensitivity.RESTRICTED:
            return self.policy.allow_restricted_sync

        return record.sensitivity in self.policy.allowed_sync_sensitivities

    def _build_kg_payloads(
        self,
        record: NormalizedMemoryRecord,
    ) -> tuple[List[KGEntityPayload], List[KGRelationPayload]]:
        entities: List[KGEntityPayload] = []
        relations: List[KGRelationPayload] = []

        entity_type = MEMORY_SOURCE_TO_ENTITY_TYPE.get(
            record.source_type,
            "DOCUMENT",
        )

        namespace = f"civilization:{record.organization_id or 'global'}"

        memory_entity_id = deterministic_id(
            "kg_memory_entity",
            {
                "record_id": record.id,
                "entity_type": entity_type,
                "namespace": namespace,
            },
        )

        properties = {
            "memory_record_id": record.id,
            "source_type": record.source_type.value,
            "source_id": record.source_id,
            "sensitivity": record.sensitivity.value,
            "tags": record.tags,
            "occurred_at": record.occurred_at,
            "received_at": record.received_at,
        }

        if record.properties.get("redacted") is not True:
            properties["content"] = record.content

        memory_entity = KGEntityPayload(
            id=memory_entity_id,
            entity_type=entity_type,
            name=record.title,
            namespace=namespace,
            description=record.summary,
            properties=properties,
            source_refs=[f"memory:{record.id}", *record.evidence_refs],
        )

        entities.append(memory_entity)

        if record.organization_id:
            organization_entity_id = deterministic_id(
                "kg_organization_entity",
                {
                    "organization_id": record.organization_id,
                },
            )

            organization_entity = KGEntityPayload(
                id=organization_entity_id,
                entity_type="ORGANIZATION",
                name=record.organization_id,
                namespace="civilization",
                description="Engineering organization.",
                properties={
                    "organization_id": record.organization_id,
                },
                source_refs=[
                    f"organization:{record.organization_id}",
                ],
            )

            entities.append(organization_entity)

            organization_relation_id = deterministic_id(
                "kg_memory_organization_relation",
                {
                    "memory_entity_id": memory_entity_id,
                    "organization_entity_id": organization_entity_id,
                },
            )

            relations.append(
                KGRelationPayload(
                    id=organization_relation_id,
                    relation_type="OWNED_BY",
                    source_entity_id=memory_entity_id,
                    target_entity_id=organization_entity_id,
                    source_refs=[f"memory:{record.id}"],
                )
            )

        if record.subject_type and record.subject_id:
            subject_entity_type = SUBJECT_TO_ENTITY_TYPE.get(
                record.subject_type,
                "LINEAGE_RECORD",
            )

            subject_entity_id = deterministic_id(
                "kg_subject_entity",
                {
                    "subject_type": record.subject_type,
                    "subject_id": record.subject_id,
                },
            )

            subject_entity = KGEntityPayload(
                id=subject_entity_id,
                entity_type=subject_entity_type,
                name=record.subject_id,
                namespace="civilization",
                description="Memory subject reference.",
                properties={
                    "subject_type": record.subject_type,
                    "subject_id": record.subject_id,
                },
                source_refs=[
                    f"{record.subject_type.lower()}:{record.subject_id}",
                ],
            )

            entities.append(subject_entity)

            subject_relation_id = deterministic_id(
                "kg_memory_subject_relation",
                {
                    "memory_entity_id": memory_entity_id,
                    "subject_entity_id": subject_entity_id,
                },
            )

            relations.append(
                KGRelationPayload(
                    id=subject_relation_id,
                    relation_type="TRACES_TO",
                    source_entity_id=memory_entity_id,
                    target_entity_id=subject_entity_id,
                    source_refs=[f"memory:{record.id}"],
                )
            )

        return entities, relations

    def _parse_timestamp(self, value: str):
        from datetime import datetime, timezone

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utcnow()

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
