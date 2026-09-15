# Observatory Test Strategy

Layered, in order, per capability:

```text
1.  unit
2.  property / invariant
3.  integration
4.  runtime
5.  API contract
6.  UI contract
7.  end-to-end
8.  failure-path
9.  authorization
10. provenance / integrity
```

## `request_command/2` matrix (required)

```text
authorized request       → accepted
unauthorized request     → rejected + reason
unknown capability       → rejected
blocked capability       → rejected
stale evidence           → rejected
tampered evidence        → rejected
safe-mode                → rejected
duplicate request        → idempotent accept
runtime unavailable      → explicit :unavailable
```

## Invariants (required properties)

- Reordered equivalent events → identical projection.
- Timestamp rendering never alters evidence identity.
- Unknowns never render as successes (property test over projections).
- Rejected commands always carry reasons.
- Reads never mutate (state-diff property test).

## Gates

Observatory quality gate: format, compile with warnings-as-errors,
static analysis, all ten layers above, WebSocket/event tests,
no-secrets, no mock data in production paths, no unauthorized mutation,
no fabricated metrics, no silent unknown→success conversion.

And: **green tests ≠ certification.** Tests establish defined claims;
certification stays a separate governance decision — same rule as D29.
