# ADR: Capability Manifest and Meta-Compiler Decoupling

Status: Accepted (Cap-D, stage D2)

## Context

The Phase-15 CI/CD meta-compiler selects stages by compiler backend id
(`if "fastapi_hexagonal" in bundle.bundles`). That couples the
meta-layer to specific backends — precisely the dependency the
Constitutional Principle eliminates. Cap-D requires the same separation
for every meta-consumer of compiled artifacts: repository
materializers, deployment planners, and so on.

## Problem

Meta-compilers must adapt pipeline generation to arbitrary backends
(current and future) without modification, while migration from the
coupled implementation must be incremental and auditable. A naive
"stringly typed capabilities" field would recreate the coupling at the
data level.

## Decision

1. **Typed capability manifest.** Every compiler backend emits a
   schema-versioned `CapabilityManifest` alongside its
   `SystemDeploymentBundle`, using a canonical `BundleCapability`
   vocabulary. `backend_id` is carried as provenance only and is
   explicitly excluded from selection logic.
2. **Capability-driven planning.** Meta-compilers consume
   `capability_stages.plan_stages(manifest)` — a pure, deterministic
   function of the manifest. The canonical plan order encodes the
   build→test→deploy dependency direction; meta-compilers refine within
   stages but never reorder across it.
3. **Bidirectional coupling guard.** `backend_coupling_scanner`
   performs AST string-literal scanning of configured
   `META_COMPILER_ROOTS`; `LEGACY_BACKEND_COUPLING_REGISTRY` records
   pre-existing debt. The guard fails on unregistered coupling (debt
   cannot grow) and on stale registrations (removals are recorded). A
   missing scan root fails fast — a guard blind to its tree is a silent
   pass, and silent passes are forbidden.
4. **Additive, monotonic migration.** `capability_manifest` is optional
   on `SystemDeploymentBundle` (`None` during migration).
   Capability-driven meta-compilers call `require_capability_manifest`,
   which fails loudly on absence; legacy consumers are untouched.
5. **Distinct vocabularies.** `BundleCapability` (compiled artifact) is
   separate from AIR's `CapabilityDeclaration` (reasoning backend).
   Merging them would couple reasoning concerns to artifact concerns at
   the type level.

## Alternatives considered

- **Runtime backend-to-capability lookup table:** rejected — routes
  through backend identity at runtime and re-couples.
- **Free-form capability strings in the manifest:** rejected —
  vocabulary must be typed (enum) so plans are deterministic and testable.
- **Immediate hard requirement of manifests on all bundles:** rejected —
  breaks the existing fleet; additive migration with loud absence errors
  preserves backward compatibility.
- **Regex scanning of all source text (not AST):** rejected — false
  positives from `backend_id` field names and substrings; AST
  string-literal scanning with word boundaries is precise.

## Trade-offs

- **AST string-literal scan ignores non-literal construction** of backend
  ids (f-strings, `format`, concatenation, variable indirection).
  Accepted as documented residual: the token vocabulary and code review
  cover that, and Cap-C registration tightens it.
- **Two "capability" vocabularies** adds a name, not coupling: each has a
  single, disjoint owner (artifact vs reasoning) and never intersects.
- **Empty initial registry** means the first green run proves zero coupling
  exists today; any future coupling is a hard failure.

## Risks

- **`META_COMPILER_ROOTS` misconfiguration:** mitigated by fail-fast
  `FileNotFoundError` (`test_scanner_missing_root_fails_fast`).
- **Capability vocabulary drift:** mitigated by schema versioning and the
  add-only extension rule in `BundleCapability`.
- **Meta-compiler bypass via `bundle.backend_name`:** mitigated by the
  guard scanning for the registered token set in compiled meta-compiler
  sources; new backend ids must be registered before they can appear.

## Consequences

- Swapping FastAPI for Elixir, Rust, Go, Java, Node — or any future
  backend that emits an equivalent manifest — changes no meta-compiler
  code. The plan is derived purely from capabilities.
- Repository materializer, deployment, and CI/CD become backend-agnostic
  by construction, not by convention.
- The coupling registry is a shrink-only sunset checklist: it can only
  go empty, never grow.

## Future evolution

- Cap-C compiler backends formalize id registration;
  `KNOWN_BACKEND_IDS` derives from the live registration registry,
  removing the second source of truth.
- Capability versioning for breaking vocabulary changes.
- Repository materializer and deployment meta-compilers adopt
  `plan_stages`.
