# Bucket 4.3 — Granular project modes and scope control

Bucket 4.3 makes the requested project surface and lifecycle explicit before
ESAP plans or mutates software.

## Authoritative modes

ESAP supports these independently composable dimensions:

- project lifecycle: new project or existing project;
- project intent: create, maintain, or improve;
- software surface: frontend, backend, API contract, or whole application;
- bounded work mode: generate, maintain, improve, document, SEO, test,
  architecture, migrate, refactor, or cross-stack.

The three granular surface modes are valid for **both new and existing**
projects:

- frontend-only;
- backend-only;
- API-contract-only.

Existing-project-only modes remain fail-closed for new projects where the
operation inherently requires an existing system, including maintenance,
improvement, documentation, SEO, testing, migration, and refactoring.

## Scope rule

The selected project intent, work mode, and generation scope form one governed
capability contract. A mutation is executable only when its surface is allowed
by that contract.

A frontend-only request must not authorize backend or API-contract mutations.
The same rule applies symmetrically to backend-only and API-contract-only work.

Whole-application work is available only when the full application surface is
explicitly selected.

## New versus existing software

Granular surface selection does not imply an existing project. For example:

- new frontend-only application -> create + frontend-only;
- existing frontend maintenance -> maintain + frontend-only;
- new backend-only service -> create + backend-only;
- existing backend improvement -> improve + backend-only;
- new API-contract-only project -> create + API-contract-only;
- existing API contract improvement -> improve + API-contract-only.

This prevents the surface selector from accidentally becoming a lifecycle
permission.

## Anti-expansion rule

Discovering an issue outside the authorized surface does not expand the
scope. It is recorded as an advisory finding or as an unmet requirement that
must be separately authorized.

ESAP must follow:

requested scope -> necessary work -> implementation -> verification ->
certification -> stop.

Optional improvements remain advisory.

## Compatibility

Bucket 4.3 preserves Bucket 4.1 existing-codebase maintenance and Bucket 4.2
deployed-app observation/governed maintenance. Runtime evidence may inform
work, but it cannot change the authorized surface or project intent.

Windows/macOS generation and marketplace publication are outside Bucket 4.3.
Marketplace listing or selling remains human-authorized and deferred to the
final phase.
