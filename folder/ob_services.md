Yes — proceeding with the **Selection / Decision view**.

This view gives the Observatory a read-only surface for inspecting governed choices:

```text
decision identity
decision question
candidate alternatives
selection outcome
evidence sufficiency
unknowns accepted
unknowns rejected
contradictions blocking the decision
authorization granted or denied
next gate authorization state
```

This view does **not** make decisions.

It does **not** authorize evolution.

It does **not** override governance.

It renders recorded decision evidence.

---

# 1. Constitutional alignment

The Constitution requires:

```text
Architectural decisions should emerge through collaboration.
Fitness evaluation should support selection.
Multi-objective optimisation should avoid a single aggregate score.
Architectural reasoning should remain transparent.
```

The Selection / Decision view therefore preserves:

```text
decision provenance
candidate alternatives
evidence sufficiency
unknown handling
contradiction handling
authorization boundaries
next-gate authority
```

---

# 2. What this adds

This step adds:

```text
backend decision projection
backend decision overview endpoint
backend decision detail endpoint
frontend decision list page
frontend decision detail page
decision event contract
```

New backend endpoints:

```text
GET /observatory/decisions
GET /observatory/decisions/{decision_id}
```

New frontend routes:

```text
/decisions
/decisions/{decision_id}
```

---

# 3. Backend: decision projection

Create:

**`observatory/backend/projections_decisions.py`**

