# TaskFlow — Architecture Contract

This document is a compilation target description, not an implementation prescription.

## Logical boundaries
- Identity boundary: users, sessions and authentication policy.
- Tenant boundary: workspaces and membership authorization.
- Work-management boundary: projects and tasks.
- Collaboration boundary: comments and activity history.
- Query boundary: filtering, search and dashboard projections.
- Evidence boundary: audit events, effect identity and verification evidence.
- Operations boundary: health, metrics, structured logs and deployment probes.

## Required data relationships
workspace -> membership -> user
workspace -> project -> task
task -> assignee(user in same workspace)
task -> comments
workspace/project/task mutations -> audit/effect evidence

## Required behavioral properties
- Authorization is evaluated against current tenant membership.
- Cross-tenant references fail closed.
- Mutations have explicit transaction/effect boundaries.
- Audit evidence is generated from actual executed effects.
- Query projections cannot become the authoritative source of domain truth.
- Runtime health must be distinguishable from build success.

## Verification traceability
Every required capability must map to:
REQ -> ISR -> architecture element -> implementation artifact -> test -> runtime observation -> evidence

## Compilation acceptance
A compiler may choose a modular monolith or multiple services if the selected architecture satisfies the ISR and quality gates. The implementation must not rewrite the ISR to accommodate an unsupported technology choice.