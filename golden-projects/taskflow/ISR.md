# TaskFlow — Golden Coherence Application

## Purpose
TaskFlow is the first Golden Coherence Suite application for Tiannara ESAP. It is deliberately small enough to finish completely, but rich enough to exercise requirements → ISR → architecture → implementation → verification → deployment → observation → evidence.

## Scope
TaskFlow is a multi-user project and task management application.

### Required capabilities
1. User registration and authenticated login.
2. Workspace creation and workspace membership.
3. Roles: owner, manager, member.
4. Project creation within a workspace.
5. Task creation, assignment, status, priority and due date.
6. Task comments and activity history.
7. Search/filter tasks by project, assignee, status and priority.
8. Dashboard showing project/task summaries.
9. Audit trail for security-sensitive mutations.
10. Health and operational telemetry sufficient for deployment observation.

## Invariants
- A user can only access workspaces to which they belong.
- Workspace ownership cannot be transferred without an explicit governed operation.
- A task cannot reference a project outside the same workspace.
- A task assignee must belong to the task's workspace.
- Members cannot perform owner-only operations.
- Deleted/archived records must not silently reappear in active queries.
- Mutating operations must have deterministic authorization outcomes.
- Repeated idempotent requests must not create duplicate effects where the ISR marks the operation idempotent.
- Every security-sensitive mutation produces an auditable effect identity.

## Non-goals
- Payments.
- External LLM/AI features.
- Chat/social networking.
- Mobile-native clients.
- Unrequested integrations.

## Technology neutrality
The ISR must not require FastAPI, PostgreSQL, React, Next.js, Docker, Redis, AWS, Render, Vercel or any other implementation technology. Those are compilation/deployment choices.

## Completion rule
Tiannara must finish the required scope, verify it end-to-end and stop. Optional features may only be proposed after certification and must never be silently added to the required implementation.