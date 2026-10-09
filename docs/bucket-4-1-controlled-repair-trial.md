# Bucket 4.1 — controlled existing-codebase repair trial

## Purpose

Prove that ESAP can go beyond static defect detection and emit a minimal patch in a disposable copy of a pinned existing codebase, then verify the patch before any external mutation is considered.

## Inputs and isolation

- JamiiLink baseline: `550fe9d17a39495101a0dd371fe3367aab344708`.
- Known repaired reference used for comparison only: `e2f30012b6f7941057c55d09d322e51022a9ba9e`.
- The workflow copies only the app workspace into `fixtures/jamiilink-repair-trial`.
- The patch generator writes only inside that disposable workspace and emits a unified diff plus SHA-256 before/after hashes.
- No credentials are persisted for the target checkout. The workflow has read-only contents permissions and never pushes to JamiiLink.

## Repair rules in this trial

1. Associate each registration label with a stable input ID.
2. Make required Playwright field filling and submission unconditional, fill confirmation password, and assert the expected login route.
3. Capture and assert the registration request payload rather than accepting `/register` as success.

The generator is deliberately fail-closed: it requires exact baseline anchors and aborts if any expected anchor is missing or duplicated. The generated workspace is rescanned before lint/build/E2E are allowed to proceed.

## What this does and does not prove

This is a **deterministic, rule-guided repair trial**, not evidence of open-ended autonomous reasoning or a general-purpose code-editing agent. It validates a narrow controlled repair against known patterns. It must not be described as a full repository audit or general repair capability.

Release evidence must include:
- patch-generation report and diff;
- a clean targeted rescan;
- lint and production build;
- the full Playwright E2E suite on the generated trial workspace;
- retained artifacts with pinned source revisions.

Any write to the real JamiiLink repository remains out of scope and requires separate explicit human approval and review of the exact diff.
