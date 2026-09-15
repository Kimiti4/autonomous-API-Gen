# Observatory Governance Boundary

## Authority model

```text
OBSERVATORY AUTHORITY
    display, correlate, explain, request          → GRANTED (this layer)

EXECUTIVE AUTHORITY
    evolve, implement, deploy, repair, optimize   → NONE (never here)

HUMAN AUTHORITY
    approve, halt, authorize                      → via request_command/2
                                                    subject to backend checks
```

The UI is a **control surface, not an executive**. A button renders a
command request; the backend accepts or rejects it under the same
governance system that constrains every other actor. A rejected command
must be visible *as a rejection with reasons*, not as a silent no-op.

## Current authority snapshot (illustrative shape)

```text
CURRENT AUTHORITY
Interpretation       GRANTED
Evolution            NONE
Implementation       NONE
Optimization         NONE
Deployment           NONE
Production           NONE
```

The Governance screen renders this from the backend on every load. It
must never be hardcoded in the frontend.

## Active gates and human control

The screen exposes gate states (e.g. `D29 PASS / HOLD`, `D30 NOT
AUTHORIZED`) as read from governance state, plus human controls
(`SAFE MODE`, `STOP`, `RESTART`, `REQUEST AUTHORIZATION`) implemented
exclusively through `request_command/2`.

## Rules

1. No frontend policy logic. If the UI needs to know whether an action
   is allowed, it asks the backend (`getEvolutionDecision`-style query)
   and renders the authoritative answer.
2. No direct RPC to runtime subsystems from UI code. All crossings go
   through the gateway's command boundary.
3. Authorization states are data, rendered; they are never computed in
   components.
4. Every accepted command produces a traceable event with actor,
   authorization snapshot, and correlation ID.
5. Safe mode / stop must work even when projections are stale: the
   command path must not depend on UI-derived state.
6. Constitutional checks (e.g. gate-state blocks on evolution commands)
   are enforced in backend code, not documented intent. A command that
   the current gate state forbids must be rejected with reasons even if
   the UI offered it.
