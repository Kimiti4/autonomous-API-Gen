# ADR: Typed ISR Schema (SystemModel v1.0) and RequirementGraph

Status: Accepted (Capability A, Phase Ledger rev. 2)

## Context
The calibration harness substrate (`S1`) proved pipeline mechanics with
reference adapters, but the ISR envelope carried its architectural sections as
opaque pydantic models (`ServiceSpec`, `DataModelSpec`, ...) that already
contained technology tokens (`container_runtime = "docker"`, `port: int`,
`memory: "256m"`). All 100 calibration inputs were hand-authored. Certification
audits 31+ are blocked: evolution needs typed dimensions to grip, compiler
backends need typed sections to consume, and requirement analysis — the first
evolution stage — needs a requirement structure to analyze.

## Problem
An opaque or coupled ISR forces the Evolution Engine either to mutate
unstructured content (violating "evolve architecture, not code") or to do
nothing, and makes traceability, fitness attribution, and certification
evidence impossible to compute deterministically.

## Decision
1. Introduce `SystemModel` v1.0 as the typed, technology-agnostic ISR payload,
   covering all constitutional ISR dimensions with abstract enumerated
   vocabulary (postures, styles, criticalities, field types, observability
   requirements, etc.). A SystemModel is carried inside the existing
   `IntermediateSoftwareRepresentation` envelope via `payload_type = "system_model.v1"`
   and a serialization-excluded `content` field.
2. Introduce `RequirementGraph` (typed nodes/edges + `GraphProvenance` +
   `AnalysisFindings`) carried as the requirement structure inside the ISR,
   traceable to `SystemModel.capabilities[].traced_requirement_ids`.
3. Keep `IntermediateSoftwareRepresentation` as the chain-linked envelope.
   Add `from_system_model` / `system_model` accessors. `content_hash` is
   unchanged in value for legacy envelopes: the new `payload_type` and `content`
   fields are declared `Field(..., exclude=True)`, so `model_dump_json(
   exclude={"lineage"})` does not emit them and every existing hash is
   byte-identical. The hash function (sha256 canonical JSON, lineage excluded)
   is not altered.
4. Enforce technology-agnosticism at envelope creation via a curated
   token scan (`scan_for_technology_coupling` -> `TechnologyCouplingError`).
5. Unknown concerns go to `SystemModel.extensions` as schema-evolution flags.
6. Structural validity of `RequirementGraph` is enforced at construction
   (unique ids, no dangling/duplicate edges, no self-directed cycles); semantic
   findings (cycles, conflicts, coverage gaps) are pure analysis output
   attached to `analysis` and excluded from `content_hash`.

## Alternatives considered
- Conventional over schema for the opaque dict: rejected — unenforceable,
  unmeasurable.
- Replacing `IntermediateSoftwareRepresentation` with a new envelope: rejected
  — breaks existing hash chains and the 1060-test floor; violates incremental
  evolution.
- Free-form property graph (RDF-style) for the ISR: rejected — too weakly
  typed to compile deterministically.
- Letting backends interpret coupled tokens directly: rejected — locks the
  ISR to a single technology stack, defeating the port/adapter architecture.

## Trade-offs
- Schema rigidity vs expressiveness: mitigated by `extensions` + a
  `schema_version` field + a semver discipline on SystemModel.
- Curated token list false-positive risk: only genuinely ambiguous natural-
  language words are excluded ("go", "rust", "swift", "lambda", "spring").
  "docker" is unambiguous and is banned. Backends map abstract postures to
  concrete choices, so the denylist can be strict without blocking design.
- `payload_type`/`content` live outside the hash: two envelopes identical in
  core fields but carrying different SystemModels hash equally. Acceptable
  because (a) typed content is carried verbatim, (b) SystemModel carries its
  own canonical `content_hash`, and (c) Cap-B additionally records
  `system_model_hash` on `CalibrationEvidence` so envelope + payload identity
  are disambiguated downstream.
- `analysis` excluded from `RequirementGraph.content_hash`: derived views must
  not alter canonical identity; analysis is recomputed on demand.

## Legacy Coupling Containment (Cap-B1)
The legacy coupled specs in `isr.py` (`ServiceSpec.port`,
`DeploymentSpec.container_runtime = "docker"`) are quarantined on the legacy
envelope path and enumerated in `LEGACY_COUPLING_REGISTRY`
(`tiannara/domain/governance/coupling_registry.py`). A bidirectional guard
test (`tests/test_coupling_registry_guard.py`) makes the boundary structural:
unregistered coupling fails the build (debt cannot grow); stale registry
entries fail the build (debt removal is recorded). `scan_for_technology_coupling`
(now including "docker") governs `from_system_model`; the legacy scanner guards
the domain layer broadly.

## Legacy Coupling Sunset Gates
Legacy coupled fields are removed only when ALL of the following are measured
true:
  1. >=1 Cap-C compiler backend compiles purely from SystemModel sections;
  2. the stratified matrix runs with zero legacy envelopes;
  3. the coupling registry is empty.

No date-based removal. Gate-based only, consistent with the phase-ledger rule.

## Risks
- Downstream adapters must migrate to typed sections (Cap-B synthesizer,
  Cap-C compiler backends). The legacy coupled specs in `isr.py` are retained
  until then so no existing code breaks.
- Token scan tuning: violations are reported with `path` + `excerpt` to make
  tuning evidence-based rather than guesswork.
- Graph analysis is O(V*E) worst case for cycle detection; acceptable at
  calibration scale (hundreds of requirements).

## Future evolution
- Cap-B synthesizer writes `NodeProvenance` (taxonomy_version, stratum, seed)
  and records each model call as `"model@version:call-hash"` in
  `RequirementGraph.provenance.model_versions`.
- Evolution stage 1 composes `analyze` + `cross_reference` as authoritative
  analysis on the ISR; may mutate requirement priorities/assumptions in place
  of the ISR (never of raw code).
- Compiler backends (Cap-C) consume `SystemModel` sections; each backend maps
  abstract field types and postures to concrete technology choices.
- Phase 38 may evolve the token list and SystemModel schema from
  `unclassified` / `extensions` flags without breaking existing hashes.
