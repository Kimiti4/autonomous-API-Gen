"""Fitness overview + detail projections (pure functions).

Read-only derived state over recorded fitness events. This view never
evaluates by itself: no aggregate score is fabricated, missing metrics
stay missing, contradicted metrics stay contradicted, and Pareto state
remains unknown unless explicitly recorded.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event
from .projections import (
    collect_evidence_refs,
    collect_payload_list,
    count_epistemic,
    latest_event,
    payload_get,
    sort_asc,
)

FITNESS_PROPOSAL_TYPES = {
    "fitness_proposed",
    "fitness_defined",
    "fitness_objective_defined",
}
METRIC_DEFINITION_TYPES = {"metric_defined", "metric_updated"}
MEASUREMENT_TYPES = {"fitness_measurement", "metric_measured",
                     "measurement_recorded"}
BASELINE_TYPES = {"fitness_baseline", "baseline_recorded"}
EVALUATION_TYPES = {"fitness_evaluation", "fitness_evaluated"}
PARETO_TYPES = {"pareto_observed", "pareto_evaluation", "pareto_updated"}
FAILURE_TYPES = {"fitness_failed", "evaluation_failed"}


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


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_fitness_id(event: Event) -> Optional[str]:
    for key in ("fitness_id", "evaluation_id", "fitness_objective_id"):
        value = payload_get(event.payload, key)
        if value is not None:
            return str(value)
    if event.type.startswith(("fitness_", "pareto_")):
        return str(event.subject_id)
    subject = str(event.subject_id)
    if subject.startswith("FIT-"):
        return subject
    return None


def extract_metric_id(event: Event) -> Optional[str]:
    value = payload_get(event.payload, "metric_id")
    if value is not None:
        return str(value)
    if event.type.startswith("metric_"):
        return str(event.subject_id)
    subject = str(event.subject_id)
    if subject.startswith("METRIC-"):
        return subject
    return None


def derive_fitness_status(events: List[Event]) -> str:
    explicit_status = _latest_payload_value(events, "status")
    if explicit_status is not None:
        return str(explicit_status)
    # Precedence over the whole set (not recency): the most informative
    # lifecycle state reached wins, so a trailing baseline record cannot
    # demote an already-measured objective.
    types = {event.type for event in events}
    if types & FAILURE_TYPES:
        return "failed"
    if types & EVALUATION_TYPES:
        return "evaluated"
    if types & MEASUREMENT_TYPES:
        return "measured"
    if types & BASELINE_TYPES:
        return "baselined"
    if types & FITNESS_PROPOSAL_TYPES:
        return "proposed"
    return "unknown"


def derive_pareto_state(events: List[Event]) -> str:
    explicit_state = _latest_payload_value(
        events, "pareto_state",
        _latest_payload_value(events, "pareto_status"))
    if explicit_state is not None:
        return str(explicit_state)
    for event in reversed(events):
        if event.type in PARETO_TYPES:
            return str(payload_get(event.payload, "pareto_status", "observed"))
    return "unknown"


def build_fitness_unknowns(events: List[Event]) -> List[Dict[str, Any]]:
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
                    default="Unknown fitness condition")),
                "timestamp": event.timestamp,
            })
    return unknowns


def build_fitness_contradictions(events: List[Event]) -> List[Dict[str, Any]]:
    contradictions: List[Dict[str, Any]] = []
    for event in events:
        if (event.epistemic_status == EpistemicStatus.CONTRADICTION
                or event.type.startswith("contradiction_")):
            contradictions.append({
                "contradiction_id": str(payload_get(
                    event.payload, "contradiction_id", event.id)),
                "statement": str(_first_str(
                    event.payload, ("statement", "summary"),
                    default="Fitness measurement contradiction")),
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


def build_fitness_metrics(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in events:
        metric_id = extract_metric_id(event)
        if metric_id is None:
            continue
        grouped.setdefault(metric_id, []).append(event)
    metrics: List[Dict[str, Any]] = []
    for metric_id, metric_events in grouped.items():
        sorted_events = sort_asc(metric_events)
        name = _latest_payload_value(sorted_events, "name", metric_id)
        unit = _latest_payload_value(sorted_events, "unit")
        direction = _latest_payload_value(sorted_events, "direction")
        target_value = _latest_payload_value(sorted_events, "target")
        baseline_value = _latest_payload_value(sorted_events, "baseline")
        baseline_at = None
        for event in sorted_events:
            if event.type in BASELINE_TYPES:
                candidate_value = payload_get(
                    event.payload, "baseline",
                    payload_get(event.payload, "value"))
                if candidate_value is not None:
                    baseline_value = candidate_value
                    baseline_at = event.timestamp
        measurements: List[Dict[str, Any]] = []
        for event in sorted_events:
            value = payload_get(
                event.payload, "value",
                payload_get(event.payload, "observed",
                            payload_get(event.payload, "measurement")))
            if event.type in MEASUREMENT_TYPES or value is not None:
                if value is None:
                    continue
                measurements.append({
                    "measurement_id": event.id,
                    "timestamp": event.timestamp,
                    "value": value,
                    "unit": payload_get(event.payload, "unit", unit),
                    "scope": payload_get(event.payload, "scope", []),
                    "epistemic_status": event.epistemic_status.value,
                    "evidence_refs": list(event.evidence_refs),
                })
        latest_measurement = measurements[-1] if measurements else None
        latest_value = latest_measurement["value"] if latest_measurement else None
        latest_float = _to_float(latest_value)
        baseline_float = _to_float(baseline_value)
        delta_vs_baseline = None
        if latest_float is not None and baseline_float is not None:
            delta_vs_baseline = latest_float - baseline_float
        explicit_status = _latest_payload_value(sorted_events, "status")
        if explicit_status is not None:
            status = str(explicit_status)
        elif any(event.epistemic_status == EpistemicStatus.CONTRADICTION
                 for event in sorted_events):
            status = "contradicted"
        elif measurements:
            status = "measured"
        else:
            status = "missing"
        metrics.append({
            "metric_id": metric_id,
            "name": str(name),
            "unit": unit,
            "direction": direction,
            "target_value": target_value,
            "baseline_value": baseline_value,
            "baseline_at": baseline_at,
            "latest_value": latest_value,
            "latest_measurement_at": (latest_measurement["timestamp"]
                                      if latest_measurement else None),
            "delta_vs_baseline": delta_vs_baseline,
            "measurement_count": len(measurements),
            "status": status,
        })
    return sorted(metrics, key=lambda item: item["metric_id"])


def build_fitness_evaluations(events: List[Event]) -> List[Dict[str, Any]]:
    evaluations: List[Dict[str, Any]] = []
    for event in events:
        if event.type not in EVALUATION_TYPES:
            continue
        evaluations.append({
            "evaluation_id": str(payload_get(event.payload, "evaluation_id",
                                             event.id)),
            "timestamp": event.timestamp,
            "summary": str(_first_str(
                event.payload, ("summary", "statement"),
                default=f"{event.type}: {event.subject_id}")),
            "result": payload_get(event.payload, "result"),
            "evidence_refs": list(event.evidence_refs),
        })
    return evaluations


def build_fitness_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in events:
        fitness_id = extract_fitness_id(event)
        if fitness_id is None:
            continue
        grouped.setdefault(fitness_id, []).append(event)
    summaries: List[Dict[str, Any]] = []
    for fitness_id, fitness_events in grouped.items():
        sorted_events = sort_asc(fitness_events)
        latest = latest_event(sorted_events)
        if latest is None:
            continue
        objective = _first_str(latest.payload, ("objective", "title", "summary"),
                               default=fitness_id)
        epistemic_state = count_epistemic(sorted_events)
        metric_ids = {extract_metric_id(event) for event in sorted_events}
        metric_ids.discard(None)
        summaries.append({
            "fitness_id": fitness_id,
            "status": derive_fitness_status(sorted_events),
            "objective": objective,
            "pareto_state": derive_pareto_state(sorted_events),
            "metric_count": len(metric_ids),
            "measurement_count": sum(
                1 for event in sorted_events if event.type in MEASUREMENT_TYPES),
            "baseline_count": sum(
                1 for event in sorted_events if event.type in BASELINE_TYPES),
            "evaluation_count": sum(
                1 for event in sorted_events if event.type in EVALUATION_TYPES),
            "evidence_count": len(collect_evidence_refs(sorted_events)),
            "unknown_count": epistemic_state["unknown"],
            "contradiction_count": epistemic_state["contradiction"],
            "updated_at": latest.timestamp,
        })
    return sorted(summaries, key=lambda item: item["fitness_id"])


def build_fitness_detail(fitness_id: str,
                         events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = [event for event in events
                if extract_fitness_id(event) == fitness_id
                or event.subject_id == fitness_id]
    if not relevant:
        return None
    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)
    if latest is None:
        return None
    objective = _first_str(latest.payload, ("objective", "title", "summary"),
                           default=fitness_id)
    scope = _latest_payload_value(relevant_sorted, "scope", [])
    if not isinstance(scope, list):
        scope = [scope]
    return {
        "fitness_id": fitness_id,
        "status": derive_fitness_status(relevant_sorted),
        "objective": objective,
        "description": _latest_payload_value(relevant_sorted, "description"),
        "scope": scope,
        "environment": _latest_payload_value(relevant_sorted, "environment"),
        "candidate_id": _latest_payload_value(relevant_sorted, "candidate_id"),
        "implementation_id": _latest_payload_value(
            relevant_sorted, "implementation_id"),
        "deployment_id": _latest_payload_value(relevant_sorted, "deployment_id"),
        "pareto_state": derive_pareto_state(relevant_sorted),
        "epistemic_state": count_epistemic(relevant_sorted),
        "metrics": build_fitness_metrics(relevant_sorted),
        "evaluations": build_fitness_evaluations(relevant_sorted),
        "unknowns": build_fitness_unknowns(relevant_sorted),
        "contradictions": build_fitness_contradictions(relevant_sorted),
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
