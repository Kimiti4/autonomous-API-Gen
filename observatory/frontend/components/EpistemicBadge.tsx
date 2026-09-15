import type { EpistemicStatus } from "@/lib/types";

export function EpistemicBadge({ status }: { status: EpistemicStatus }) {
  const normalized = String(status || "unknown").toLowerCase();

  return (
    <span className={`epistemic epistemic-${normalized}`}>{normalized}</span>
  );
}
