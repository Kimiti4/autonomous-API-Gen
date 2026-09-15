# Observatory Definition of Done

A feature is complete only when it has passed every stage:

```text
FUNCTIONAL
    ↓ real backend data, real evidence references,
      real authorization state, real event timeline
TESTED
    ↓ TEST_STRATEGY.md layers applicable to the feature
OBSERVABLE
    ↓ failure state rendered, unknown state rendered,
      no fake fallback data (verified, not asserted)
TRACEABLE
    ↓ every claim links to evidence or explicit unknown
AUTHORIZED
    ↓ command paths governed; reads side-effect free
FAILURE-COMPLETE
    ↓ crash/overflow/stale/unavailable paths defined and tested
DOCUMENTED
    ↓ spec, API entries, and this checklist updated
```

Worked example — the Evolution page is done when evolution data,
evidence references, authorization state, timeline, failure and unknown
states are all real and rendered, no fallback data exists, and the full
chain is E2E-verified.

A screen that renders but cannot answer the nine operational questions
in `UI_SPEC.md` is not done; it is a mock with styling.
