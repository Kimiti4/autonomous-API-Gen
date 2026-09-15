"use client";

import { useEffect, useState } from "react";

import type { ObservatoryEvent, TimelineEntry } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ?? "http://127.0.0.1:8000";

function eventToTimelineEntry(event: ObservatoryEvent): TimelineEntry {
  const summary =
    typeof event.payload?.summary === "string"
      ? event.payload.summary
      : `${event.type}: ${event.subject_id}`;

  return {
    event_id: event.id,
    timestamp: event.timestamp,
    category: event.category,
    type: event.type,
    subject_id: event.subject_id,
    epistemic_status: event.epistemic_status,
    severity: event.severity,
    summary
  };
}

export function useEventTimeline(limit = 100) {
  const [items, setItems] = useState<TimelineEntry[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/observatory/stream`);

    source.onopen = () => {
      setConnected(true);
    };

    source.onerror = () => {
      setConnected(false);
    };

    source.onmessage = message => {
      try {
        const event = JSON.parse(message.data) as ObservatoryEvent;
        const entry = eventToTimelineEntry(event);

        setItems(previous => [entry, ...previous].slice(0, limit));
      } catch {
        // Ignore malformed stream payloads.
      }
    };

    return () => {
      source.close();
    };
  }, [limit]);

  return {
    items,
    connected
  };
}
