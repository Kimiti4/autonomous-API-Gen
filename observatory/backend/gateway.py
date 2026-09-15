"""Observatory gateway: the single backend entry point.

Read paths derive projections; write paths (observe, request_command)
validate, persist/audit, and emit events. Request IDs are content-derived
but timestamp-bound: they are correlation handles, never evidence
identities, and must not be treated as stable.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from datetime import datetime, timezone

from .bus import AsyncEventBus
from .domain import (Actor, CommandRequest, Event, EventCategory,
                     canonical_json, new_governance_event, sha256_hex,
                     utc_now)
from .projections import payload_get
from .projections_provenance import build_provenance_audit, classify_entity
from .projections_experiments import (
    ALL_EVENT_CATEGORIES,
    build_experiment_detail,
    build_experiments_overview,
)
from .projections_fitness import (
    build_fitness_detail,
    build_fitness_overview,
)
from .projections_genomes import (
    build_genome_detail,
    build_genomes_overview,
)
from .projections_provenance import (
    build_provenance_audit,
    build_provenance_overview,
)
from .projections_knowledge import (
    build_knowledge_memory, build_knowledge_overview)
from . import projections
from .governance import COMMAND_ACTIONS, AuthorizationError, GovernanceBoundary
from .store import SqliteEventStore, StoreIntegrityError


class ObservatoryError(Exception):
    pass


class NotFoundError(ObservatoryError):
    pass


SECRET_KEY_MARKERS = ("password", "secret", "token", "credential", "api_key",
                      "apikey", "private_key", "session")


class ObservatoryGateway:
    def __init__(self, store: SqliteEventStore, bus: AsyncEventBus,
                 boundary: Optional[GovernanceBoundary] = None) -> None:
        self.store = store
        self.bus = bus
        self.boundary = boundary or GovernanceBoundary()

    async def observe(self, event: Event) -> str:
        try:
            await asyncio.to_thread(self.store.append, event)
        except StoreIntegrityError as exc:
            raise ObservatoryError(str(exc)) from exc
        await self.bus.publish(event)
        return event.id

    async def observe_many(self, events: List[Event]) -> List[str]:
        return [await self.observe(event) for event in events]

    async def observe_batch(self, events: List[Event]) -> Dict[str, Any]:
        # Only newly inserted events are published; idempotent duplicates
        # are accepted without republication.
        if not events:
            return {"status": "accepted", "accepted": 0, "inserted": 0,
                    "duplicates": 0, "event_ids": []}
        result = await asyncio.to_thread(self.store.append_batch, events)
        for event in result.inserted_events:
            await self.bus.publish(event)
        return {"status": "accepted",
                "accepted": len(result.accepted_event_ids),
                "inserted": result.inserted,
                "duplicates": result.duplicates,
                "event_ids": result.accepted_event_ids}

    async def dashboard(self) -> Dict[str, Any]:
        overview = await self.overview()
        runtime = await self.runtime()
        governance = await self.governance()
        timeline = await self.timeline(limit=20)
        return {"overview": overview, "runtime": runtime,
                "governance": governance, "timeline": timeline}

    async def overview(self) -> Dict[str, Any]:
        recent = await asyncio.to_thread(self.store.recent_events, 200, True)
        runtime = await self.runtime()
        governance = await self.governance()
        current_cycle = self._current_cycle(recent)
        evidence_count = await asyncio.to_thread(
            self.store.count_events_by_category, EventCategory.EVIDENCE)
        return {
            "current_cycle": current_cycle,
            "status": self._overall_status(runtime, governance),
            "runtime_health": runtime["health"],
            "safe_mode": governance["safe_mode"],
            "evidence_count": evidence_count,
            "authorization_state": self._authorization_state(
                current_cycle, governance),
            "recent_event_count": len(recent)}

    async def runtime(self) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_category, EventCategory.RUNTIME, 5000)
        return projections.build_runtime_state(events)

    async def evolution(self, evolution_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_subject, evolution_id, 5000)
        if not events:
            raise NotFoundError(f"evolution {evolution_id} not found")
        return projections.build_evolution_state(evolution_id, events)

    async def evidence(self, evidence_id: str) -> Dict[str, Any]:
        subject_events = await asyncio.to_thread(
            self.store.events_by_subject, evidence_id, 5000)
        events = subject_events or await asyncio.to_thread(
            self.store.events_by_category, EventCategory.EVIDENCE, 10000)
        record = projections.get_evidence(events, evidence_id)
        if record is None:
            raise NotFoundError(f"evidence {evidence_id} not found")
        return record

    async def requirement(self, requirement_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_subject, requirement_id, 5000)
        state = projections.build_requirement_state(requirement_id, events)
        if state is None:
            raise NotFoundError(f"requirement {requirement_id} not found")
        return state

    async def capability(self, capability_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_subject, capability_id, 5000)
        state = projections.build_capability_state(capability_id, events)
        if state is None:
            raise NotFoundError(f"capability {capability_id} not found")
        return state

    async def knowledge(self, subject_id: Optional[str] = None) -> Any:
        if subject_id is None:
            knowledge_events = await asyncio.to_thread(
                self.store.events_by_category, EventCategory.KNOWLEDGE, 10000)
            evidence_events = await asyncio.to_thread(
                self.store.events_by_category, EventCategory.EVIDENCE, 10000)
            return projections.build_knowledge_state(
                knowledge_events + evidence_events)
        events = await asyncio.to_thread(
            self.store.events_by_subject, subject_id, 5000)
        state = projections.get_knowledge(events, subject_id)
        if state is None:
            raise NotFoundError(f"knowledge subject {subject_id} not found")
        return state

    async def governance(self) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_category, EventCategory.GOVERNANCE, 10000)
        return projections.build_governance_state(events)

    async def knowledge_overview(self) -> List[Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            [EventCategory.RUNTIME, EventCategory.EVIDENCE,
             EventCategory.EVOLUTION, EventCategory.GOVERNANCE,
             EventCategory.KNOWLEDGE],
            20000)
        return build_knowledge_overview(events)

    async def experiments_overview(self) -> List[Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        return build_experiments_overview(events)

    async def experiment_detail(self, experiment_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        detail = build_experiment_detail(experiment_id, events)
        if detail is None:
            raise NotFoundError(f"experiment {experiment_id} not found")
        return detail

    async def fitness_overview(self) -> List[Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        return build_fitness_overview(events)

    async def fitness_detail(self, fitness_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        detail = build_fitness_detail(fitness_id, events)
        if detail is None:
            raise NotFoundError(f"fitness subject {fitness_id} not found")
        return detail

    async def genomes_overview(self) -> List[Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        return build_genomes_overview(events)

    async def genome_detail(self, genome_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        detail = build_genome_detail(genome_id, events)
        if detail is None:
            raise NotFoundError(f"genome {genome_id} not found")
        return detail

    async def provenance_overview(self) -> List[Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        return build_provenance_overview(events)

    async def provenance_audit(self, subject_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        audit = build_provenance_audit(subject_id, events)
        if audit is None:
            raise NotFoundError(f"provenance subject {subject_id} not found")
        return audit

    async def search_events(
        self,
        query: Optional[str] = None,
        categories: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        epistemic_statuses: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        events = await asyncio.to_thread(
            self.store.search_events, query, categories, severities,
            epistemic_statuses, since, until, limit)
        results: List[Dict[str, Any]] = []
        for event in events:
            summary = payload_get(
                event.payload, "summary", f"{event.type}: {event.subject_id}")
            results.append({
                "event_id": event.id,
                "timestamp": event.timestamp,
                "category": event.category.value,
                "type": event.type,
                "subject_id": event.subject_id,
                "source": event.source,
                "epistemic_status": event.epistemic_status.value,
                "severity": event.severity.value,
                "entity_type": classify_entity(event.subject_id),
                "summary": str(summary),
            })
        return results

    async def audit_bundle(self, subject_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories, ALL_EVENT_CATEGORIES, 20000)
        audit = build_provenance_audit(subject_id, events)
        if audit is None:
            raise NotFoundError(f"provenance subject {subject_id} not found")
        entity_type = audit["entity_type"]
        links: Dict[str, str] = {"provenance": f"/provenance/{subject_id}"}
        # Domain-family routing first (stable subject identities), then
        # entity type: a mixed-category experiment subject classifies as
        # "evidence" by precedence but belongs in the experiments view.
        normalized = subject_id.strip().upper()
        if normalized.startswith("EXP-"):
            links["view"] = f"/experiments/{subject_id}"
        elif normalized.startswith("FIT-"):
            links["view"] = f"/fitness/{subject_id}"
        elif normalized.startswith(("GEN-", "GENOME-", "GENE-", "CAND-")):
            links["view"] = f"/genomes/{subject_id}"
        elif normalized.startswith(("KNOW-", "MEM-")):
            links["view"] = f"/knowledge/{subject_id}"
        elif normalized.startswith("EVD-"):
            links["view"] = f"/evidence/{subject_id}"
        elif entity_type == "knowledge":
            links["view"] = f"/knowledge/{subject_id}"
        elif entity_type == "experiment":
            links["view"] = f"/experiments/{subject_id}"
        elif entity_type == "fitness":
            links["view"] = f"/fitness/{subject_id}"
        elif entity_type in {"genome", "gene"}:
            links["view"] = f"/genomes/{subject_id}"
        elif entity_type in {"decision", "governance"}:
            links["view"] = "/governance"
        else:
            links["view"] = f"/provenance/{subject_id}"
        return {
            "bundle_version": "observatory-audit-bundle-v1",
            "subject_id": subject_id,
            "entity_type": entity_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "links": links,
            "provenance_audit": audit,
        }

    async def knowledge_memory(self, subject_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            [EventCategory.RUNTIME, EventCategory.EVIDENCE,
             EventCategory.EVOLUTION, EventCategory.GOVERNANCE,
             EventCategory.KNOWLEDGE],
            20000)
        memory = build_knowledge_memory(subject_id, events)
        if memory is None:
            raise NotFoundError(f"knowledge subject {subject_id} not found")
        return memory

    async def timeline(self, subject: Optional[str] = None,
                       limit: int = 50) -> List[Dict[str, Any]]:
        if subject:
            events = await asyncio.to_thread(
                self.store.events_by_subject, subject, limit)
            if not events:
                raise NotFoundError(f"subject {subject} not found")
            events = list(reversed(events))
        else:
            events = await asyncio.to_thread(self.store.recent_events, limit, True)
        return [self._format_timeline_event(event) for event in events]

    async def health(self) -> Dict[str, Any]:
        runtime = await self.runtime()
        governance = await self.governance()
        event_count = await asyncio.to_thread(self.store.count_events)
        evidence_count = await asyncio.to_thread(
            self.store.count_events_by_category, EventCategory.EVIDENCE)
        runtime_count = await asyncio.to_thread(
            self.store.count_events_by_category, EventCategory.RUNTIME)
        governance_count = await asyncio.to_thread(
            self.store.count_events_by_category, EventCategory.GOVERNANCE)
        return {
            "status": self._overall_status(runtime, governance),
            "runtime": runtime, "governance": governance,
            "store": {"event_count": event_count,
                      "evidence_event_count": evidence_count,
                      "runtime_event_count": runtime_count,
                      "governance_event_count": governance_count}}

    async def trace(self, subject_id: str) -> List[Dict[str, Any]]:
        events = await asyncio.to_thread(
            self.store.events_by_subject, subject_id, 10000)
        if not events:
            raise NotFoundError(f"subject {subject_id} not found")
        return [event.model_dump(mode="json") for event in events]

    async def explain(self, subject_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_subject, subject_id, 10000)
        if not events:
            raise NotFoundError(f"subject {subject_id} not found")
        if any(event.category == EventCategory.EVOLUTION for event in events):
            state = projections.build_evolution_state(subject_id, events)
            return {
                "subject_id": subject_id, "explanation_type": "evolution",
                "decision": state["decision"], "status": state["status"],
                "epistemic_state": state["epistemic_state"],
                "capability_check": state["capability_check"],
                "authorization": state["authorization"],
                "unknowns": state["unknowns"],
                "contradictions": state["contradictions"],
                "pipeline": state["pipeline"],
                "trace": [event.id for event in events]}
        if any(event.category == EventCategory.EVIDENCE for event in events):
            record = projections.get_evidence(events, subject_id)
            if record is not None:
                return {
                    "subject_id": subject_id, "explanation_type": "evidence",
                    "claim": record["claim"],
                    "epistemic_status": record["epistemic_status"],
                    "result": record["result"], "scope": record["scope"],
                    "not_proven": record["not_proven"],
                    "provenance": record["provenance"],
                    "trace": [event.id for event in events]}
        return {
            "subject_id": subject_id, "explanation_type": "generic",
            "epistemic_state": projections.count_epistemic(events),
            "latest_event_type": events[-1].type,
            "latest_timestamp": events[-1].timestamp,
            "trace": [event.id for event in events]}

    async def request_command(self, command: CommandRequest,
                              actor: Actor) -> Dict[str, Any]:
        action = command.action
        if action not in COMMAND_ACTIONS:
            raise AuthorizationError("unsupported_action")
        governance_state = await self.governance()
        if (governance_state["safe_mode"] == "enabled"
                and action != "safe_mode_disable"):
            await self._audit_rejection(
                action, command.params, actor, "safe_mode_enabled")
            raise AuthorizationError("safe_mode_enabled")
        authority = governance_state["current_authority"]
        try:
            self.boundary.authorize(action, actor, authority)
        except AuthorizationError as exc:
            await self._audit_rejection(action, command.params, actor, str(exc))
            raise
        request_id = self._generate_request_id(action, command.params)
        target_id = str(command.params.get("target_id") or request_id)
        event = new_governance_event(
            source="observatory_gateway", type="command_requested",
            subject_id=target_id,
            payload={"request_id": request_id, "action": action,
                     "params": self._redact(command.params),
                     "actor_id": actor.id})
        await self.observe(event)
        return {"request_id": request_id, "status": "pending"}

    async def _audit_rejection(self, action: str, params: Dict[str, Any],
                               actor: Actor, reason: str) -> None:
        try:
            event = new_governance_event(
                source="observatory_gateway", type="command_rejected",
                subject_id=str(params.get("target_id") or "GOVERNANCE"),
                reason=reason, severity="warning",
                payload={"action": action, "params": self._redact(params),
                         "actor_id": actor.id})
            await self.observe(event)
        except Exception:
            # Audit failure must not mask the original authorization failure.
            pass

    def _current_cycle(self, recent_events_desc: List[Event]):
        for event in recent_events_desc:
            if event.category == EventCategory.EVOLUTION:
                return {"evolution_id": event.subject_id,
                        "latest_event_type": event.type,
                        "updated_at": event.timestamp}
        return None

    def _overall_status(self, runtime: Dict[str, Any],
                        governance: Dict[str, Any]) -> str:
        if runtime["health"] == "degraded":
            return "degraded"
        if governance["safe_mode"] == "enabled":
            return "safe_mode"
        if runtime["health"] == "green":
            return "operational"
        return "unknown"

    def _authorization_state(self, current_cycle, governance: Dict[str, Any]) -> str:
        if current_cycle is None:
            return "not_applicable"
        if governance["current_authority"].get("implementation") == "none":
            return "required"
        return "granted"

    def _format_timeline_event(self, event: Event) -> Dict[str, Any]:
        summary = event.payload.get("summary")
        if summary is None:
            summary = f"{event.type}: {event.subject_id}"
        return {"event_id": event.id, "timestamp": event.timestamp,
                "category": event.category.value, "type": event.type,
                "subject_id": event.subject_id,
                "epistemic_status": event.epistemic_status.value,
                "severity": event.severity.value, "summary": summary}

    def _generate_request_id(self, action: str, params: Dict[str, Any]) -> str:
        basis = canonical_json({"action": action,
                                "params": self._redact(params),
                                "timestamp": utc_now().isoformat()})
        return f"REQ-{sha256_hex(basis)[:20]}"

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: "[REDACTED]" if self._secret_key(key)
                    else self._redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

    def _secret_key(self, key: Any) -> bool:
        normalized = str(key).lower()
        return any(marker in normalized for marker in SECRET_KEY_MARKERS)
