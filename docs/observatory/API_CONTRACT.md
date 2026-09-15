# Observatory API Contract

Public surface. Anything not listed here is internal.

## Read-only views

```elixir
dashboard/0
overview/0
runtime/0
evolution/1
evidence/1
requirement/1
capability/1
knowledge/1
governance/0
timeline/1
health/0
```

Contract for every view function:

- `@spec` + `@doc` mandatory.
- Pure derivation from events/evidence; no I/O beyond bounded,
  explicitly declared reads.
- No side effects: no state change, no evolution trigger, no repair,
  no process start, no evidence write.
- Partial availability is explicit: `{:error, :unavailable | :timeout |
  :invalid_response | :process_crashed}` — never a silent `{}` or `0`.

## Event ingestion

```elixir
observe/1
observe_many/1
```

Asynchronous, non-blocking, bounded. Returns acknowledgement of receipt,
not of processing. Ordering guarantees (if any) must be documented per
source; the projection layer must not assume global ordering.

## Live subscription

```elixir
subscribe/1
unsubscribe/1
```

Delivers canonical events to subscribers. Dropped/stale delivery must be
signalled (`:stale`, `:gap_detected`), never hidden.

## Human-control boundary

```elixir
request_command/2
```

The **only** path from human intent to system action. Semantics:

```text
request → validate → authorization check → constitutional check →
capability check → ACCEPTED | REJECTED → event in both cases
```

Rejections are first-class results with reasons, visible in the UI.
Duplicate requests are idempotent. There is no `start_evolution/1`-style
direct executive; adding one is a constitutional change.

## Traceability

```elixir
trace/1
explain/1
```

- `trace/1` returns the ID/hash chain for a subject, with gaps marked.
- `explain/1` returns decision + supporting evidence IDs + unknowns +
  contradictions + authorization snapshot + human-readable reason.

Example shape:

```elixir
%{
  decision: :advance,
  class: :e1_definition_only,
  supported_by: ["EVD-001", "D29"],
  unknowns: ["SC01", "SC06"],
  contradictions: [],
  authorization: %{evolution: :none, implementation: :none,
                   runtime: :none, production: :none},
  reason: "Evidence sufficient for analytical definition only"
}
```

## Versioning

Breaking changes to any of the above require a contract version bump and
a migration note. The UI must declare the contract version it speaks.
