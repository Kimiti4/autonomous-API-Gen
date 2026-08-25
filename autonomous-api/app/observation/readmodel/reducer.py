"""CompositeObservationReducer -- platform fold, heartbeat no-op."""
from __future__ import annotations

def initial_state():
    return {"facets": {}, "meta": {"generation": 0, "facetUpdatedAt": {}}}

FACET_FOR_EVENT = {
    "fitness.evaluated": "fitness",
    "candidate.promoted": "candidates",
    "governance.decision_made": "governance",
    "isr.updated": "isr",
    "evolution.stage_changed": "evolution",
}

class CompositeObservationReducer:
    def fold(self, state, envelope):
        facet = FACET_FOR_EVENT.get(envelope.eventType)
        if not facet:
            return state
        facets = dict(state["facets"])
        if facet == "candidates":
            lst = list(facets.get("candidates", []))
            cid = getattr(envelope.payload, "get", lambda k, d=None: None)("candidateId") if isinstance(envelope.payload, dict) else getattr(envelope.payload, "candidateId", None)
            idx = next((i for i, c in enumerate(lst) if isinstance(c, dict) and c.get("candidateId") == cid), -1)
            if idx >= 0:
                lst[idx] = envelope.payload
            else:
                lst.append(envelope.payload)
            facets["candidates"] = lst
        elif facet == "governance":
            facets["governance"] = list(facets.get("governance", [])) + [envelope.payload]
        else:
            facets[facet] = envelope.payload
        meta = dict(state["meta"])
        meta["generation"] = envelope.generation
        meta["facetUpdatedAt"] = dict(meta.get("facetUpdatedAt", {}))
        meta["facetUpdatedAt"][facet] = envelope.occurredAt
        return {"facets": facets, "meta": meta}
