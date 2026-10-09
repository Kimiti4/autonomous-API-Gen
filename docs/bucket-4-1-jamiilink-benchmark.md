# Bucket 4.1 — JamiiLink existing-codebase benchmark

This benchmark uses the public repository Kimiti4/iyf-s10-week-12-Kimiti4 as an external, read-only test subject. It does not push to or mutate that repository.

## Pinned inputs

- Baseline: 550fe9d17a39495101a0dd371fe3367aab344708 (the test repository's recorded main head when this benchmark was authored).
- Repaired candidate: e2f30012b6f7941057c55d09d322e51022a9ba9e (branch esap/existing-codebase-e2e-repair-2026-10).
- Primary paths:
  - iyf-s10-week-09-Kimiti4/src/pages/RegisterPage.jsx
  - iyf-s10-week-09-Kimiti4/e2e/journeys/jn-01.register-feed-discover-profile-alerts.spec.js

## Known defects used as the benchmark oracle

1. **Unassociated registration labels** — baseline labels do not declare htmlFor and their sibling inputs do not declare matching IDs. This makes label-based automation unreliable and harms accessible name association.
2. **Conditional E2E interactions** — the baseline journey conditionally fills fields only when isVisible() is true, silently allowing an action to be skipped.
3. **Permissive journey outcome** — the baseline accepts /register as a successful destination after submitting the form, so a failed registration can still satisfy the outcome assertion.

The scanner emits evidence-bearing candidate findings with path, line, rule, and source excerpt. It does not treat a heuristic as proof of a runtime defect, does not execute the source, and does not apply a repair.

## Required candidate evidence

- The three benchmark findings appear in the pinned baseline at the expected files.
- The same findings are absent from those files in the pinned repaired candidate.
- Candidate frontend lint, production build, and Playwright E2E regression suite pass.
- The JSON artifact records scan digests, source-file counts, findings, evidence excerpts, and per-check verdicts.

## Scope and limits

The scan inventory consists of Git-tracked files with supported source extensions, excluding dependency/build/output directories. It is not a complete audit of configuration, deployment, secrets, infrastructure, or runtime behavior. The full_repository_audit_claimed field must remain false. Candidate regression tests validate the pinned repaired reference; they do not yet prove ESAP independently generated that repair. Human review and governed mutation remain required before any actual target-repository change.
