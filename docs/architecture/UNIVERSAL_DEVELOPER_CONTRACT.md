# Universal Developer Contract

**Status:** implementation contract under construction. This document is not a certification claim.

## Objective

Tiannara ESAP is to become a universal software developer, not a TaskFlow-specific generator. It must translate a source specification into production-quality software through different languages, compilers, runtimes, frameworks, and deployment targets without redesigning the core each time a new application is attempted.

TaskFlow is the first demanding end-to-end proving project, not the architecture's special case. Ledger, capstone, and later applications must reuse the same core contracts and quality gates. New projects may require domain-specific requirements and adapters, but must not require another foundational rewrite of parsing, semantic preservation, obligation tracking, compiler selection, testing, or certification.

## Shared pipeline

1. **Source intake and provenance** — identify the immutable source snapshot; retain exact bytes, origin, version, and content hash. Parsing must produce a source map and report unsupported or ambiguous syntax rather than silently dropping it.
2. **Technology-neutral requirement graph** — normalize goals, constraints, data, workflows, permissions, non-functional requirements, acceptance criteria, assumptions, and dependencies. Every node traces back to source spans or explicit decisions.
3. **Semantic resolution ledger** — identify missing decisions; distinguish explicit user intent, reviewed decisions, inferred proposals, and unresolved unknowns. A schema default is never treated as user intent. High-impact ambiguity blocks generation until resolved.
4. **Authoritative obligation projection** — derive stable obligation IDs and acceptance conditions from the validated source/graph/semantic context. Consumers cannot supply a reduced obligation list to bypass required work.
5. **Technology-neutral system model / ISR** — preserve the full contract independently of implementation language, framework, database, or cloud. No backend may mutate the source semantics.
6. **Realization planner and backend adapters** — select language, compiler, runtime, framework, libraries, and deployment only as realization decisions. Each adapter declares supported, partial, or unsupported semantics; unsupported MUST requirements block or require an explicit approved alternative.
7. **Artifact construction** — generate coherent backend, frontend, persistence, migrations, API schemas, infrastructure, deployment, documentation, tests, and operational instrumentation as required by the specification. Generated pieces must integrate into one buildable product.
8. **Independent verification** — run formatter/linter/type checks, unit/integration/contract/E2E/security/accessibility/performance checks where applicable, dependency and secret scans, build/reproducibility checks, and negative-case tests. Test execution and evidence must be bound to the exact source, obligations, consumer, build, and environment.
9. **Runtime acceptance** — start the actual candidate, exercise its API and UI, verify persistence and restart/recovery behavior, permissions and isolation, and collect traceable evidence. Static declarations or simulated runners are not runtime proof.
10. **Promotion and release** — require complete authoritative obligations, successful applicable gates, auditable evidence, rollback/recovery readiness, and human authorization where policy requires it. UNKNOWN is not PASS.

## Language/compiler portability contract

The semantic core must not be coupled to one language or compiler. A language/backend adapter must implement a common contract for:
- capability discovery and versioned toolchain identity;
- mapping from technology-neutral types, constraints, transactions, authorization, errors, and lifecycle semantics;
- deterministic generation and provenance;
- explicit support/degradation reporting for every required semantic;
- build, test, run, inspect, and package operations in a bounded environment;
- artifact and runtime evidence linked to obligation IDs;
- parity tests proving that the same source semantics survive across supported backends.

A new language should require a backend adapter and conformance campaign, not a rewrite of source understanding, semantic resolution, obligation projection, governance, or evidence certification. “Any language/compiler” is a goal of an extensible adapter architecture, not a claim that every toolchain is already implemented or supported.

The shared domain now defines `ToolchainCapabilityManifest` in `tiannara/domain/models/capability_manifest.py`. It records adapter identity, language, compiler/version constraint, optional runtime/version constraint, target platforms, bounded operations, per-semantic support levels, and required toolchain digests. Missing semantic entries resolve to `UNKNOWN`, not `SUPPORTED`. The manifest can be attached to a `BackendCapabilityDeclaration`; legacy declarations remain loadable during migration, but absence of a manifest is not evidence of portability. Manifest claims must still be checked against resolved toolchain identity and independent conformance evidence before they can satisfy a certification gate.

## Project reuse rule

Before TaskFlow is declared ready, the shared pipeline and gates must be exercised against at least:
- TaskFlow: multi-user application with workspace isolation, roles, relational integrity, workflows, UI/API parity, auditability, and operational recovery;
- Ledger: a distinct domain model and invariants that test whether obligation derivation is genuinely generic rather than hard-coded to TaskFlow;
- Capstone: a third specification shape that challenges assumptions in intake, planning, artifact selection, and verification.

These are portability and generalization checks. They do not require fully generating all three products before TaskFlow; they require the core contracts and test fixtures to demonstrate that later projects can enter the same pipeline without a foundational redesign.

## Non-negotiable quality rules

- No hidden defaults for consequential product, security, privacy, consistency, retention, or deployment decisions.
- No fabricated files, APIs, tests, evidence, or claims of execution.
- No promotion based solely on a successful compiler exit or generated test source.
- No simulated evidence accepted as real build/runtime evidence.
- No caller-supplied boolean, status, or hash alone treated as authority.
- Preserve all failed attempts, gaps, and UNKNOWN outcomes in the evidence trail.
- Human authority remains explicit for policy decisions and releases that require approval.

## Current implementation boundary

The shared source projection in `tiannara/application/compiler/source_projection.py` is an initial reusable primitive. It freezes source/graph identity, projects generic graph nodes into UNKNOWN obligation records, and detects omission or semantic weakening. It does not yet attest that the graph was faithfully derived from the source, bind that context to the live ISR/compiler path, prove runtime enforcement, or certify multi-language parity. These are active blockers, not completed features.

**TaskFlow generation stays blocked** until the trusted source-to-graph projection, source-to-ISR binding, authoritative obligation enforcement, and evidence-backed consumer/runtime gates are integrated and adversarially tested.