```python
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

DECISION_PROPOSAL_TYPES = {
    "decision_proposed",
    "decision_requested",
    "decision_defined",
}

DECISION_EVALUATION_TYPES = {
    "decision_evaluated",
    "sufficiency_evaluated",
    "selection_evaluated",
}

DECISION_RECORDED_TYPES = {
    "decision_recorded",
    "decision_made",
    "selection_recorded",
    "candidate_selected",
}

DECISION_AUTHORIZATION_TYPES = {
    "decision_authorized",
    "authorization_granted",
    "authorization_updated",
}

DECISION_REJECTION_TYPES = {
    "decision_rejected",
    "authorization_rejected",
    "selection_rejected",
}

DECISION_BLOCK_TYPES = {
    "decision_blocked",
    "selection_blocked",
}

CANDIDATE_SELECTED_TYPES = {
    "candidate_selected",
}

CANDIDATE_REJECTED_TYPES = {
    "candidate_rejected",
}

CANDIDATE_EVALUATED_TYPES = {
    "candidate_evaluated",
}

SELECTION_EVENT_TYPES = {
    "selection_recorded",
    "selection_evaluated",
    "candidate_selected",
    "candidate_rejected",
    "candidate_evaluated",
}


def _merge_unique(*lists: List[str]) -> List[str]:
    merged = set()

    for values in lists:
        for value in values:
            if value is None:
                continue

            merged.add(str(value))

    return sorted(merged)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    return [str(value)]


def _first_str(
    payload: Dict[str, Any],
    keys: tuple[str, ...],
    default: Optional[str] = None,
) -> Optional[str]:
    for key in keys:
        value = payload_get(payload, key)

        if value is not None:
            return str(value)

    return default


def _latest_payload_value(
    events: List[Event],
    key: str,
    default: Any = None,
) -> Any:
    for event in reversed(events):
        value = payload_get(event.payload, key)

        if value is not None:
            return value

    return default


def extract_decision_id(event: Event) -> Optional[str]:
    for key in (
        "decision_id",
        "selection_id",
        "authorization_id",
        "gate_decision_id",
    ):
        value = payload_get(event.payload, key)

        if value is not None:
            return str(value)

    if event.type.startswith(
        (
            "decision_",
            "selection_",
            "authorization_",
            "gate_",
        )
    ):
        return str(event.subject_id)

    subject = str(event.subject_id)

    if subject.startswith(("DEC-", "SEL-", "AUTH-", "GATE-")):
        return subject

    return None


def derive_decision_type(events: List[Event]) -> str:
    explicit_type = _latest_payload_value(events, "decision_type")

    if explicit_type is not None:
        return str(explicit_type)

    has_selection = any(event.type in SELECTION_EVENT_TYPES for event in events)

    if has_selection:
        return "selection"

    has_authorization = any(
        event.type in DECISION_AUTHORIZATION_TYPES for event in events
    )

    if has_authorization:
        return "authorization"

    has_decision = any(
        event.type.startswith("decision_") or event.type.startswith("gate_")
        for event in events
    )

    if has_decision:
        return "decision"

    return "unknown"


def derive_decision_status(events: List[Event]) -> str:
    explicit_status = _latest_payload_value(events, "status")

    if explicit_status is not None:
        return str(explicit_status)

    for event in reversed(events):
        if event.type in DECISION_BLOCK_TYPES:
            return "blocked"

        if event.type in DECISION_REJECTION_TYPES:
            return "rejected"

        if event.type in DECISION_AUTHORIZATION_TYPES:
            return "authorized"

        if event.type in DECISION_RECORDED_TYPES:
            return "decided"

        if event.type in DECISION_EVALUATION_TYPES:
            return "evaluated"

        if event.type in DECISION_PROPOSAL_TYPES:
            return "proposed"

    return "observed"


def derive_evidence_sufficiency(events: List[Event]) -> str:
    explicit_sufficiency = _latest_payload_value(
        events,
        "evidence_sufficiency",
        _latest_payload_value(events, "sufficiency"),
    )

    if explicit_sufficiency is not None:
        return str(explicit_sufficiency)

    if any(event.type in DECISION_EVALUATION_TYPES for event in events):
        return "evaluated"

    return "unknown"


def derive_authorization_state(events: List[Event]) -> str:
    explicit_state = _latest_payload_value(events, "authorization_state")

    if explicit_state is not None:
        return str(explicit_state)

    for event in reversed(events):
        if event.type in DECISION_REJECTION_TYPES:
            return "rejected"

        if event.type in DECISION_AUTHORIZATION_TYPES:
            return "granted"

        if event.type in DECISION_RECORDED_TYPES:
            return "none"

        if event.type in DECISION_PROPOSAL_TYPES:
            return "not_authorized"

    return "unknown"


def build_decision_alternatives(events: List[Event]) -> List[Dict[str, Any]]:
    alternatives: Dict[str, Dict[str, Any]] = {}

    def add_alternative(
        candidate_id: Any,
        outcome: Optional[str] = None,
        reason: Optional[str] = None,
        event: Optional[Event] = None,
    ) -> None:
        if candidate_id is None:
            return

        normalized_candidate_id = str(candidate_id)

        alternative = alternatives.get(normalized_candidate_id)

        if alternative is None:
            alternative = {
                "candidate_id": normalized_candidate_id,
                "outcome": outcome or "listed",
                "reason": reason,
                "fitness_links": set(),
                "evidence_refs": set(),
                "updated_at": event.timestamp if event else None,
            }
            alternatives[normalized_candidate_id] = alternative
        else:
            if outcome is not None:
                alternative["outcome"] = outcome

            if reason is not None:
                alternative["reason"] = reason

            if event is not None:
                alternative["updated_at"] = event.timestamp

        if event is not None:
            alternative["evidence_refs"].update(event.evidence_refs)

            fitness_id = payload_get(event.payload, "fitness_id")

            if fitness_id is not None:
                alternative["fitness_links"].add(str(fitness_id))

    for event in events:
        for key in ("candidates", "alternatives", "rejected_candidates"):
            value = payload_get(event.payload, key)

            if not isinstance(value, list):
                continue

            for item in value:
                if isinstance(item, dict):
                    candidate_id = item.get("candidate_id") or item.get("id")
                    outcome = item.get("outcome")
                    reason = item.get("reason")

                    if key == "rejected_candidates" and outcome is None:
                        outcome = "rejected"

                    add_alternative(candidate_id, outcome, reason, event)
                else:
                    outcome = "rejected" if key == "rejected_candidates" else "listed"
                    add_alternative(item, outcome, None, event)

        selected_candidate = payload_get(event.payload, "selected_candidate")

        if selected_candidate is not None:
            add_alternative(
                selected_candidate,
                "selected",
                payload_get(event.payload, "reason"),
                event,
            )

        rejected_candidate = payload_get(event.payload, "rejected_candidate")

        if rejected_candidate is not None:
            add_alternative(
                rejected_candidate,
                "rejected",
                payload_get(event.payload, "reason"),
                event,
            )

        if event.type in CANDIDATE_SELECTED_TYPES:
            candidate_id = payload_get(
                event.payload,
                "candidate_id",
                payload_get(event.payload, "selected_candidate"),
            )

            add_alternative(
                candidate_id,
                "selected",
                payload_get(event.payload, "reason"),
                event,
            )

        if event.type in CANDIDATE_REJECTED_TYPES:
            candidate_id = payload_get(
                event.payload,
                "candidate_id",
                payload_get(event.payload, "rejected_candidate"),
            )

            add_alternative(
                candidate_id,
                "rejected",
                payload_get(event.payload, "reason"),
                event,
            )

        if event.type in CANDIDATE_EVALUATED_TYPES:
            candidate_id = payload_get(event.payload, "candidate_id")

            add_alternative(
                candidate_id,
                "evaluated",
                payload_get(event.payload, "reason"),
                event,
            )

    result: List[Dict[str, Any]] = []

    for alternative in alternatives.values():
        alternative["fitness_links"] = sorted(alternative["fitness_links"])
        alternative["evidence_refs"] = sorted(alternative["evidence_refs"])
        result.append(alternative)

    return sorted(result, key=lambda item: item["candidate_id"])


def build_unknown_lists(events: List[Event]) -> tuple[List[str], List[str]]:
    accepted = set()
    rejected = set()

    for event in events:
        accepted_payload = payload_get(event.payload, "unknowns_accepted", [])
        rejected_payload = payload_get(event.payload, "unknowns_rejected", [])

        accepted.update(_as_list(accepted_payload))
        rejected.update(_as_list(rejected_payload))

        if event.type == "unknown_accepted":
            unknown_id = payload_get(event.payload, "unknown_id", event.id)
            accepted.add(str(unknown_id))

        if event.type == "unknown_rejected":
            unknown_id = payload_get(event.payload, "unknown_id", event.id)
            rejected.add(str(unknown_id))

    return sorted(accepted), sorted(rejected)


def build_contradiction_ids(events: List[Event]) -> List[str]:
    contradiction_ids = set()

    for event in events:
        blocking_payload = payload_get(event.payload, "contradictions_blocking", [])
        contradiction_ids.update(_as_list(blocking_payload))

        contradiction_id = payload_get(event.payload, "contradiction_id")

        if contradiction_id is not None and (
            event.epistemic_status == EpistemicStatus.CONTRADICTION
            or event.type.startswith("contradiction_")
        ):
            contradiction_ids.add(str(contradiction_id))

    return sorted(contradiction_ids)


def build_timeline(events: List[Event]) -> List[Dict[str, Any]]:
    return [
        {
            "event_id": event.id,
            "timestamp": event.timestamp,
            "category": event.category.value,
            "type": event.type,
            "subject_id": event.subject_id,
            "epistemic_status": event.epistemic_status.value,
            "severity": event.severity.value,
            "summary": str(
                payload_get(
                    event.payload,
                    "summary",
                    f"{event.type}: {event.subject_id}",
                )
            ),
        }
        for event in reversed(events)
    ]


def build_decisions_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}

    for event in events:
        decision_id = extract_decision_id(event)

        if decision_id is None:
            continue

        grouped.setdefault(decision_id, []).append(event)

    summaries: List[Dict[str, Any]] = []

    for decision_id, decision_events in grouped.items():
        sorted_events = sort_asc(decision_events)
        latest = latest_event(sorted_events)

        if latest is None:
            continue

        question = _first_str(
            latest.payload,
            ("decision_question", "question", "objective", "summary"),
            default=decision_id,
        )

        unknown_accepted, unknown_rejected = build_unknown_lists(sorted_events)
        contradiction_ids = build_contradiction_ids(sorted_events)

        summaries.append(
            {
                "decision_id": decision_id,
                "status": derive_decision_status(sorted_events),
                "decision_type": derive_decision_type(sorted_events),
                "question": question,
                "evidence_sufficiency": derive_evidence_sufficiency(sorted_events),
                "authorization_state": derive_authorization_state(sorted_events),
                "next_gate": _latest_payload_value(sorted_events, "next_gate"),
                "candidate_count": len(build_decision_alternatives(sorted_events)),
                "unknown_accepted_count": len(unknown_accepted),
                "unknown_rejected_count": len(unknown_rejected),
                "contradiction_count": len(contradiction_ids),
                "evidence_count": len(collect_evidence_refs(sorted_events)),
                "updated_at": latest.timestamp,
            }
        )

    return sorted(summaries, key=lambda item: item["decision_id"])


def build_decision_detail(
    decision_id: str,
    events: List[Event],
) -> Optional[Dict[str, Any]]:
    relevant = [
        event
        for event in events
        if extract_decision_id(event) == decision_id
        or event.subject_id == decision_id
    ]

    if not relevant:
        return None

    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)

    if latest is None:
        return None

    question = _first_str(
        latest.payload,
        ("decision_question", "question", "objective", "summary"),
        default=decision_id,
    )

    description = _latest_payload_value(relevant_sorted, "description")
    scope = _latest_payload_value(relevant_sorted, "scope", [])

    if not isinstance(scope, list):
        scope = [scope]

    unknown_accepted, unknown_rejected = build_unknown_lists(relevant_sorted)
    contradiction_ids = build_contradiction_ids(relevant_sorted)
    alternatives = build_decision_alternatives(relevant_sorted)

    requirement_links = _merge_unique(
        collect_payload_list(relevant_sorted, "requirement_id"),
        collect_payload_list(relevant_sorted, "objective_id"),
    )

    candidate_links = _merge_unique(
        [alternative["candidate_id"] for alternative in alternatives],
        collect_payload_list(relevant_sorted, "candidate_id"),
    )

    genome_links = _merge_unique(
        collect_payload_list(relevant_sorted, "genome_id"),
    )

    fitness_links = _merge_unique(
        collect_payload_list(relevant_sorted, "fitness_id"),
    )

    experiment_links = _merge_unique(
        collect_payload_list(relevant_sorted, "experiment_id"),
    )

    evidence_refs = _merge_unique(
        collect_evidence_refs(relevant_sorted),
        collect_payload_list(relevant_sorted, "evidence_id"),
        collect_payload_list(relevant_sorted, "evidence_refs"),
    )

    authority = _latest_payload_value(
        relevant_sorted,
        "authority",
        _latest_payload_value(relevant_sorted, "authorization"),
    )

    if not isinstance(authority, dict):
        authority = {}

    return {
        "decision_id": decision_id,
        "status": derive_decision_status(relevant_sorted),
        "decision_type": derive_decision_type(relevant_sorted),
        "question": question,
        "description": description,
        "scope": scope,
        "evidence_sufficiency": derive_evidence_sufficiency(relevant_sorted),
        "authorization_state": derive_authorization_state(relevant_sorted),
        "authority": authority,
        "next_gate": _latest_payload_value(relevant_sorted, "next_gate"),
        "next_gate_authorization": _latest_payload_value(
            relevant_sorted,
            "next_gate_authorization",
            _latest_payload_value(relevant_sorted, "next_gate_authorized"),
        ),
        "requirement_links": requirement_links,
        "candidate_links": candidate_links,
        "genome_links": genome_links,
        "fitness_links": fitness_links,
        "experiment_links": experiment_links,
        "alternatives": alternatives,
        "unknowns_accepted": unknown_accepted,
        "unknowns_rejected": unknown_rejected,
        "contradictions": contradiction_ids,
        "evidence_refs": evidence_refs,
        "epistemic_state": count_epistemic(relevant_sorted),
        "timeline": build_timeline(relevant_sorted),
        "provenance": latest.provenance,
        "sources": sorted({event.source for event in relevant_sorted}),
        "first_observed_at": relevant_sorted[0].timestamp,
        "updated_at": latest.timestamp,
    }
```

