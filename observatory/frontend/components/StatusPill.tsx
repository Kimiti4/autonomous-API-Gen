export function StatusPill({ status }: { status: string }) {
  const normalized = String(status || "unknown")
    .toLowerCase()
    .replaceAll(" ", "-");

  return <span className={`pill pill-${normalized}`}>{normalized}</span>;
}
