# Observatory UI Spec

## Purpose

Let a human answer, on every screen: *what is happening, why, what is
known and unknown, what evidence supports it, what is allowed and
forbidden, what happened before, what happens next.* A screen that cannot
answer these is decorative, not operational.

## Information levels (exactly three)

```text
LEVEL 1 — SYSTEM STATE
Healthy / degraded / blocked · current activity · current authority

LEVEL 2 — DECISION STATE
Requirement · capability · evolution · evidence · governance

LEVEL 3 — RAW TRACE
events · hashes · timestamps · processes · tests · observations
```

Top layer comprehensible; drillable to evidence in ≤3 interactions.

## Screens

- **Overview** — cycle status, pipeline position, key figures with
  epistemic honesty (unknowns shown, not zeroed).
- **Live Runtime** — supervisor tree, process lineage/state/failures,
  live events. Clicking a process shows lineage and supervision history,
  not raw telemetry dumps.
- **Evolution** — request, epistemic state (known/partial/unknown),
  capability check, pipeline checklist, decision + authorization block.
- **Evidence** — drillable records: source → claim → result → scope →
  not-proven → provenance with per-link state.
- **Requirements / ISR** — requirement → constraint → capability →
  execution → observation → evidence → decision trace.
- **Experiments, Memory/Knowledge, Governance, System Health** — same
  three-level pattern; Governance is visually distinct (control room,
  not dashboard).

## Rules

1. No business/governance logic in components. Render authoritative
   backend answers only.
2. Epistemic states visually unconfusable (`unknown` ≠ `failed` ≠
   `not_applicable`; `not_measured` ≠ `0`).
3. Every material claim links to its evidence or its explicit unknown.
4. Stale/cached data carries a staleness marker.
5. Rejections, unknowns, and forbidden actions are rendered as
   first-class content, not empty states.
