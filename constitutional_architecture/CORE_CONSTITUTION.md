# Core Constitution of the Evolutionary Software Architecture Platform

## Preamble

The Evolutionary Software Architecture Platform is a **language-agnostic, multi-pass software compiler** that autonomously designs, evolves, verifies, generates, deploys, and improves complete production systems. This document establishes the immutable axioms that govern all platform behaviour. No compiler backend, evolution operator, or fitness evaluator may violate these axioms.

---

## Axiom I: The ISR Supremacy

> **The Universal Intermediate Software Representation (ISR) is the single, technology-agnostic source of truth for all architectural structure.**

- The ISR encodes *what* the system does, never *how* it is implemented.
- No compiler backend, evolution operator, or evaluator may alter the ISR in-place. All ISR modifications produce a new immutable version.
- The ISR must never contain framework-specific types, provider names, or infrastructure identifiers. Protocol abstractions (REST, HTTP verbs, event patterns) are permitted; concrete implementations (FastAPI, Express, AWS SQS) are forbidden.
- A violation of ISR purity is a **constitutional violation**. The offending commit or pull request must be rejected.

### Enforcement

The `ConstitutionValidator` scans all ISR instances and rejects any that contain:
- Strings matching the **Forbidden Lexicon** (see Appendix A)
- Technology-specific field values in abstract entity types
- Direct references to cloud providers, database engines, or UI frameworks

---

## Axiom II: The Genome Isolation

> **The Evolution Engine operates exclusively on the Architecture Genome. It never mutates the ISR directly.**

- The Genome encodes abstract architectural decisions as parameterized, bounded genes.
- The Transcriber is the sole bridge between Genome and ISR: `Transcriber(Genome) → ISR`.
- No genetic operator (mutation, crossover, heuristic injection) may bypass the Transcriber to write ISR nodes.
- The Genome and the ISR are distinct representations. The Evolution Engine evolves the Genome; the Transcriber expresses the phenotype.

### Enforcement

The `ConstitutionValidator` verifies that all evolution paths flow: `Mutation → Genome → Transcriber → ISR`. Any code path that writes ISR entities outside the Transcriber is a violation.

---

## Axiom III: The Compiler Purity

> **All Compiler Backends are pure, stateless functions: `f(ISR, Target, Constraints) → CompiledArtifacts`.**

- A Compiler Backend consumes the ISR and produces artifacts. It never modifies the ISR.
- Compiler Backends are the **only** location where framework-specific syntax exists. All generated code (Tailwind, FastAPI, Terraform, etc.) is produced here.
- The Compiler Framework is an abstract interface. Backends are pluggable and replaceable.
- No business logic or architectural decision may be embedded in a compiler backend. They contain only *assembly logic*.

### Enforcement

The `ConstitutionValidator` checks that compiler modules do not import or modify ISR model types (with the exception of reading ISR profiles for code generation). Any compiler that writes to the ISR is in violation.

---

## Axiom IV: The Knowledge Externality

> **Architectural patterns, anti-patterns, heuristics, and empirical data reside in the Constitutional Knowledge Base (CKB), never hardcoded in the Evolution Engine or Compiler Backends.**

- The CKB is a versioned, queryable repository of architectural expertise.
- The Evolution Engine queries the CKB for valid gene alleles, fitness heuristics, and transformation rules.
- Heuristic mutations and seed populations are derived from CKB queries, not from hardcoded constants.
- The CKB evolves through a closed feedback loop: production telemetry → learning engine → CKB update.
- Hardcoding an architectural heuristic in the Evolution Engine or any compiler is a constitutional violation.

### Enforcement

The `ConstitutionValidator` audits evolution operators and seed factories for hardcoded domain-specific values. Architectural constants (bounds, defaults) are permitted in the Genome definition; application-specific heuristics must reside in the CKB.

---

## Axiom V: The Dual-Track Evolution

> **Functional and Non-Functional requirements are evolved in parallel, never sequentially.**

- The Functional Track evolves business capabilities, API surfaces, UI flows, and domain logic.
- The Non-Functional Track evolves performance, security, resilience, cost, accessibility, and operability.
- Pareto multi-objective optimization ensures that no functional gain may compromise operational viability below constitutional thresholds.
- Fitness evaluation must include at least one non-functional dimension for every candidate.
- A candidate that passes all functional checks but fails any non-functional constitutional threshold is rejected regardless of functional correctness.

### Enforcement

The `ConstitutionValidator` checks that all evolution runs include evaluators from both tracks. The minimum evaluator set must contain at least one functional and one non-functional evaluator.

---

## Axiom VI: The Boundary Integrity

> **The 10-pass compiler pipeline is the only permitted path from raw requirements to compiled artifacts. No stage may be skipped, and no stage may perform the work of another.**

| Pass | Stage | Input | Output |
|------|-------|-------|--------|
| 1 | Requirements Validation | Raw Input | Validated Requirement Graph |
| 2 | Intent Analysis | Requirement Graph | Intent Model |
| 3 | Topology Resolution | Intent Model + CKB | Architectural Profile |
| 4 | Genome Construction | Architectural Profile | Architecture Genome |
| 5 | Dual-Track Evolution | Genome + Constitution | Optimized Genome |
| 6 | ISR Instantiation | Optimized Genome | Universal ISR |
| 7 | Verification | Universal ISR | Verification Report |
| 8 | Backend Selection | ISR + Constraints | Compiler Targets |
| 9 | Code Generation | ISR + Targets | Source Artifacts |
| 10 | Runtime Instrumentation | Generated Artifacts | Deployable System |

