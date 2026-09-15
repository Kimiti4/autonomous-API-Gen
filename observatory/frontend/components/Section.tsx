import type { ReactNode } from "react";

export function Section({
  title,
  right,
  children
}: {
  title: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2>{title}</h2>
        {right ? <div className="section-right">{right}</div> : null}
      </div>

      <div className="section-body">{children}</div>
    </section>
  );
}
