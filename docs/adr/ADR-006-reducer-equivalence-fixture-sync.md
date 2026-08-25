# ADR-006: Cross-Language Reducer-Equivalence Fixture Sync

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-24 |
| Relates to | ADR-004 (live-projection sync), ADR-001 (POC v1.1) |
| Scope | `autonomous-api/tests/observation/test_reducer_equivalence.py`, `observation-client/src/reducer.ts`, `observation-client/tests/reducer.vectors.test.ts`, `reducer_vectors.json` |

## Context

`LiveProjection` hydration is sound only if the client-side fold is **behaviorally identical** to the platform's `CompositeObservationReducer`. The fold exists twice by necessity: Python on the platform, TypeScript in `observation-client`. The constitution demands correctness and testability; hydration is the recovery path whose failure mode is silent state divergence — the worst kind, because the dashboard would render a plausible but wrong architecture.

## Problem

Two independent implementations of one semantic contract **will drift** — and already had. While constructing the equivalence vectors, a real divergence was discovered: the TS reducer updated `meta.generation` for heartbeats/unknown events, while the platform reducer returns state unchanged for them. Invisible at zero-generation, corrupting otherwise. The problem is therefore not "test equivalence once" but **make drift impossible to ship**, in both directions, permanently, without coupling the two build systems at runtime.

## Decision

A **canonical fixture** — `reducer_vectors.json` — with one-directional production and bidirectional verification:

1. **Vectors are curated canonical event sequences** (`_CANONICAL_EVENTS`), each including a deliberate **drift-detector** (`heartbeat_noop_nonzero_generation` uses generations 7 and 8 specifically to expose the discovered bug).
2. **Python is the producer of truth**: `_build_vectors()` folds each vector through `CompositeObservationReducer` and emits `{events, expected}`.
3. **A freshness test enforces sync**: `test_client_vectors_fixture_in_sync` recomputes the fixture; on mismatch it rewrites the file and *fails*, forcing a human to review and commit. Regeneration is a developer-local act with a visible diff — semantic changes surface in code review.
4. **TypeScript is a pure consumer**: `reducer.vectors.test.ts` loads the committed fixture and asserts `observationReducer` reproduces `expected` for every vector.
5. **CI never writes fixtures**: Python runs in verify mode; only a developer regenerates. The PR diff of `reducer_vectors.json` is itself the review artifact.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Runtime equivalence check (client hashes its state, compares with server's AM-3 anchor) | Detects drift only in production, after the user sees wrong data; also currently deferred because the server anchor is a log summary, not domain state |
| Port one reducer into the other's language and test both there | Creates a third implementation to maintain; defeats the point of verifying the *actual* shipped code |
| Cross-language property-based testing via subprocess/FFI | Couples the two toolchains at test time; flaky CI; property generators still need a shared notion of "expected" — which is exactly what the fixture provides |
| Golden-master on only one side | Verifies stability, not equivalence — both sides could be stably wrong in different ways |
| Generate random vectors on each run | Non-deterministic; failures hard to reproduce; no reviewable artifact. Curated vectors are small, targeted, and include known bug shapes |

## Trade-offs

- **Curated vectors have bounded coverage** — accepted: they encode the *semantic contract* (upsert, append, no-op, meta rules), and the corpus grows when new facet semantics are added.
- **Manual regeneration step** — deliberate: a changing fixture means changing fold semantics, which deserves human eyes.
- **JSON as interchange** — slightly verbose, but universal, diffable, and language-neutral; deterministic serialization (`sort_keys`, fixed formatting) removes false diffs.
- **Python designated producer** — arbitrary but fixed; the platform's fold is the authoritative one because the platform owns canonical state.

## Benefits

1. Drift is caught **at test time, in PRs**, in both languages — the discovered heartbeat bug is now permanently guarded.
2. Single source of truth: neither reducer can silently become the outlier.
3. The fixture diff is a **reviewable record of semantic evolution** — documentation that cannot go stale because CI enforces it.
4. No runtime or build-time coupling between the Python and TypeScript toolchains.

## Risks

| Risk | Mitigation |
|---|---|
| A developer regenerates the fixture mechanically without understanding the semantic change | The freshness test's failure message instructs review; PR review culture treats fixture diffs as semantic changes |
| Serialization-format drift (float formatting, key order) produces false failures | `sort_keys=True` + deterministic formatting; both suites compare parsed structures, not raw strings |
| Vector corpus stagnates | Every new facet handler or meta rule must add a vector — enforced by review checklist |

## Future evolution considerations

- Expand the corpus with property-derived vectors (generate, verify, then commit the survivors).
- Version the fixture schema (`"schemaVersion": 1`) so format evolution is explicit.
- When the platform materializes as-of-sequence domain state (AM-3 anchor upgrade), add a **runtime integrity check** layered on top of — not replacing — this build-time guarantee.
