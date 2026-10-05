"use client";

import { useEffect, useState } from "react";
import type { RepairNotification } from "@/lib/repair-types";
import { useEventTimeline } from "@/lib/use-event-stream";

export function useRepairNotifications(limit = 30) {
  const { items, connected } = useEventTimeline(Math.max(limit * 2, 60));
  const [notifications, setNotifications] = useState<RepairNotification[]>([]);

  useEffect(() => {
    const repairEvents = items.filter(item => item.type === "repair_report");
    setNotifications(repairEvents.slice(0, limit).map(item => {
      const status = String(item.summary).toLowerCase();
      const action = status.includes("blocked") || status.includes("authorization");
      return {
        id: item.event_id,
        severity: item.severity,
        title: action ? "Repair action required" : "Repair update",
        message: item.summary,
        repair_id: item.subject_id,
        action_required: action,
        deployment_authorization_required: status.includes("authorization")
      };
    }));
  }, [items, limit]);

  return { notifications, connected };
}
