"""Knowledge overview + memory projections (pure functions).

Read-only derived state over recorded knowledge/memory events. This view
is not a source of truth: it renders what was recorded, with epistemic
states preserved exactly as observed. The ISR remains constitutional.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event, EventCategory
from .projections import (
    collect_evidence_refs,
    collect_payload_list,
    count_epistemic,
    latest_event,
    payload_get,
    sort_asc,
)

KNOWLEDGE_EVENT_PREFIXES = (
    "knowledge_",
    "memory_",
    "fact_",
    "unknown_",
    "contradiction_",
)

DECISION_TYPES = {
    "decision_recorded",
    "evolution_decision",
    "evolution_advanced",
    "evolution_held",
    "evolution_blocked",
}

MEMORY_EVENT_TYPES = {
    "memory_recorded",
    "memory_updated",
}


def _merge_unique(*lists: List[str]) -> List[str]:
    merged = set()
    for values in lists:
        for value in values:
            if value is None:
                continue
            merged.add(str(value))
    return sorted(merged)


def _first_str(payload: Dict[str, Any], keys: tuple,
               default: Optional[str] = None) -> Optional[str]:
    for key in keys:
        value = payload_get(payload, key)
        if value is not None:
            return str(value)
    return default


def extract_knowledge_subject_id(event: Event) -> Optional[str]:
    for key in ("knowledge_id", "memory_id", "topic_id", "concept_id"):
        value = payload_get(event.payload, key)
        if value is not None:
            return str(value)
    if event.category in {EventCategory.KNOWLEDGE, EventCategory.EVIDENCE}:
        return str(event.subject_id)
    if event.type.startswith(KNOWLEDGE_EVENT_PREFIXES):
        return str(event.subject_id)
    subject = str(event.subject_id)
    if subject.startswith("KNOW-") or subject.startswith("MEM-"):
        return subject
    return None


def build_knowledge_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in events:
        subject_id = extract_knowledge_subject_id(event)
        if subject_id is None:
            continue
        grouped.setdefault(subject_id, []).append(event)
    summaries: List[Dict[str, Any]] = []
    for subject_id, subject_events in grouped.items():
        sorted_events = sort_asc(subject_events)
        latest = latest_event(sorted_events)
        if latest is None:
            continue
        status = payload_get(latest.payload, "status",
                             latest.epistemic_status.value)
        summary = _first_str(
            latest.payload, ("summary", "statement", "claim", "question"),
            default=f"{latest.type}: {subject_id}")
        categories = sorted({event.category.value for event in sorted_events})
        summaries.append({
            "subject_id": subject_id,
            "status": str(status),
            "summary": str(summary),
            "epistemic_state": count_epistemic(sorted_events),
            "categories": categories,
            "evidence_count": len(collect_evidence_refs(sorted_events)),
            "updated_at": latest.timestamp,
        })
    return sorted(summaries, key=lambda item: item["subject_id"])


def build_knowledge_memory(subject_id: str,
                           events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = [event for event in events
                if extract_knowledge_subject_id(event) == subject_id
                or event.subject_id == subject_id]
    if not relevant:
        return None
    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)
    if latest is None:
        return None
    status = payload_get(latest.payload, "status",
                         latest.epistemic_status.value)
    facts: List[Dict[str, Any]] = []
    unknowns: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []
    memories: List[Dict[str, Any]] = []
    for event in relevant_sorted:
        statement = _first_str(
            event.payload, ("statement", "claim", "summary"),
            default=f"{event.type}: {event.subject_id}")
        is_knowledge_like = (
            event.category in {EventCategory.KNOWLEDGE, EventCategory.EVIDENCE}
            or event.type.startswith(KNOWLEDGE_EVENT_PREFIXES)
            or payload_get(event.payload, "statement") is not None
            or payload_get(event.payload, "claim") is not None)
        if is_knowledge_like and event.epistemic_status in {
                EpistemicStatus.OBSERVED, EpistemicStatus.INFERRED}:
            facts.append({
                "fact_id": event.id,
                "statement": str(statement),
                "epistemic_status": event.epistemic_status.value,
                "evidence_refs": list(event.evidence_refs),
                "timestamp": event.timestamp,
                "source": event.source,
                "severity": event.severity.value,
            })
        if (event.epistemic_status == EpistemicStatus.UNKNOWN
                or event.type.startswith("unknown_")):
            unknowns.append({
                "unknown_id": str(payload_get(event.payload, "unknown_id",
                                              event.id)),
                "question": str(_first_str(
                    event.payload,
                    ("question", "unknown", "statement", "summary"),
                    default=statement)),
                "reason": str(payload_get(event.payload, "reason", "unknown")),
                "timestamp": event.timestamp,
            })
        if (event.epistemic_status == EpistemicStatus.CONTRADICTION
                or event.type.startswith("contradiction_")):
            contradictions.append({
                "contradiction_id": str(payload_get(
                    event.payload, "contradiction_id", event.id)),
                "statement": str(statement),
                "left_evidence_id": payload_get(event.payload,
                                                "left_evidence_id"),
                "right_evidence_id": payload_get(event.payload,
                                                 "right_evidence_id"),
                "timestamp": event.timestamp,
            })
        if event.type in MEMORY_EVENT_TYPES or event.type.startswith("memory_"):
            memories.append({
                "memory_id": event.id,
                "timestamp": event.timestamp,
                "summary": str(_first_str(
                    event.payload, ("summary", "statement"),
                    default=f"{event.type}: {event.subject_id}")),
                "memory": payload_get(event.payload, "memory"),
            })
    decision_events = [
        event for event in relevant_sorted
        if event.category == EventCategory.GOVERNANCE
        and event.type in DECISION_TYPES]
    decisions = _merge_unique(
        collect_payload_list(decision_events, "decision_id"),
        [event.id for event in decision_events])
    evidence_refs = _merge_unique(
        collect_evidence_refs(relevant_sorted),
        collect_payload_list(relevant_sorted, "evidence_id"),
        collect_payload_list(relevant_sorted, "evidence_refs"))
    timeline = [{
        "event_id": event.id,
        "timestamp": event.timestamp,
        "category": event.category.value,
        "type": event.type,
        "subject_id": event.subject_id,
        "epistemic_status": event.epistemic_status.value,
        "severity": event.severity.value,
        "summary": str(payload_get(event.payload, "summary",
                                   f"{event.type}: {event.subject_id}")),
    } for event in reversed(relevant_sorted)]
    return {
        "subject_id": subject_id,
        "status": str(status),
        "epistemic_state": count_epistemic(relevant_sorted),
        "facts": facts, "unknowns": unknowns,
        "contradictions": contradictions, "memories": memories,
        "evidence_refs": evidence_refs, "decisions": decisions,
        "timeline": timeline, "provenance": latest.provenance,
        "sources": sorted({event.source for event in relevant_sorted}),
        "first_observed_at": relevant_sorted[0].timestamp,
        "updated_at": latest.timestamp,
    }
