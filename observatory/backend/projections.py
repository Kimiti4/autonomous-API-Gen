"""Pure projection functions: events in, derived state out.

RULES: no I/O, no messaging, no mutation, deterministic output.
Epistemic rule: missing data is never fabricated — an absent result is
not success, an unmeasured metric is "not_measured", an empty stream
yields "unknown", never a healthy default.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event, EventCategory, Severity

DEFAULT_AUTHORITY = {
    "interpretation": "granted",
    "evolution": "definition_only",
    "implementation": "none",
    "runtime": "none",
    "deployment": "none",
    "production": "none",
    "governance": "granted",
}

EVOLUTION_STAGES = [
    "requirement_parsed",
    "isr_consulted",
    "constraints_derived",
    "candidate_generated",
    "static_validation",
    "runtime_validation",
    "evidence_certification",
]

SUCCESS_VALUES = {"success", "pass", "ok", "completed", "done"}

# Closed decision vocabulary for derived evolution decisions. Payload
# values outside this set degrade to "recorded", never surface verbatim.
DECISION_VOCABULARY = {"advanced", "held", "blocked", "recorded", "unknown"}


def sort_asc(events: List[Event]) -> List[Event]:
    return sorted(events, key=lambda event: event.timestamp)


def latest_event(events: List[Event]) -> Optional[Event]:
    if not events:
        return None
    return max(events, key=lambda event: event.timestamp)


def payload_get(payload: Dict[str, Any], key: str, default: Any = None) -> Any:
    if payload is None:
        return default
    if key in payload:
        return payload[key]
    string_key = str(key)
    if string_key in payload:
        return payload[string_key]
    return default


def result_is_ok(value: Any) -> bool:
    # FIX (never-fabricate): a missing result is NOT success.
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in SUCCESS_VALUES


def count_epistemic(events: List[Event]) -> Dict[str, int]:
    counts = {status.value: 0 for status in EpistemicStatus}
    for event in events:
        counts[event.epistemic_status.value] += 1
    return counts


def count_type(events: List[Event], type: str) -> int:
    return sum(1 for event in events if event.type == type)


def latest_metric(events: List[Event], key: str) -> Any:
    metric_events = [
        event for event in events
        if event.type == "metric" and payload_get(event.payload, key) is not None
    ]
    latest = latest_event(metric_events)
    if latest is None:
        return "not_measured"
    return payload_get(latest.payload, key)


def derive_runtime_health(events: List[Event]) -> str:
    if not events:
        return "unknown"
    degraded = any(
        event.severity in {Severity.ERROR, Severity.FATAL}
        or event.type in {"process_crashed", "supervisor_crashed", "runtime_failure"}
        for event in events)
    return "degraded" if degraded else "green"


def build_runtime_state(events: List[Event]) -> Dict[str, Any]:
    runtime_events = sort_asc(
        [event for event in events if event.category == EventCategory.RUNTIME])
    started = count_type(runtime_events, "process_started")
    stopped = count_type(runtime_events, "process_stopped")
    latest = latest_event(runtime_events)
    return {
        "processes": max(started - stopped, 0),
        "supervisors": count_type(runtime_events, "supervisor_started"),
        "messages_per_sec": latest_metric(runtime_events, "messages_per_sec"),
        "memory_total": latest_metric(runtime_events, "memory_total"),
        "restart_count": count_type(runtime_events, "process_restarted"),
        "health": derive_runtime_health(runtime_events),
        "updated_at": latest.timestamp if latest else None,
    }


def stage_done(events: List[Event], stage: str) -> bool:
    for event in events:
        if event.type == stage and result_is_ok(payload_get(event.payload, "result")):
            return True
        if (event.type == "stage_completed"
                and payload_get(event.payload, "stage") == stage
                and result_is_ok(payload_get(event.payload, "result"))):
            return True
    return False


def stage_failed(events: List[Event], stage: str) -> bool:
    return any(event.type == "stage_failed"
               and payload_get(event.payload, "stage") == stage
               for event in events)


def mark_current_stage(pipeline: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if any(item["status"] in {"failed", "blocked"} for item in pipeline):
        return pipeline
    marked = False
    for item in pipeline:
        if item["status"] == "pending" and not marked:
            item["status"] = "current"
            marked = True
    return pipeline


def build_pipeline(events: List[Event]) -> List[Dict[str, str]]:
    blocked = any(event.type == "evolution_blocked" for event in events)
    pipeline = []
    for stage in EVOLUTION_STAGES:
        if stage_failed(events, stage):
            status = "failed"
        elif blocked and not stage_done(events, stage):
            status = "blocked"
        elif stage_done(events, stage):
            status = "done"
        else:
            status = "pending"
        pipeline.append({"stage": stage, "status": status})
    return mark_current_stage(pipeline)


def derive_evolution_status(events: List[Event],
                            pipeline: List[Dict[str, str]]) -> str:
    if not events:
        return "unknown"
    if any(event.type == "evolution_blocked" for event in events):
        return "blocked"
    if any(item["status"] == "failed" for item in pipeline):
        return "blocked"
    if all(item["status"] == "done" for item in pipeline):
        return "complete"
    return "in_progress"


def derive_epistemic_state(events: List[Event]) -> Dict[str, int]:
    return count_epistemic(
        [event for event in events if event.category == EventCategory.EVIDENCE])


def derive_capability_check(events: List[Event]) -> Dict[str, str]:
    state = {"generation": "unknown", "validation": "unknown",
             "runtime": "unknown", "production": "unknown"}
    for event in events:
        if event.type not in {"capability_check", "capability_assessed"}:
            continue
        capability = str(payload_get(event.payload, "capability", "")).strip().lower()
        status = str(payload_get(event.payload, "status", "unknown")).strip().lower()
        if capability in state:
            state[capability] = status
    return state


def derive_decision(events: List[Event]) -> str:
    decision_events = [
        event for event in events
        if event.type in {"decision_recorded", "evolution_decision",
                         "evolution_advanced", "evolution_held",
                         "evolution_blocked"}]
    latest = latest_event(decision_events)
    if latest is None:
        return "unknown"
    payload_decision = payload_get(latest.payload, "decision")
    if payload_decision is not None:
        # FIX: closed vocabulary; unknown values degrade to "recorded".
        candidate = str(payload_decision).strip().lower()
        return candidate if candidate in DECISION_VOCABULARY else "recorded"
    if latest.type == "evolution_advanced":
        return "advanced"
    if latest.type == "evolution_held":
        return "held"
    if latest.type == "evolution_blocked":
        return "blocked"
    return "recorded"


def derive_authorization(events: List[Event]) -> Dict[str, str]:
    authority = dict(DEFAULT_AUTHORITY)
    authorization_events = [
        event for event in events if event.type == "authorization_updated"]
    latest = latest_event(authorization_events)
    if latest is None:
        return authority
    raw_authority = payload_get(latest.payload, "authority", {})
    if not isinstance(raw_authority, dict):
        return authority
    normalized = {str(key).strip().lower(): str(value).strip().lower()
                  for key, value in raw_authority.items()}
    for key in DEFAULT_AUTHORITY:
        if key in normalized:
            authority[key] = normalized[key]
    return authority


def derive_unknowns(events: List[Event]) -> List[str]:
    unknowns = set()
    for event in events:
        if event.epistemic_status == EpistemicStatus.UNKNOWN:
            unknowns.add(str(payload_get(event.payload, "unknown_id",
                                         event.subject_id)))
    return sorted(unknowns)


def derive_contradictions(events: List[Event]) -> List[str]:
    contradictions = set()
    for event in events:
        if event.epistemic_status == EpistemicStatus.CONTRADICTION:
            contradictions.add(str(payload_get(event.payload, "contradiction_id",
                                               event.subject_id)))
    return sorted(contradictions)


def build_evolution_state(evolution_id: str,
                          events: List[Event]) -> Dict[str, Any]:
    relevant = sort_asc(
        [event for event in events if event.subject_id == evolution_id])
    pipeline = build_pipeline(relevant)
    return {
        "evolution_id": evolution_id,
        "status": derive_evolution_status(relevant, pipeline),
        "epistemic_state": derive_epistemic_state(relevant),
        "capability_check": derive_capability_check(relevant),
        "pipeline": pipeline,
        "decision": derive_decision(relevant),
        "authorization": derive_authorization(relevant),
        "unknowns": derive_unknowns(relevant),
        "contradictions": derive_contradictions(relevant),
        "updated_at": latest_event(relevant).timestamp if relevant else None,
    }


def build_evidence_record(evidence_id: str,
                          events: List[Event]) -> Dict[str, Any]:
    latest = latest_event(events)
    assert latest is not None
    claim = str(payload_get(latest.payload, "claim", "unspecified"))
    if latest.epistemic_status == EpistemicStatus.CONTRADICTION:
        result = "contradiction"
    else:
        result = payload_get(latest.payload, "result", "unknown")
    scope = payload_get(latest.payload, "scope", [])
    not_proven = payload_get(latest.payload, "not_proven", [])
    provenance = dict(latest.provenance or {})
    payload_provenance = payload_get(latest.payload, "provenance", {})
    if isinstance(payload_provenance, dict):
        provenance.update(payload_provenance)
    for event in events:
        if event.type != "provenance_verified":
            continue
        checks = payload_get(event.payload, "checks", {})
        if isinstance(checks, dict):
            provenance.update(checks)
    return {"evidence_id": evidence_id,
            "epistemic_status": latest.epistemic_status.value,
            "claim": claim, "result": result, "scope": scope,
            "not_proven": not_proven, "provenance": provenance,
            "observed_at": latest.timestamp}


def build_evidence_state(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in sort_asc(
            [e for e in events if e.category == EventCategory.EVIDENCE]):
        grouped.setdefault(event.subject_id, []).append(event)
    return sorted((build_evidence_record(eid, evs)
                   for eid, evs in grouped.items()),
                  key=lambda record: record["evidence_id"])


def get_evidence(events: List[Event],
                 evidence_id: str) -> Optional[Dict[str, Any]]:
    for record in build_evidence_state(events):
        if record["evidence_id"] == evidence_id:
            return record
    return None


def build_governance_state(events: List[Event]) -> Dict[str, Any]:
    governance_events = sort_asc(
        [event for event in events if event.category == EventCategory.GOVERNANCE])
    authority = dict(DEFAULT_AUTHORITY)
    gates: Dict[str, str] = {}
    safe_mode = "unknown"
    commands = {"requested": 0, "accepted": 0, "rejected": 0}
    for event in governance_events:
        if event.type == "authority_updated":
            raw_authority = payload_get(event.payload, "authority", {})
            if isinstance(raw_authority, dict):
                normalized = {
                    str(key).strip().lower(): str(value).strip().lower()
                    for key, value in raw_authority.items()}
                for key in DEFAULT_AUTHORITY:
                    if key in normalized:
                        authority[key] = normalized[key]
        elif event.type == "gate_updated":
            gate = payload_get(event.payload, "gate")
            status = payload_get(event.payload, "status", "unknown")
            if gate is not None:
                gates[str(gate)] = str(status)
        elif event.type == "safe_mode_enabled":
            safe_mode = "enabled"
        elif event.type == "safe_mode_disabled":
            safe_mode = "disabled"
        elif event.type == "command_requested":
            commands["requested"] += 1
        elif event.type == "command_accepted":
            commands["accepted"] += 1
        elif event.type == "command_rejected":
            commands["rejected"] += 1
    return {
        "current_authority": authority,
        "active_gates": [{"gate": gate, "status": status}
                         for gate, status in sorted(gates.items())],
        "safe_mode": safe_mode,
        "human_controls": ["safe_mode", "stop", "restart",
                           "request_authorization"],
        "command_activity": commands,
    }


def build_knowledge_state(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}
    for event in sort_asc(
            [e for e in events
             if e.category in {EventCategory.KNOWLEDGE, EventCategory.EVIDENCE}]):
        grouped.setdefault(event.subject_id, []).append(event)
    records = []
    for subject_id, grouped_events in grouped.items():
        latest = latest_event(grouped_events)
        assert latest is not None
        records.append({
            "subject_id": subject_id,
            "epistemic_state": count_epistemic(grouped_events),
            "latest_status": latest.epistemic_status.value,
            "updated_at": latest.timestamp})
    return sorted(records, key=lambda record: record["subject_id"])


def get_knowledge(events: List[Event],
                  subject_id: str) -> Optional[Dict[str, Any]]:
    for record in build_knowledge_state(events):
        if record["subject_id"] == subject_id:
            return record
    return None


def collect_evidence_refs(events: List[Event]) -> List[str]:
    refs = set()
    for event in events:
        for ref in event.evidence_refs:
            refs.add(str(ref))
    return sorted(refs)


def collect_payload_list(events: List[Event], key: str) -> List[str]:
    values: List[str] = []
    for event in events:
        value = payload_get(event.payload, key, [])
        if isinstance(value, list):
            values.extend(str(item) for item in value if item is not None)
        elif value is not None:
            values.append(str(value))
    return sorted(set(values))


def build_requirement_state(requirement_id: str,
                            events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = sort_asc(
        [event for event in events if event.subject_id == requirement_id])
    if not relevant:
        return None
    latest = latest_event(relevant)
    assert latest is not None
    return {
        "requirement_id": requirement_id,
        "status": payload_get(latest.payload, "status",
                              latest.epistemic_status.value),
        "epistemic_state": count_epistemic(relevant),
        "evidence_refs": collect_evidence_refs(relevant),
        "related_capabilities": collect_payload_list(relevant, "capabilities"),
        "related_evolutions": collect_payload_list(relevant, "evolutions"),
        "unknown_dependencies": collect_payload_list(
            relevant, "unknown_dependencies"),
        "updated_at": latest.timestamp}


def build_capability_state(capability_id: str,
                           events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = sort_asc(
        [event for event in events if event.subject_id == capability_id])
    if not relevant:
        return None
    latest = latest_event(relevant)
    assert latest is not None
    return {
        "capability_id": capability_id,
        "status": payload_get(latest.payload, "status",
                              latest.epistemic_status.value),
        "epistemic_state": count_epistemic(relevant),
        "evidence_refs": collect_evidence_refs(relevant),
        "related_requirements": collect_payload_list(relevant, "requirements"),
        "related_evolutions": collect_payload_list(relevant, "evolutions"),
        "updated_at": latest.timestamp}
