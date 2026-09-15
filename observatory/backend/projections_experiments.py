"""Experiment overview + detail projections (pure functions).

Read-only derived state over recorded experiment events. This view never
executes experiments, never authorizes them, and never infers success
beyond recorded evidence: unrecorded dimensions stay "unknown", never a
healthy default.
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

ALL_EVENT_CATEGORIES = (
    EventCategory.RUNTIME,
    EventCategory.EVIDENCE,
    EventCategory.EVOLUTION,
    EventCategory.GOVERNANCE,
    EventCategory.KNOWLEDGE,
)

EXPERIMENT_EVENT_PREFIXES = ("experiment_", "trial_")
PROPOSAL_TYPES = {"experiment_proposed", "experiment_defined"}
AUTHORIZATION_TYPES = {"experiment_authorized", "authorization_granted"}
REJECTION_TYPES = {"experiment_rejected", "authorization_rejected"}
START_TYPES = {"experiment_started", "experiment_running", "trial_started"}
COMPLETION_TYPES = {"experiment_completed", "experiment_finished",
                    "trial_completed"}
FAILURE_TYPES = {"experiment_failed", "trial_failed"}
RESULT_TYPES = {"experiment_result", "experiment_observation",
                "observation_recorded", "result_recorded"}
REPRODUCIBILITY_TYPES = {"reproducibility_verified", "experiment_reproduced"}


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


def _latest_payload_value(events: List[Event], key: str,
                          default: Any = None) -> Any:
    for event in reversed(events):
        value = payload_get(event.payload, key)
        if value is not None:
            return value
    return default


def extract_experiment_id(event: Event) -> Optional[str]:
    for key in ("experiment_id", "experiment_run_id", "trial_id"):
        value = payload_get(event.payload, key)
        if value is not None:
            return str(value)
    if event.type.startswith(EXPERIMENT_EVENT_PREFIXES):
        return str(event.subject_id)
    subject = str(event.subject_id)
    if subject.startswith("EXP-"):
        return subject
    return None


def _lifecycle_status(event_type: str) -> Optional[str]:
    if event_type in PROPOSAL_TYPES:
        return "proposed"
    if event_type in AUTHORIZATION_TYPES:
        return "authorized"
    if event_type in REJECTION_TYPES:
        return "rejected"
    if event_type in START_TYPES:
        return "running"
    if event_type in COMPLETION_TYPES:
        return "completed"
    if event_type in FAILURE_TYPES:
        return "failed"
    return None


def derive_experiment_status(events: List[Event]) -> str:
    explicit_status = _latest_payload_value(events, "status")
    if explicit_status is not None:
        return str(explicit_status)
    for event in reversed(events):
        status = _lifecycle_status(event.type)
        if status is not None:
            return status
    return "unknown"


def derive_authorization_state(events: List[Event]) -> str:
    explicit_state = _latest_payload_value(events, "authorization_state")
    if explicit_state is not None:
        return str(explicit_state)
    for event in reversed(events):
        if event.type in REJECTION_TYPES:
            return "rejected"
        if event.type in AUTHORIZATION_TYPES:
            return "authorized"
        if event.type in PROPOSAL_TYPES:
            return "not_authorized"
    return "unknown"


def _normalize_reproducibility(value: Any) -> str:
    if isinstance(value, bool):
        return "verified" if value else "not_verified"
    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    if normalized in {"verified", "reproduced", "pass", "true"}:
        return "verified"
    if normalized in {"not_verified", "failed", "false"}:
        return "not_verified"
    return normalized


def derive_reproducibility_state(events: List[Event]) -> str:
    explicit_value = _latest_payload_value(events, "reproducibility")
    if explicit_value is not None:
        return _normalize_reproducibility(explicit_value)
    for event in reversed(events):
        if event.type in REPRODUCIBILITY_TYPES:
            return "verified"
    return "unknown"


def build_experiment_results(events: List[Event]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for event in events:
        is_result_event = (
            event.type in RESULT_TYPES
            or payload_get(event.payload, "result") is not None
            or payload_get(event.payload, "observed") is not None)
        if not is_result_event:
            continue
        name = _first_str(event.payload, ("name", "metric", "check", "summary"),
                          default=event.type)
        results.append({
            "result_id": event.id,
            "timestamp": event.timestamp,
            "name": str(name),
            "expected": payload_get(event.payload, "expected"),
            "observed": payload_get(event.payload, "observed",
                                    payload_get(event.payload, "result")),
            "passed": payload_get(event.payload, "passed"),
            "epistemic_status": event.epistemic_status.value,
            "evidence_refs": list(event.evidence_refs),
        })
    return results


def build_experiment_unknowns(events: List[Event]) -> List[Dict[str, Any]]:
    unknowns: List[Dict[str, Any]] = []
    for event in events:
        if (event.epistemic_status == EpistemicStatus.UNKNOWN
                or event.type.startswith("unknown_")):
            unknowns.append({
                "unknown_id": str(payload_get(event.payload, "unknown_id",
                                              event.id)),
                "question": str(_first_str(
                    event.payload,
                    ("question", "unknown", "statement", "summary"),
                    default="Unknown experiment condition")),
                "timestamp": event.timestamp,
            })
    return unknowns


def build_experiment_contradictions(events: List[Event]) -> List[Dict[str, Any]]:
    contradictions: List[Dict[str, Any]] = []
    for event in events:
        if (event.epistemic_status == EpistemicStatus.CONTRADICTION
                or event.type.startswith("contradiction_")):
            contradictions.append({
                "contradiction_id": str(payload_get(
                    event.payload, "contradiction_id", event.id)),
                "statement": str(_first_str(
                    event.payload, ("statement", "summary"),
                    default="Experiment evidence contradiction")),
                "timestamp": event.timestamp,
            })
    return contradictions


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


def build_experiments_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in events:
        experiment_id = extract_experiment_id(event)
        if experiment_id is None:
            continue
        grouped.setdefault(experiment_id, []).append(event)
    summaries: List[Dict[str, Any]] = []
    for experiment_id, experiment_events in grouped.items():
        sorted_events = sort_asc(experiment_events)
        latest = latest_event(sorted_events)
        if latest is None:
            continue
        epistemic_state = count_epistemic(sorted_events)
        summaries.append({
            "experiment_id": experiment_id,
            "status": derive_experiment_status(sorted_events),
            "authorization_state": derive_authorization_state(sorted_events),
            "reproducibility": derive_reproducibility_state(sorted_events),
            "hypothesis": _latest_payload_value(sorted_events, "hypothesis"),
            "fixture": _latest_payload_value(sorted_events, "fixture"),
            "environment": _latest_payload_value(sorted_events, "environment"),
            "evidence_count": len(collect_evidence_refs(sorted_events)),
            "results_count": len(build_experiment_results(sorted_events)),
            "unknown_count": epistemic_state["unknown"],
            "contradiction_count": epistemic_state["contradiction"],
            "updated_at": latest.timestamp,
        })
    return sorted(summaries, key=lambda item: item["experiment_id"])


def build_experiment_detail(experiment_id: str,
                            events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = [event for event in events
                if extract_experiment_id(event) == experiment_id
                or event.subject_id == experiment_id]
    if not relevant:
        return None
    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)
    if latest is None:
        return None
    scope = _latest_payload_value(relevant_sorted, "scope", [])
    if not isinstance(scope, list):
        scope = [scope]
    return {
        "experiment_id": experiment_id,
        "status": derive_experiment_status(relevant_sorted),
        "authorization_state": derive_authorization_state(relevant_sorted),
        "reproducibility": derive_reproducibility_state(relevant_sorted),
        "hypothesis": _latest_payload_value(relevant_sorted, "hypothesis"),
        "objective": _latest_payload_value(relevant_sorted, "objective"),
        "fixture": _latest_payload_value(relevant_sorted, "fixture"),
        "environment": _latest_payload_value(relevant_sorted, "environment"),
        "run_id": _latest_payload_value(relevant_sorted, "run_id"),
        "deployment_id": _latest_payload_value(relevant_sorted, "deployment_id"),
        "implementation_id": _latest_payload_value(
            relevant_sorted, "implementation_id"),
        "candidate_id": _latest_payload_value(relevant_sorted, "candidate_id"),
        "scope": scope,
        "epistemic_state": count_epistemic(relevant_sorted),
        "results": build_experiment_results(relevant_sorted),
        "unknowns": build_experiment_unknowns(relevant_sorted),
        "contradictions": build_experiment_contradictions(relevant_sorted),
        "evidence_refs": _merge_unique(
            collect_evidence_refs(relevant_sorted),
            collect_payload_list(relevant_sorted, "evidence_id"),
            collect_payload_list(relevant_sorted, "evidence_refs")),
        "timeline": build_timeline(relevant_sorted),
        "provenance": latest.provenance,
        "sources": sorted({event.source for event in relevant_sorted}),
        "first_observed_at": relevant_sorted[0].timestamp,
        "updated_at": latest.timestamp,
    }
