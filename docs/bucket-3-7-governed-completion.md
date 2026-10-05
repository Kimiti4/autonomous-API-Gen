# Bucket 3.7 — Governed Project Continuation & Completion

Bucket 3.7 is a standalone governance layer for deciding whether ESAP still has
authorized work to perform on a project.

It is intentionally separate from Bucket 3.6 long-lived project memory. The
completion engine consumes explicit obligations and evidence; an integration
adapter may persist its outcomes later.

## State contract

An empty project is UNKNOWN, not COMPLETE.

A project becomes COMPLETE only when every registered obligation is CERTIFIED
with authoritative evidence and the remaining-work set is empty.

Advisory information never creates an obligation.

## Continuation rules

- Requirements, verified defects, explicit maintenance requests, regressions,
  and verification obligations may become work.
- Work without a governing obligation is rejected.
- Certification requires evidence, and that evidence must be authoritative.
- A regression adds a new regression obligation linked to the affected
  certification. The historical certification remains intact.
- Maintenance creates a new obligation without rewriting prior obligations.
- Completion is deterministic: remaining_obligation_ids == ().
- Once complete, is_stopped() is true. No feature generation should continue
  until a new governed maintenance/change request is added.

## Deliberate boundary

This module does not import app.engine.project_memory. That separation prevents
Bucket 3.7 from becoming a hidden mutation path for Bucket 3.6. A future
adapter can record completion/reopen outcomes into the append-only memory store
while preserving both contracts independently.
