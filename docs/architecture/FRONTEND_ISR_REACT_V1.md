# ISR-driven frontend compiler v1

## Architecture

The canonical pipeline remains:

ISRRevision -> isr_to_plan -> CompilationPlan -> ReactFrontendBackend -> GeneratedRepository

The frontend emitter consumes only typed route, interaction, and API contracts preserved by ISR lowering. It does not infer routes from entity names or invent interaction flows.

## ISR semantics

- A frontend_route node carries a path, page title, and authentication requirement.
- A frontend_interaction node carries a label, action, and optional success message.
- CONTAINS associates an interaction with exactly one route.
- ROUTES_TO binds a route to an API operation.
- INVOKES binds an interaction to its target API operation.
- submit, refresh, and delete interactions must target an API node with an explicit ApiBehavior payload. The action must match the API method.
- Path parameters in an API contract must be declared in request_fields.
- Duplicate route paths, missing API contracts, and invalid action/method combinations fail during ISR revision construction.

## Generated output

The reference backend emits a React + TypeScript + Vite project, with:
- Route-driven page rendering and navigation.
- Forms derived from API request fields.
- API method/path calls derived from API contracts.
- Response/error status presentation.
- Vitest + Testing Library tests for route rendering and a real API interaction.
- A production build command that runs TypeScript checking and Vite bundling.

## Explicit limits

This v1 backend does not implement frontend authentication flows, role-aware UI authorization, arbitrary service calls, or automatic CRUD screen inference. Auth-required routes fail closed. API authorization remains a backend obligation; a frontend cannot safely establish authorization on its own.

## Verification

The frontend certification workflow materializes the generated repository, installs its declared dependencies, runs Vitest interaction tests, and executes a production build. A source-string check alone is not considered build evidence.
