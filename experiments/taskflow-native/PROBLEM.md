# TaskFlow Problem Specification

Build a multi-user task-management web application for teams.

Users must be able to register and authenticate, create workspaces, belong to workspaces with owner/manager/member roles, create projects, create and assign tasks, change task status and priority, set due dates, comment on tasks, inspect activity history, search/filter tasks, and view a useful workspace dashboard.

Security and correctness requirements:

- A user can access only workspaces to which they belong.
- Cross-workspace reads and writes fail closed.
- An assignee must belong to the task's workspace.
- Owner-only operations cannot be performed by ordinary members.
- Task/project/workspace relationships remain consistent.
- Archived records do not reappear in normal active queries.
- Authorization outcomes are deterministic and fail closed.
- Requests explicitly declared idempotent do not create duplicate effects.
- Security-sensitive mutations have a unique auditable effect identity.
- Authentication sessions can be invalidated and invalidated sessions cannot continue to authorize requests.

Operational requirements:

- Expose health/readiness information.
- Produce structured operational/audit evidence.
- Support repeatable automated verification.
- Be deployable in a reproducible environment.
- Preserve enough provenance to trace each certified capability back to the specification.

Non-goals:

- payments
- external AI/chat features
- social networking
- native mobile applications
- integrations not required by the problem

The implementation technology is intentionally unspecified. ESAP must choose an architecture and technology stack based on the requirements and its available compiler capabilities.