- Direct conversion from requirements to ISR (bypassing Genome construction and evolution) is prohibited.
- Direct conversion from Genome to code (bypassing ISR instantiation) is prohibited.
- Each pass produces a distinct, versioned artifact. Pass outputs may not be overwritten by downstream stages.

### Enforcement

The `ConstitutionValidator` traces the transformation lineage of every artifact. Any artifact whose chain of derivation skips a required pass is flagged and rejected.

---

## Axiom VII: The Auditability Principle

> **Every transformation in the platform must be recorded, versioned, and traceable to the originating pass and operator.**

- All ISR mutations produce a new version with parent hash and provenance metadata.
- All Genome mutations are recorded in the mutation history with the operator identity and allele values.
- All evolutionary snapshots are persisted in Constitutional Memory.
- The complete lineage of every compiled artifact must be reconstructible from the stored metadata.
- Untraceable modifications are constitutional violations and must be rejected.

### Enforcement

The `ConstitutionValidator` checks that every ISR instance and Genome has a valid provenance chain. Missing provenance metadata or orphaned artifacts are violations.

---

## Appendix A: The Forbidden Lexicon

The following terms must never appear in ISR entity values, field names, or schema definitions. This list is not exhaustive — any technology-specific identifier that implies a concrete implementation rather than an abstract concept is subject to rejection.

### Cloud Providers
`aws`, `azure`, `gcp`, `digitalocean`, `heroku`, `netlify`, `vercel`, `cloudflare`, `alibaba`

### Database Engines
`postgresql`, `postgres`, `mysql`, `mariadb`, `sqlite`, `mongodb`, `dynamodb`, `cassandra`, `redis`, `elasticsearch`, `cockroachdb`, `spanner`

### UI Frameworks
`react`, `vue`, `svelte`, `angular`, `ember`, `solidjs`, `qwik`, `lit`, `flutter`, `swiftui`

### API Frameworks
`fastapi`, `express`, `django`, `flask`, `spring`, `rails`, `laravel`, `aspnet`, `gin`, `echo`

### Infrastructure as Code
`terraform`, `pulumi`, `cloudformation`, `cdk`, `helm`, `kustomize`, `ansible`, `chef`, `puppet`

### CSS / Styling
`tailwind`, `bootstrap`, `material-ui`, `chakra`, `styled-components`, `sass`, `less`, `postcss`

### Orchestration & Compute
`kubernetes`, `k8s`, `docker`, `ecs`, `eks`, `gke`, `aks`, `lambda`, `functions`, `fargate`

> **Note:** These terms ARE permitted in Compiler Backend implementations and in the `target` parameter of `f(ISR, Target, Constraints)`. They are FORBIDDEN in the ISR itself, the Genome, the CKB pattern definitions, and the Fitness Evaluator interfaces.

---

## Appendix B: Baseline Audit (Phase -1)

As of the Phase -1 Baseline Audit, the following existing components have been mapped to the 10-pass pipeline:

| Existing Component | Pipeline Mapping | Status |
|-------------------|-----------------|--------|
| IRR Schema | Pass 1-2 (Requirements Validation + Intent Analysis) | Kept — refactor output to Intent Model |
| FrontendGenomeTranscriber | Pass 6 (ISR Instantiation) | Kept — deterministic Genome→ISR mapper |
| InMemoryKnowledgeGraph + graph_data.json | Pass 3 (Topology Resolver seed) | Kept — becomes seed for CKB |
| ParetoEvolutionCoordinator | Pass 5 (Dual-Track Evolution) | Kept — Pareto optimization |
| TokenConsistencyEvaluator | Pass 5 + 7 (Fitness + Verification) | Kept — split role |
| AccessibilityEvaluator | Pass 5 + 7 | Kept — split role |
| VisualIntelligenceEvaluator | Pass 5 + 7 | Kept — split role |
| InMemoryConstitutionalMemory | Pass 5 (Evolutionary Memory) + CKB seed | Kept — bifurcates |
| TailwindCompiler | Pass 9 (Code Generation) | Kept — pure compiler backend |
| FastAPIBackend | Pass 9 (Code Generation) | Kept — pure compiler backend |
| FrontendISRProfile | Pass 6 (ISR schema extension) | Kept — domain profile |
| Compiler Pipeline (pass_manager, etc.) | Pass 8-9 (Backend Selection + Code Gen) | Kept |

**No existing code is deprecated.** All existing modules map to one or more pipeline passes. The refactoring required is at the *boundary interfaces* (making Pass 1-2 output an Intent Model instead of raw IR, and formalizing the Genome→ISR→Compiler artifact chain).

---

## Appendix C: Amendment Process

1. Any proposed amendment to these axioms must be submitted as an Architectural Decision Record (ADR).
2. The amendment must demonstrate that existing axioms are insufficient to prevent a specific class of architectural drift.
3. The amendment must pass a constitutional review by at least two independent reviewers.
4. Amendments are versioned. The current constitution version is `v1.0.0`.
5. The amendment process may not alter Axioms I, II, or VII (the three foundational axioms). These are immutable. Any attempt to amend them dissolves the constitution entirely.
