function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export function KeyValue({ data }: { data: object }) {
  const entries = Object.entries(data || {});
  const rows: Array<[string, unknown]> = entries as Array<[string, unknown]>;

  if (entries.length === 0) {
    return <div className="empty">None</div>;
  }

  return (
    <dl className="key-value">
      {rows.map(([key, value]) => (
        <div key={key} className="key-value-row">
          <dt>{key}</dt>
          <dd>{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}
