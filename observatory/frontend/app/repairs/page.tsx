"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { RepairNotification, RepairState } from "@/lib/types";

export default function RepairsPage() {
  const [notifications, setNotifications] = useState<RepairNotification[]>([]);
  const [selected, setSelected] = useState<RepairState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.recentNotifications(30).then(setNotifications).catch((e) => setError(e.message));
  }, []);

  async function inspect(id: string) {
    try {
      const state = await api.repair(id);
      setSelected(state);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load repair");
    }
  }

  return (
    <div className="grid">
      <section className="section">
        <div className="section-header"><h2>Repair Notifications</h2><span className="muted">{notifications.length} recent</span></div>
        {error ? <div className="error">{error}</div> : null}
        {notifications.length === 0 ? <div className="empty">No repair notifications.</div> : null}
        {notifications.map((n) => (
          <button key={n.id} className="notification-row" onClick={() => inspect(n.repair_id)}>
            <strong>{n.title}</strong>
            <span>{n.message}</span>
            <small>{n.repair_id} · {n.severity}{n.action_required ? " · action required" : ""}</small>
          </button>
        ))}
      </section>

      {selected ? (
        <section className="section">
          <div className="section-header"><h2>Repair Investigation</h2><span>{selected.status}</span></div>
          <div className="grid grid-2">
            <div><strong>Repair</strong><p>{selected.repair_id}</p></div>
            <div><strong>Events</strong><p>{selected.events}</p></div>
          </div>
          {selected.report ? (
            <pre className="code-block">{JSON.stringify(selected.report, null, 2)}</pre>
          ) : <div className="empty">No repair report payload is available.</div>}
        </section>
      ) : null}
    </div>
  );
}
