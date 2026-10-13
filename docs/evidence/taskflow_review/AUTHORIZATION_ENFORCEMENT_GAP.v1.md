# TaskFlow Authorization Enforcement Gap — v1

Status: **BLOCKED — audit finding, not certification**

Branch: `review/taskflow-group-1-kimityr-clean`

## Finding

The current FastAPI hexagonal backend does not implement TaskFlow workspace isolation or role-based authorization. Its generated API dependency performs optional API-key comparison only. The resource routers apply that dependency at router level, while service and repository operations are not scoped by workspace or actor identity.

This is not sufficient to enforce the reviewed TaskFlow authorization semantics.

## Source evidence inspected

- `tiannara/application/compiler/fastapi_hexagonal_backend.py`
  - `_deps_py`: generated `verify_api_key` checks `AUTH_REQUIRED`, `settings.api_key`, and `X-API-Key`; it does not resolve an authenticated actor, workspace membership, or role.
  - `_routes_py`: list/create/get/delete routes use a router-level `Depends(auth_dependency)`; handlers call `service.list()`, `service.create(...)`, `service.get(id)`, and `service.delete(id)` without workspace/actor scope.
  - `_services_py`: service methods pass through to repository operations without authorization context.
  - `_memory_repositories_py`: records are stored and queried by entity ID only; list returns all stored values.
- `tiannara/domain/models/authorization_semantic_obligations.py`
  - Converts the two reviewed authorization ledger values to an immutable, graph-bound typed object and computes a canonical digest.
  - The module explicitly does not claim runtime enforcement.
- `tiannara/application/compiler/project_compiler.py`
  - With `taskflow_semantic_gate=True`, compilation fails closed after typed ISR validation and before requirement derivation/backend planning. Even when obligations are present, the compiler blocks because no registered backend/runtime consumer proves enforcement.
- `tiannara/domain/models/backend_declaration.py`
  - `CompilationRequirement` currently carries artifact kind, required capabilities, and subject reference; it has no authorization-obligation field or enforcement attestation.

## Consequences

1. Do not mark either authorization semantic path as consumed by a runtime enforcement point.
2. Do not infer workspace scoping or role permissions from API-key authentication.
3. Do not authorize TaskFlow generation or certification on the basis of the typed contract or generated-code presence alone.
4. Do not invent unspecified policy details. The reviewed authorization payloads must be mapped into explicit, validated semantics before backend behavior is implemented.

## Required implementation and evidence

- Define a typed authorization enforcement contract between semantic resolution, backend compilation, and generated runtime.
- Validate the required structure and meaning of workspace and role policies without defaulting missing rules.
- Generate workspace-aware identity/membership checks and role/permission checks at the application boundary and ensure repository queries are scoped to the authorized workspace.
- Add generated-application tests for cross-workspace reads, lists, creates, updates/deletes where applicable, unauthorized role actions, missing identity/membership, and policy mutation/omission.
- Verify the generated test suite runs and record its actual result, including build/runtime provenance.
- Update `SEMANTIC_CONSUMER_TRACE.v1.json` only when each required consumer and acceptance evidence is present.

## Evidence limitations

This is a source audit, not a runtime test. No generated TaskFlow application was built or exercised as part of this audit. CI/test status must be checked separately; absent status data is not a pass.
