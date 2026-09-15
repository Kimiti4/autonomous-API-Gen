# INC-01 Deployment Constraints (D36 T6)

Companion to D35 §11 and D31 §20-item-6. This document records EXTANT deployment
posture for the Observatory. It changes nothing. It authorizes nothing.

## B-001 — Reads are configuration-gated, not code-guaranteed

All `GET /observatory/*` read endpoints, `GET /observatory/stream` (SSE),
export, and audit-bundle carry no backend auth dependency. When
`OBSERVATORY_API_TOKEN` is set, writes are token-gated; reads remain
header-trust regardless. The frontend calls reads browser-direct.

Consequence: **do not expose the backend to any network where unauthenticated
reads would be a finding.** The intended posture is backend-on-loopback with
the Next.js proxy as the only remote surface (mutations), or an explicit
operator decision otherwise. This file does not make that decision.

## B-002 — Workspace identity is trusted-proxy

`X-Operator-*` headers are asserted by the Next.js workspaces proxy from the
server-side session. Anyone reaching the backend directly can assert any
operator identity. Mitigation exists ONLY if the backend is not directly
exposed (see B-001 posture above). Undeclared in-repo; operator-owned.

## B-003 — UI filtering is convenience, never boundary

Clearance-gated action lists, hidden buttons, and disabled notices improve
usability. Every security property is re-checked server-side (proxy) and/or
backend-side (deps, GovernanceBoundary, WorkspaceGovernor). Never argue
"the UI hides it, therefore it is safe."

## Non-boundaries (explicitly NOT established here)

No production command execution. No deployment authority. No certification.
No secret handling beyond intake-time redaction plus workspace secret-scan
(verbatim payload persistence per GAP-006 remains a known, deferred gap).
