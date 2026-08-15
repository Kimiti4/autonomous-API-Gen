# ADR: Cap-C Stage 1 — FastAPI Hexagonal Compiler Backend

Status: Accepted (Cap-C, stage 1)

## Context

Cap-D delivered the Intelligence Foundation (D1–D5): a keyless, audited,
capability-matched intelligence runtime. The Software Factory (Phases 16–20)
requires the missing back half of "Intent → complete repository": a real
compiler backend that turns a typed ISR (`SystemModel`) into a deployable
production system. Only a reference `minimal-container` backend existed.

## Problem

Deliver the first real compiler backend without resorting to shallow
placeholders, and prove it produces software that actually builds and runs.

## Decision

1. **Consume the typed ISR.** `FastAPIHexagonalBackend` reads
   `IntermediateSoftwareRepresentation.system_model()` (Capability A's typed
   payload). For legacy envelopes it synthesizes a `SystemModel` from the legacy
   fields, so it works with the existing `StructuredIntentCompiler` pipeline too.
2. **Implement the existing `CompilerBackend` port**
   (`tiannara.domain.ports`) — `name` + `compile(isr, genome, output_dir) ->
   SystemDeploymentBundle` — rather than introducing a second, conflicting
   protocol. The backend id `fastapi_hexagonal` is already declared in
   `KNOWN_BACKEND_IDS` (`backend_coupling_registry.py`), so this is the
   canonical backend, not a parallel one.
3. **Emit a real, layered FastAPI service**: domain / application /
   infrastructure / API, API-key auth, structured JSON logging, settings,
   `health`/`readiness`, pytest suite, Dockerfile, compose, CI, and a README.
   It is hexagonal so persistence/security/K8s backends can swap adapters behind
   the existing domain ports later.
4. **Honest CapabilityManifest**: stage 1 declares build/lint/static-analysis/
   test/security-scan/containerize/deploy/health/observability/documentation/
   release — and deliberately does **not** declare `infrastructure_provision`
   or `database_migration`. Those are separate backends (Constitutional
   Principle: one concern per backend), not placeholders.
5. **Independent verification.** `BundleVerifier` checks structure, Python
   syntax, and inward dependency direction (domain must not import
   api/application/infrastructure). Behavioral proof (load the app, exercise
   health + auth + CRUD) lives in the test suite and is gated on `fastapi`/`httpx`
   via `importorskip`, so it degrades gracefully in stripped environments.

## Constitutional alignment

- The ISR boundary holds: `from_system_model` rejects any `SystemModel`
  containing technology tokens (`scan_for_technology_coupling`); backends
  therefore never see tech-coupled architecture. The generated *output* may
  contain `fastapi`/`docker` — that is the backend mapping an abstract posture
  to a concrete choice, which is its job.
- Backend id appears only in manifest provenance; `plan_stages`
  (`tiannara.application.cicd.capability_stages`) matches capabilities, never
  ids.

## Alternatives considered

- Emitting K8s + Terraform + Kafka + CQRS in one pass: rejected — would be a
  pile of placeholders, the exact anti-pattern the Constitution forbids.
  Those are separate compiler backends.
- A SQL persistence layer now: rejected — in-memory repositories behind domain
  ports are real and swappable; SQL arrives as a persistence backend.
- Full OAuth2/JWT now: rejected — API-key gating is real and testable; richer
  auth arrives as security backends.

## Trade-offs

- In-memory persistence limits production use until a persistence backend lands;
  accepted — ports already isolate it.
- Generation is string-templated; AST-level codegen is future hardening if
  template maintenance becomes error-prone.

## Risks

- Generated-code drift if templates grow; mitigated by syntax + behavioral tests
  on every compile.

## Future evolution

- Persistence / messaging / K8s / Terraform backends behind the same port.
- A backend registry with capability-driven selection (Cap-C Stage 2 — the gate
  Phase 16 needs to route an ISR to the right compiler(s)).
- AST-level codegen and richer fitness scoring of generated systems.

## Sources

- `folder/16.md` (Phase 16 objective: Intent → complete repository).
- `tiannara/domain/models/system_model.py` (typed ISR; technology-token denylist).
- `tiannara/domain/ports/__init__.py` (`CompilerBackend` port).
- `tiannara/application/cicd/capability_stages.py` (`plan_stages`: capability-driven).
- `tiannara/domain/governance/backend_coupling_registry.py` (`fastapi_hexagonal` declared).
