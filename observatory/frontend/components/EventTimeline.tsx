import type { TimelineEntry } from "@/lib/types";

import { EpistemicBadge } from "./EpistemicBadge";

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return date.toLocaleString();
}

export function EventTimeline({ items }: { items: TimelineEntry[] }) {
  if (items.length === 0) {
    return <div className="empty">No events</div>;
  }

  return (
    <ul className="timeline">
      {items.map(item => (
        <li key={item.event_id} className="timeline-item">
          <div className="timeline-top">
            <span className="timeline-time">
              {formatTimestamp(item.timestamp)}
            </span>

            <EpistemicBadge status={item.epistemic_status} />
          </div>

          <div className="timeline-summary">{item.summary}</div>

          <div className="timeline-meta">
            <span>{item.category}</span>
            <span>{item.type}</span>
            <span>{item.subject_id}</span>
            <span>{item.severity}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
