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

The platform now provides the operator session boundary. The issued dashboard session has observation scope only; control-plane prefixes still require the existing control-scoped API-key authority. The dashboard login
POSTs the operator credential to same-origin `/auth/login`; the platform
validates it against `ADMIN_API_KEY` and returns a signed, HttpOnly,
SameSite=Lax session cookie. Subsequent observation and WebSocket requests use
that cookie and are authenticated by the canonical platform auth provider.

The dashboard must not embed an API key in JavaScript, runtime ConfigMaps,
URLs, or WebSocket query parameters. The credential is held only in the
login form while it is submitted over the same-origin HTTPS connection; it is
not persisted in browser storage.

Without a valid platform session, `/auth/session` and observation endpoints
return 401 and the UI remains at the login boundary rather than fabricating
state. Production cookies are marked Secure.

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
- the dashboard auth proxy targets `/api/v1/auth/`;
- the platform session is HttpOnly and signed;
- no platform credential appears in dashboard runtime ConfigMap;
- observation clients use same-origin credentials.
