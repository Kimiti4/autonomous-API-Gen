"""Provenance overview + audit projections (pure functions).

Read-only derived state over recorded references. This view never rewrites
provenance, never repairs broken references, and never certifies trust:
the derived hash chain is recomputed from stored event hashes at read
time, and any gap or warning renders as such.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event, EventCategory, Severity, event_hash
from .projections import (
    collect_evidence_refs,
    count_epistemic,
    latest_event,
    payload_get,
    sort_asc,
)

REFERENCE_FIELDS = {
    "requirement_id": "requirement",
    "objective_id": "requirement",
    "capability_id": "capability",
    "evolution_id": "evolution",
    "experiment_id": "experiment",
    "fitness_id": "fitness",
    "genome_id": "genome",
    "candidate_id": "candidate",
    "decision_id": "decision",
    "selection_id": "decision",
    "authorization_id": "authorization",
    "evidence_id": "evidence",
    "deployment_id": "deployment",
    "implementation_id": "implementation",
    "run_id": "run",
    "knowledge_id": "knowledge",
    "memory_id": "memory",
    "command_id": "command",
    "request_id": "command",
}

LIST_REFERENCE_FIELDS = {
    "parent_genome_ids": "genome",
    "source_genome_ids": "genome",
    "evidence_refs": "evidence",
    "candidates": "candidate",
    "unknowns_accepted": "unknown",
    "unknowns_rejected": "unknown",
    "contradictions_blocking": "contradiction",
    "requirement_links": "requirement",
    "genome_links": "genome",
    "fitness_links": "fitness",
    "experiment_links": "experiment",
}

WARNING_EVENT_TYPES = {
    "command_rejected",
    "authorization_rejected",
    "decision_rejected",
    "decision_blocked",
    "selection_blocked",
    "safe_mode_enabled",
    "integrity_check_failed",
    "provenance_warning",
}


def _first_str(payload: Dict[str, Any], keys: tuple,
               default: Optional[str] = None) -> Optional[str]:
    for key in keys:
        value = payload_get(payload, key)
        if value is not None:
            return str(value)
    return default


def extract_references(event: Event) -> List[Dict[str, str]]:
    references: List[Dict[str, str]] = []
    seen = set()

    def add_reference(target: Any, relation: str, field: str) -> None:
        if target is None:
            return
        normalized_target = str(target)
        key = (normalized_target, relation, field)
        if key in seen:
            return
        seen.add(key)
        references.append({"target": normalized_target,
                           "relation": relation, "field": field})

    for field, relation in REFERENCE_FIELDS.items():
        add_reference(payload_get(event.payload, field), relation, field)
    for field, relation in LIST_REFERENCE_FIELDS.items():
        value = payload_get(event.payload, field)
        if value is None:
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, dict):
                target = (item.get("candidate_id") or item.get("id")
                          or item.get("unknown_id")
                          or item.get("contradiction_id")
                          or item.get("evidence_id"))
            else:
                target = item
            add_reference(target, relation, field)
    for evidence_reference in event.evidence_refs:
        add_reference(evidence_reference, "evidence_ref",
                      "event.evidence_refs")
    return references


def classify_entity(entity_id: str,
                    grouped_events: Optional[Dict[str, List[Event]]] = None
                    ) -> str:
    if grouped_events is not None:
        events = grouped_events.get(entity_id, [])
        if events:
            categories = {event.category for event in events}
            if EventCategory.GOVERNANCE in categories:
                return "governance"
            if EventCategory.EVIDENCE in categories:
                return "evidence"
            if EventCategory.EVOLUTION in categories:
                return "evolution"
            if EventCategory.KNOWLEDGE in categories:
                return "knowledge"
            if EventCategory.RUNTIME in categories:
                return "runtime"
    normalized = entity_id.strip().upper()
    if normalized.startswith("REQ-"):
        return "requirement"
    if normalized.startswith("CAP-"):
        return "capability"
    if normalized.startswith("EXP-"):
        return "experiment"
    if normalized.startswith("EV-"):
        return "evolution"
    if normalized.startswith("FIT-"):
        return "fitness"
    if normalized.startswith("GENE-"):
        return "gene"
    if normalized.startswith(("GEN-", "GENOME-")):
        return "genome"
    if normalized.startswith(("DEC-", "SEL-", "AUTH-", "GATE-")):
        return "decision"
    if normalized.startswith("EVD-"):
        return "evidence"
    if normalized.startswith(("KNOW-", "MEM-")):
        return "knowledge"
    if normalized.startswith("CMD-"):
        return "command"
    return "entity"


def build_integrity_warnings(events: List[Event]) -> List[Dict[str, Any]]:
    warnings: List[Dict[str, Any]] = []
    for event in events:
        warning_type = None
        if event.epistemic_status == EpistemicStatus.CONTRADICTION:
            warning_type = "contradiction"
        elif event.severity in {Severity.ERROR, Severity.FATAL}:
            warning_type = "error"
        elif event.type in WARNING_EVENT_TYPES:
            warning_type = event.type
        elif event.type.startswith("contradiction_"):
            warning_type = "contradiction"
        if warning_type is None:
            continue
        summary = _first_str(event.payload, ("reason", "summary", "statement"),
                             default=f"{event.type}: {event.subject_id}")
        warnings.append({
            "warning_id": event.id,
            "timestamp": event.timestamp,
            "type": warning_type,
            "severity": event.severity.value,
            "event_type": event.type,
            "subject_id": event.subject_id,
            "summary": str(summary),
        })
    return warnings


def build_timeline(events: List[Event]) -> List[Dict[str, Any]]:
    return [{
        "event_id": event.id,
        "timestamp": event.timestamp,
        "category": event.category.value,
        "type": event.type,
        "subject_id": event.subject_id,
        "epistemic_status": event.epistemic_status.value,
        "severity": event.severity.value,
        "summary": str(payload_get(event.payload, "summary",
                                   f"{event.type}: {event.subject_id}")),
    } for event in reversed(events)]


def build_actors(events: List[Event]) -> List[str]:
    actors = set()
    for event in events:
        actor_id = payload_get(event.payload, "actor_id")
        if actor_id is not None:
            actors.add(str(actor_id))
        else:
            actors.add(str(event.source))
    return sorted(actors)


def build_provenance_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in events:
        grouped.setdefault(event.subject_id, []).append(event)
    summaries: List[Dict[str, Any]] = []
    for subject_id, subject_events in grouped.items():
        sorted_events = sort_asc(subject_events)
        latest = latest_event(sorted_events)
        if latest is None:
            continue
        reference_targets = set()
        relation_counts: Dict[str, int] = {}
        for event in sorted_events:
            for reference in extract_references(event):
                reference_targets.add(reference["target"])
                relation_counts[reference["relation"]] = \
                    relation_counts.get(reference["relation"], 0) + 1
        warnings = build_integrity_warnings(sorted_events)
        summaries.append({
            "subject_id": subject_id,
            "entity_type": classify_entity(subject_id, grouped),
            "latest_status": str(payload_get(
                latest.payload, "status", latest.epistemic_status.value)),
            "categories": sorted(
                {event.category.value for event in sorted_events}),
            "event_count": len(sorted_events),
            "reference_count": len(reference_targets),
            "warning_count": len(warnings),
            "actors": build_actors(sorted_events),
            "first_observed_at": sorted_events[0].timestamp,
            "last_observed_at": latest.timestamp,
        })
    return sorted(summaries, key=lambda item: item["last_observed_at"],
                  reverse=True)


def build_provenance_audit(subject_id: str,
                           events: List[Event]) -> Optional[Dict[str, Any]]:
    direct_events: List[Event] = []
    relevant_events: List[Event] = []
    for event in events:
        if event.subject_id == subject_id:
            direct_events.append(event)
            relevant_events.append(event)
            continue
        references = extract_references(event)
        if any(reference["target"] == subject_id for reference in references):
            relevant_events.append(event)
    if not relevant_events:
        return None
    direct_sorted = sort_asc(direct_events)
    relevant_sorted = sort_asc(relevant_events)
    latest_direct = latest_event(direct_sorted)
    latest_relevant = latest_event(relevant_sorted)
    status_source = latest_direct or latest_relevant
    if status_source is None:
        return None
    status = str(payload_get(status_source.payload, "status",
                             status_source.epistemic_status.value))
    # Derived hash chain over direct events in chronological order. This
    # chain is recomputed at read time; it is evidence of ordering, not a
    # stored ledger — gaps render as missing links, never assumed links.
    hash_chain: List[Dict[str, Any]] = []
    previous_hash = None
    for event in direct_sorted:
        current_hash = event_hash(event)
        hash_chain.append({"event_id": event.id, "timestamp": event.timestamp,
                           "event_hash": current_hash,
                           "previous_event_hash": previous_hash})
        previous_hash = current_hash
    edges: List[Dict[str, Any]] = []
    seen_edges = set()

    def add_edge(source: str, target: str, relation: str,
                 event: Event) -> None:
        if source == target:
            return
        edge_key = (source, target, relation, event.id)
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)
        edges.append({"source": source, "target": target,
                      "relation": relation, "event_id": event.id,
                      "timestamp": event.timestamp})

    for event in direct_sorted:
        for reference in extract_references(event):
            add_edge(subject_id, reference["target"], reference["relation"],
                     event)
    for event in relevant_sorted:
        if event.subject_id == subject_id:
            continue
        for reference in extract_references(event):
            if reference["target"] == subject_id:
                add_edge(event.subject_id, subject_id, reference["relation"],
                         event)
    node_ids = {subject_id}
    for edge in edges:
        node_ids.add(edge["source"])
        node_ids.add(edge["target"])
    relevant_grouped: Dict[str, List[Event]] = {}
    for event in relevant_sorted:
        relevant_grouped.setdefault(event.subject_id, []).append(event)
    nodes: List[Dict[str, Any]] = []
    for node_id in sorted(node_ids):
        node_events = relevant_grouped.get(node_id, [])
        node_latest = latest_event(sort_asc(node_events)) if node_events else None
        nodes.append({
            "id": node_id,
            "entity_type": classify_entity(node_id, relevant_grouped),
            "event_count": len(node_events),
            "last_observed_at": node_latest.timestamp if node_latest else None,
        })
    warnings = build_integrity_warnings(relevant_sorted)
    governance_events = [event for event in relevant_sorted
                         if event.category == EventCategory.GOVERNANCE]
    categories = sorted({event.category.value for event in relevant_sorted})
    return {
        "subject_id": subject_id,
        "entity_type": classify_entity(subject_id, relevant_grouped),
        "status": status,
        "categories": categories,
        "actors": build_actors(relevant_sorted),
        "direct_event_count": len(direct_sorted),
        "related_event_count": len(relevant_sorted) - len(direct_sorted),
        "epistemic_state": count_epistemic(relevant_sorted),
        "evidence_refs": sorted(collect_evidence_refs(relevant_sorted)),
        "hash_chain": hash_chain,
        "nodes": nodes,
        "edges": edges,
        "warnings": warnings,
        "governance_events": build_timeline(sort_asc(governance_events)),
        "timeline": build_timeline(relevant_sorted),
        "first_observed_at": relevant_sorted[0].timestamp,
        "last_observed_at": relevant_sorted[-1].timestamp,
    }