---

# 4. Backend: gateway additions

Add to:

**`observatory/backend/gateway.py`**

Import:

```python
from .projections_decisions import (
    build_decision_detail,
    build_decisions_overview,
)
```

Add methods inside `ObservatoryGateway`:

```python
    async def decisions_overview(self) -> List[Dict[str, Any]]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            ALL_EVENT_CATEGORIES,
            20_000,
        )

        return build_decisions_overview(events)

    async def decision_detail(self, decision_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            ALL_EVENT_CATEGORIES,
            20_000,
        )

        detail = build_decision_detail(decision_id, events)

        if detail is None:
            raise NotFoundError(f"decision {decision_id} not found")

        return detail
```

---

# 5. Backend: API routes

Add to:

**`observatory/backend/api/routes.py`**

```python
@router.get("/decisions")
async def decisions_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.decisions_overview()


@router.get("/decisions/{decision_id}")
async def decision_detail(
    decision_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.decision_detail(decision_id)
```

---

# 6. Frontend: type additions

Append to:

**`observatory/frontend/lib/types.ts`**

```typescript
export interface DecisionSummary {
  decision_id: string;
  status: string;
  decision_type: string;
  question: string;
  evidence_sufficiency: string;
  authorization_state: string;
  next_gate: string | null;
  candidate_count: number;
  unknown_accepted_count: number;
  unknown_rejected_count: number;
  contradiction_count: number;
  evidence_count: number;
  updated_at: string | null;
}

export interface DecisionAlternative {
  candidate_id: string;
  outcome: string;
  reason: string | null;
  fitness_links: string[];
  evidence_refs: string[];
  updated_at: string | null;
}

export interface DecisionDetail {
  decision_id: string;
  status: string;
  decision_type: string;
  question: string;
  description: string | null;
  scope: string[];
  evidence_sufficiency: string;
  authorization_state: string;
  authority: Record<string, unknown>;
  next_gate: string | null;
  next_gate_authorization: string | null;
  requirement_links: string[];
  candidate_links: string[];
  genome_links: string[];
  fitness_links: string[];
  experiment_links: string[];
  alternatives: DecisionAlternative[];
  unknowns_accepted: string[];
  unknowns_rejected: string[];
  contradictions: string[];
  evidence_refs: string[];
  epistemic_state: EpistemicCounts;
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}
```

