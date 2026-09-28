# A09-009 — Operator Surface Security Boundary

The shipped React dashboard is a **read-only presentation surface**. It does not
make governance decisions, mutate candidates, certify artifacts, or maintain
an independent governance store.

## Canonical path

Browser requests use the same-origin `/observation/*` path. Dashboard nginx
rewrites that path to the versioned platform API:

`/observation/* -> /api/v1/observation/*`

This keeps the browser independent of internal Kubernetes DNS and preserves the
platform's canonical API version boundary.

## Authentication

The platform API remains the authentication authority. Dashboard runtime
configuration contains no API keys, bearer tokens, or other credentials.
Observation requests use same-origin credentials so an upstream authenticated
session/cookie can be forwarded to the platform API.

A production deployment MUST provide an authenticated gateway/session mechanism
that establishes the platform-recognized cookie before exposing the dashboard
to operators. The dashboard must not embed an API key in JavaScript, runtime
ConfigMaps, URLs, or WebSocket query parameters.

Until such an upstream identity/session mechanism is configured, the dashboard
is intentionally fail-closed: the platform returns 401 and the UI must treat
the observation as unavailable rather than fabricate state.

## Legacy Phase-28 dashboard

`constitutional_architecture/governance/dashboard/` remains a separate
reference/admin BFF for the Phase-28 kernel. It is **not** the authority for
the shipped `autonomous-api` governance subsystem and must not be presented
as the product governance control plane.

Its in-memory session implementation and demo users are therefore not used as
the authentication mechanism for the deployed React operator surface.

## Mutation boundary

The deployed React dashboard exposes observation only. Governance mutation
continues to require explicit platform control-plane APIs and their existing
authentication/governance gates.

## Verification pins

A09-009 tests assert:

- the dashboard proxy targets `/api/v1/observation/`;
- no platform credential appears in dashboard runtime ConfigMap;
- observation clients use same-origin credentials.
