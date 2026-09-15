# Observatory Architecture

## Position

A single **application layer** above the existing observation sources
(`Tiannara.Omega.Observatory`, `Tiannara.Observatory`, Sentinel/ASC/
Crucible/reality observatories). It unifies; it does not replace on day
one.

```text
                    OBSERVATORY UI
                           │
                    WebSocket / API
                           │
                   OBSERVATORY GATEWAY
              (event model · queries · commands
               · evidence projection)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   RUNTIME            EVOLUTION           EVIDENCE
 supervisors         compiler /        provenance /
 processes           candidates         hashes
 telemetry           validation
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                 Existing subsystems
                 (adapted, not deleted)
```

## Rules

1. **UI consumes the canonical event/read model only.** It must not know
   about individual BEAM subsystems, GenServer names, or database schemas.
2. **Existing modules are adapted first.** The gateway acts as an
   adapter/aggregator over current sources (`Tiannara.Omega.Observatory`,
   `Tiannara.Observatory`, Sentinel/ASC/Crucible/reality observatories),
   normalizing their states into the canonical `Event` stream (see
   `EVENT_MODEL.md`). Inventory + consolidation analysis precedes any new
   module. Deletion of a legacy module requires its own authorization
   after the gateway demonstrably covers its surface.
3. **New capabilities attach to the gateway**, never as parallel
   observatories. A second dashboard is a defect, not a feature.
4. **Projections are pure functions** of event streams (see
   `CODE_QUALITY.md`). Deterministic input → deterministic projection,
   which makes the UI replayable and the evidence auditable.
5. **Ingestion is asynchronous and non-blocking.** Runtime emits events
   without waiting for projection or UI (cast/buffered, never
   call-and-wait on the emission path; synchronous `GenServer.call` is
   acceptable for query paths only). Bounded buffers protect runtime
   memory; overflow policy (drop-oldest with counter) must be visible,
   never silent.
6. **Failure isolation.** If the Observatory crashes, the runtime must
   continue safely: buffer → restart → replay → resume. The Observatory
   is never a single point of failure for the cognitive runtime.
7. **Reads have no side effects.** Query paths (`dashboard/0`,
   `trace/1`, `explain/1`, …) must not change state, trigger evolution,
   repair anything, or write production data.

## Conformance

Any new observation source must provide:

- a stable source identity,
- events in (or adaptable to) the canonical envelope,
- stable subject IDs enabling `trace/1`,
- explicit unavailability signalling (`:unavailable`, `:timeout`,
  `:invalid_response`, `:process_crashed`) rather than silent defaults.