---

# 7. Frontend: API client additions

Add to the `api` object in:

**`observatory/frontend/lib/api.ts`**

```typescript
  decisions(): Promise<DecisionSummary[]> {
    return request<DecisionSummary[]>("/observatory/decisions");
  },

  decisionDetail(decisionId: string): Promise<DecisionDetail> {
    return request<DecisionDetail>(
      `/observatory/decisions/${encodeURIComponent(decisionId)}`
    );
  }
```

Update the type import in `api.ts`:

```typescript
import type {
  DashboardState,
  DecisionDetail,
  DecisionSummary,
  EvidenceRecord,
  EvolutionState,
  ExperimentDetail,
  ExperimentSummary,
  FitnessDetail,
  FitnessSummary,
  GenomeDetail,
  GenomeSummary,
  GovernanceState,
  KnowledgeMemory,
  KnowledgeSubjectSummary,
  OverviewState,
  RequirementSummary,
  RequirementTrace,
  RuntimeState,
  TimelineEntry
} from "./types";
```

---

# 8. Frontend: decision list page

Create:

**`observatory/frontend/app/decisions/page.tsx`**

```typescript
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { DecisionSummary } from "@/lib/types";

export default function DecisionsPage() {
  const [items, setItems] = useState<DecisionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.decisions();
      setItems(nextItems);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !items) {
    return <div className="error">Decisions unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading decisions…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.decision_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Selection / Decisions">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter decisions"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No decisions visible. Emit decision or selection events to populate
            this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.decision_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/decisions/${item.decision_id}`}>
                    {item.decision_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">{item.question}</div>

                <div className="timeline-meta">
                  <span>type {item.decision_type}</span>
                  <span>sufficiency {item.evidence_sufficiency}</span>
                  <span>authorization {item.authorization_state}</span>
                  <span>next gate {item.next_gate ?? "unknown"}</span>
                  <span>candidates {item.candidate_count}</span>
                  <span>unknowns accepted {item.unknown_accepted_count}</span>
                  <span>unknowns rejected {item.unknown_rejected_count}</span>
                  <span>contradictions {item.contradiction_count}</span>
                  <span>evidence {item.evidence_count}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
```

---

# 9. Frontend: decision detail page

Create:

**`observatory/frontend/app/decisions/[id]/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { DecisionDetail } from "@/lib/types";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export default function DecisionDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [decision, setDecision] = useState<DecisionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextDecision = await api.decisionDetail(params.id);
      setDecision(nextDecision);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, [params.id]);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !decision) {
    return <div className="error">Decision unavailable: {error}</div>;
  }

  if (!decision) {
    return <div className="muted">Loading decision…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Decision ${decision.decision_id}`}
        right={<StatusPill status={decision.status} />}
      >
        <KeyValue
          data={{
            type: decision.decision_type,
            evidence_sufficiency: decision.evidence_sufficiency,
            authorization_state: decision.authorization_state,
            next_gate: displayValue(decision.next_gate),
            next_gate_authorization: displayValue(
              decision.next_gate_authorization
            ),
            updated_at: displayValue(decision.updated_at),
            first_observed_at: displayValue(decision.first_observed_at)
          }}
        />
      </Section>

      <Section title="Decision Question">
        {decision.question ? (
          <div>{decision.question}</div>
        ) : (
          <div className="empty">No decision question recorded</div>
        )}
      </Section>

      <Section title="Description">
        {decision.description ? (
          <div>{decision.description}</div>
        ) : (
          <div className="empty">No description recorded</div>
        )}
      </Section>

      <Section title="Scope">
        {decision.scope.length === 0 ? (
          <div className="empty">No scope recorded</div>
        ) : (
          <ul className="list">
            {decision.scope.map(scopeItem => (
              <li key={scopeItem}>{scopeItem}</li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Alternatives">
        {decision.alternatives.length === 0 ? (
          <div className="empty">No alternatives recorded</div>
        ) : (
          <ul className="timeline">
            {decision.alternatives.map(alternative => (
              <li key={alternative.candidate_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{alternative.candidate_id}</span>
                  <StatusPill status={alternative.outcome} />
                </div>

                {alternative.reason ? (
                  <div className="timeline-summary">{alternative.reason}</div>
                ) : null}

                <div className="timeline-meta">
                  <span>fitness links {alternative.fitness_links.length}</span>
                  <span>evidence {alternative.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Authority">
          <KeyValue data={decision.authority} />
        </Section>

        <Section title="Epistemic State">
          <KeyValue data={decision.epistemic_state} />
        </Section>
      </div>

      <div className="grid grid-2">
        <Section title="Unknowns Accepted">
          {decision.unknowns_accepted.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.unknowns_accepted.map(unknownId => (
                <li key={unknownId}>{unknownId}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Unknowns Rejected">
          {decision.unknowns_rejected.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.unknowns_rejected.map(unknownId => (
                <li key={unknownId}>{unknownId}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Contradictions">
        {decision.contradictions.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <ul className="list">
            {decision.contradictions.map(contradictionId => (
              <li key={contradictionId}>{contradictionId}</li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Linked Requirements">
          {decision.requirement_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.requirement_links.map(requirementId => (
                <li key={requirementId}>
                  <a href={`/requirements/${requirementId}`}>{requirementId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Linked Genomes">
          {decision.genome_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.genome_links.map(genomeId => (
                <li key={genomeId}>
                  <a href={`/genomes/${genomeId}`}>{genomeId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <div className="grid grid-2">
        <Section title="Linked Fitness">
          {decision.fitness_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.fitness_links.map(fitnessId => (
                <li key={fitnessId}>
                  <a href={`/fitness/${fitnessId}`}>{fitnessId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Linked Experiments">
          {decision.experiment_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {decision.experiment_links.map(experimentId => (
                <li key={experimentId}>
                  <a href={`/experiments/${experimentId}`}>{experimentId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Evidence References">
        {decision.evidence_refs.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <ul className="list">
            {decision.evidence_refs.map(evidenceId => (
              <li key={evidenceId}>
                <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Decision Timeline">
        <EventTimeline items={decision.timeline} />
      </Section>
    </div>
  );
}
```

---

# 10. Add Decisions to navigation

Update the navigation block in:

**`observatory/frontend/app/layout.tsx`**

```tsx
          <nav className="app-nav">
            <a href="/">Overview</a>
            <a href="/runtime">Runtime</a>
            <a href="/requirements">Requirements</a>
            <a href="/knowledge">Knowledge</a>
            <a href="/experiments">Experiments</a>
            <a href="/fitness">Fitness</a>
            <a href="/genomes">Genomes</a>
            <a href="/decisions">Decisions</a>
            <a href="/governance">Governance</a>
          </nav>
```

---

# 11. Decision event contract

The Selection / Decision view depends on explicit decision events.

Recommended event types:

```text
decision_proposed
decision_evaluated
decision_recorded
decision_authorized
decision_rejected
decision_blocked
selection_recorded
selection_evaluated
candidate_selected
candidate_rejected
candidate_evaluated
unknown_accepted
unknown_rejected
contradiction_blocking
authorization_updated
```

Recommended identifiers:

```text
DEC-D29-001
SEL-D24-001
AUTH-D30-001
GATE-D29
```

---

## Example: propose a decision

```python
await adapter.observe(
    category="governance",
    type="decision_proposed",
    subject_id="DEC-D29-001",
    payload={
        "decision_id": "DEC-D29-001",
        "decision_type": "evolution_decision",
        "decision_question": "Is evidence sufficient to authorize the next bounded evolution step?",
        "objective_id": "VS1-OBJ-001",
        "scope": [
            "definition-only",
            "no-execution",
        ],
        "summary": "D29 decision proposed",
    },
)
```

---

## Example: evaluate evidence sufficiency

```python
await adapter.observe(
    category="governance",
    type="decision_evaluated",
    subject_id="DEC-D29-001",
    payload={
        "decision_id": "DEC-D29-001",
        "evidence_sufficiency": "sufficient_for_definition",
        "unknown_count": 6,
        "contradiction_count": 0,
        "summary": "Evidence sufficient for definition, not execution",
    },
    epistemic_status="inferred",
)
```

---

## Example: record a selection decision

```python
await adapter.observe(
    category="governance",
    type="selection_recorded",
    subject_id="SEL-D24-001",
    payload={
        "decision_id": "SEL-D24-001",
        "selection_id": "SEL-D24-001",
        "decision_type": "architecture_selection",
        "candidates": [
            {
                "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
                "outcome": "selected"
            },
            {
                "candidate_id": "vs1-obj001-candidate-a046c88a2460",
                "outcome": "rejected"
            },
            {
                "candidate_id": "vs1-obj001-candidate-f98815eb19e9",
                "outcome": "rejected"
            }
        ],
        "selected_candidate": "vs1-obj001-candidate-313b071dd7d4",
        "summary": "D24 architecture selection recorded",
    },
)
```

---

## Example: accept unknowns in a decision

```python
await adapter.observe(
    category="governance",
    type="unknown_accepted",
    subject_id="DEC-D29-001",
    payload={
        "decision_id": "DEC-D29-001",
        "unknown_id": "UNKNOWN-SC08",
        "reason": "UI evidence is not required for definition-only authorization.",
        "summary": "Unknown SC08 accepted for D29 definition scope",
    },
)
```

---

## Example: reject unknowns

```python
await adapter.observe(
    category="governance",
    type="unknown_rejected",
    subject_id="DEC-D29-001",
    payload={
        "decision_id": "DEC-D29-001",
        "unknown_id": "UNKNOWN-PRODUCTION-SECURITY",
        "reason": "Production security unknowns cannot be accepted for execution.",
        "summary": "Production security unknown rejected",
    },
)
```

---

## Example: record decision authorization

```python
await adapter.observe(
    category="governance",
    type="decision_authorized",
    subject_id="DEC-D29-001",
    payload={
        "decision_id": "DEC-D29-001",
        "authorization_state": "granted",
        "authority": {
            "evolution": "definition_only",
            "implementation": "none",
            "runtime": "none",
            "deployment": "none",
            "production": "none"
        },
        "next_gate": "D30",
        "next_gate_authorization": "not_granted",
        "summary": "D29 decision authorized definition only",
    },
)
```

---

# 12. What this view establishes

The Selection / Decision view now exposes:

```text
decision identity
decision question
decision type
candidate alternatives
selection outcomes
evidence sufficiency
authorization state
authority grants
next gate authority
unknowns accepted
unknowns rejected
contradictions
linked requirements
linked genomes
linked fitness
linked experiments
evidence references
decision timeline
```

It preserves the constitutional boundary:

```text
The Observatory displays decision evidence.
It does not make decisions.
It does not grant authority.
It does not authorize execution.
```

---

# 13. Verification checklist

Before treating the Decision view as production-ready, verify:

```text
decisions endpoint returns empty list when no decision events exist
decision events populate the list
decision detail returns 404 for unknown decision ID
selection events render candidate alternatives
selected candidates render selected outcome
rejected candidates render rejected outcome
evidence sufficiency remains unknown unless explicitly recorded
authorization state remains unknown unless explicitly recorded
authority map renders only recorded authority
next gate renders only recorded next gate
unknowns accepted render
unknowns rejected render
contradictions render
requirement links resolve
genome links resolve
fitness links resolve
experiment links resolve
evidence links resolve
timeline renders newest first
UI does not make decisions
UI does not authorize gates
```

---

# 14. Next recommended step

The next surface should be the **Provenance / Audit view**.

That view should expose cross-cutting traceability:

```text
event identity
subject identity
actor/source
hash chain where available
upstream references
downstream references
evidence references
decision references
authority boundaries
integrity warnings
```

This would complete the Observatory’s accountability loop:

```text
Requirements
Knowledge
Experiments
Fitness
Genomes
Decisions
Governance
Provenance / Audit
```