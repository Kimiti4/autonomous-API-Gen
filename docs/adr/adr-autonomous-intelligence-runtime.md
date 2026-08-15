# ADR: Autonomous Intelligence Runtime

Status: Accepted (Cap-D, stage D1)

## Context

Tiannara's intelligent behaviour currently routes through language-model
providers (Cap-B). The platform's constitutional purpose is to operate as an
autonomous software-engineering organisation; architectural dependence on any
single external model API contradicts the Constitutional Principle
(*languages, frameworks, databases, clouds… are backends, not foundations*).
"Intelligence" must become a backend class, not a foundation.

## Problem

How to integrate reasoning backends — deterministic compilers, algorithmic
solvers, local models, and remote/ frontier models — behind a single
technology-agnostic boundary, such that:

1. No external model is ever architecturally required;
2. Intelligence outputs are candidates, never artifacts (they pass validation
   before reaching the ISR);
3. Provider identity is provenance, never part of the core reasoning model;
4. The platform remains bootable, compilable, testable, and certifiable with
   zero external API keys.

## Decision

1. **Intelligence as a backend class.** Introduce
   `IntelligenceProvider` (port) + `CapabilityDeclaration`.
   `LocalityLevel` orders backends on a deterministic-first cascade:
   `L0 deterministic → L1 algorithmic → L2 local model → L3 remote model`.
2. **Policy-as-data routing.** `RoutingPolicy.max_locality` is the only knob.
   `KEYLESS_POLICY` caps locality at L2 — with it, L3 candidates never enter
   the candidate set, making "no external key required" a *structural*
   property, not a documented aspiration.
3. **Deterministic-first cascade.** `CascadeExecutor` tries capability-matched
   providers in `(locality, provider_id)` order; the first success deflects
   all remaining candidates, and every deflection is recorded for audit.
4. **Outputs are candidates, never artifacts.** The port produces
   `IntelligenceResult`; no ISR mutation or generated code consumes a model
   output before it passes the existing B2/B3 validation, repair, and
   authoritative-analysis machinery.
5. **Provider identity is provenance.** `provider_id`/`provider_class` ride in
   `IntelligenceResult` for evidence only; the ISR, Evolution Engine,
   compilers, and verification never branch on backend identity.
6. **Local inference is deployment topology.** Ollama/llama.cpp/vLLM/
   CUDA/Metal/vendor names exist only inside `CapabilityDeclaration.metadata`
   as opaque provenance. The AIR core names no runtime, accelerator, or
   vendor.
7. **Cap-B backward compatibility.** `LanguageModelBridge` satisfies the
   existing `LanguageModelProvider` port over the AIR cascade. Recorded replay
   and B6's live adapter are wrapped as model-class `IntelligenceProvider`s;
   Cap-B consumers receive the identical `ModelCallRecord`, so B2/B5
   provenance is byte-identical. No Cap-B code changes.

## Alternatives considered

- **Vendor-neutral single SDK layer:** rejected — still a dependency class,
  no deflection economics, no local-first guarantee, and it papers over the
  "intelligence as backend" framing with "LLM topology".
- **Hardcoding a live provider as required:** rejected — violated the
  Constitutional Principle and made the platform non-bootable without keys.
- **Learned routing from the start:** rejected — opaque and unauditable; it
  would recreate the dependency disease in a new form. A learned router is a
  future audited evolution stage, not the starting point.
- **Auto-confirming autonomy from observations:** rejected — observation
  informs; certification status is ratified, never auto-promoted.

## Trade-offs

- **Capability ceiling is real.** Without frontier models, genuinely ambiguous
  synthesis degrades. This is accepted and made *measurable* via the Autonomy
  Certification (`AutonomyAccountant`), so progress is visible per task class.
- **Deterministic-first may under-serve ambiguous tasks at L0/L1.** Mitigated
  by the cascade falling through to L3 under the default policy; keyless runs
  accept lower coverage in exchange for the structural guarantee.
- **Routing is simple, not clever.** Routing quality is observable and evolvable
  rather than hidden behind learned behaviour.

## Risks

- **Overstating local-model quality.** Mitigated by requiring the first
  Autonomy Audit before any task class is declared keyless-capable at L2.
- **Provider drift in recorded fixtures.** Existing `ModelCallTranscript`
  chain verification detects tampering; schema drift fails fast via pydantic.
- **Router opacity** — the policy is data, every routing decision is logged
  via `CascadeStep`, and the keyless structural guarantee is unit-tested
  (`cascade_path == []` for L3 under `KEYLESS_POLICY`).

## Consequences

- The platform can boot, elicit, extract, synthesize, compile, test, audit,
  version, and deploy with no external model configured (deterministic and
  algorithmic backends at L0/L1).
- External models become optional accelerators, gated by `RoutingPolicy` and
  `BudgetGovernor` (added in a later D-stage), never requirements.
- Cap-C compiler backends land as `DETERMINISTIC_COMPILER` providers — expanding
  the L0 surface and *reducing* intelligence dependence over time, which the
  autonomy metrics will register as progress.
- The autonomy certification becomes a standing, measured property rather than
  an aspiration.

## Future evolution

- A learned/optimised router as an audited evolution stage in Phase 38.
- Model genomes: models selected and retired by evolutionary fitness (Cap-D D5).
- Per-task-class autonomy targets as standing certification gates, with
  provisional→confirmed transitions governed by measured audits.
