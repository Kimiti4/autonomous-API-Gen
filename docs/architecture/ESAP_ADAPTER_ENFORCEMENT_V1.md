# ESAP Adapter Enforcement — FS-00 Remediation A4

**Document ID:** ESAP-ADR-FS00-004  
**Status:** APPROVED — IMPLEMENTATION IN PROGRESS  
**Approval record:** User approved the four FS-00 remediation steps on 2026-11-05.  
**Implementation branch:** `remediation/fs00-authority-implementation`  
**Canonical owners:** `reqgraph/core`, `isr/core`, `compiler/core/canonical_ir.py`

## 1. Purpose

A canonical model is not sufficient if adapters can silently omit source semantics or production routes can bypass the model. A4 defines a common enforcement surface for source-to-ISR and ISR-to-CompilerIR adapters, and for the transitional CompilerIR-to-backend-plan boundary.

## 2. Adapter record requirements

Every production adapter must expose or persist:

- adapter identifier and semantic version;
- input/output contract IDs and schema versions;
- immutable source and output identities;
- source-to-output node/relationship mapping;
- preserved, normalized, deferred, and rejected source identifiers;
- unresolved/ambiguous binding diagnostics;
- explicit loss classification;
- backend capability/constraint result before artifact emission.

A source hash alone is not a mapping report. A typed model alone is not proof that all source semantics survived.

## 3. Implemented CompilerIR projection report

`compiler/core/canonical_ir.py:CompilerIRProjectionReport` currently records:

- complete source node and relationship ID inventories;
- elements represented in the transitional `CompilationPlan`;
- elements preserved in CompilerIR only;
- explicit lost node and relationship ID sets.

The report enforces a complete, non-overlapping partition. CompilerIR construction rejects any lost or unclassified source element. The complete source ISR node/edge records remain available in the canonical CompilerIR regardless of whether the transitional plan has a corresponding field.

## 4. Backend compatibility gate

`assert_compiler_ir_supported(compiler_ir, capabilities)`:

1. checks any declared backend constraints against the selected backend ID;
2. checks the transitional plan's required semantic features against the backend's declared capabilities;
3. raises a fail-closed error before backend compilation when a constraint or required feature is unsupported.

Existing backend-level capability checks remain enabled as defense in depth. A backend must not be considered capable merely because it can deserialize or structurally accept the plan.

## 5. Evidence binding

The TOR SourceTraceability record is now schema `1.1` and binds both ISR graph and revision-envelope hashes. The source-bound authorization candidate manifest is schema `1.2.0`. Payroll certification candidate hashes also bind the exact ISR revision and CompilerIR identities. It binds the ISR graph content hash, ISR revision-envelope hash, CompilerIR compilation ID/content hash, and transitional plan hash. The campaign persists `compiler-ir.json`; the independent verifier reloads it, validates its identity/content hash, checks both ISR hashes and revision ID, and verifies that the persisted plan exactly matches the CompilerIR execution-plan projection. Mutation tests now require the ISR revision and CompilerIR hashes to invalidate alongside the other candidate bindings.

## 6. Current route adoption

| Route | Current implementation | Status |
|---|---|---|
| Compatibility lowering API | `isr_to_plan` delegates through `isr_revision_to_compiler_ir` and returns the transitional plan projection | IMPLEMENTED |
| Campaign A plan builder | Binds the ArchitectureCandidate hash; constructs CompilerIR before plan projection | IMPLEMENTED IN BRANCH |
| Source-bound authorization campaign | Constructs CompilerIR with explicit not-applicable ArchitectureCandidate reason; candidate schema 1.2.0 binds ISR revision and CompilerIR hashes; verifier reloads and checks both | IMPLEMENTED IN BRANCH |
| Payroll certification | Candidate hash now binds ISR revision-envelope hash and CompilerIR ID/hash; certifier validates exact source/plan projection and uses canonical backend gate | IMPLEMENTED IN BRANCH |
| TOR adapter | Emits schema-2.0 ISR revisions through the single ISR registry | IMPLEMENTED IN BRANCH |
| `compiler/kernel.py:UniversalCompiler` | Accepts `CompilationRequest.isr` dict and constructs legacy `compiler.models.CompilationPlan`; production caller reachability not yet established | LEGACY ROUTE / MIGRATION OPEN |
| `compiler/sdk/testing.py` | Constructs legacy SDK test plan from sample ISR dict | TEST HARNESS; not a production route |
| `tiannara/application/compiler/selector.py` | Selection-only; returns separate `tiannara.domain.models.backend_declaration.CompilationPlan`; no backend invocation in this module | DISTINCT SELECTION SUBSYSTEM / CALLER REACHABILITY OPEN |
| `autonomous-api/app/engine/domain_aware_compiler.py` | Builds proposal-level domain constraints plan, distinct from `compiler.core.plan.CompilationPlan` | DISTINCT SUBSYSTEM / PRODUCTION REACHABILITY OPEN |
| Other frontend/backend/mobile compiler-family routes | Not yet migrated or proven to converge | UNKNOWN / OPEN |

## 7. Blocking semantics

- Unknown schema version or node/edge kind: block.
- Missing source ISR or revision-envelope identity: block.
- Missing ArchitectureCandidate reference without an explicit not-applicable reason: block.
- Missing/ambiguous frontend interaction or route binding: block.
- CompilerIR source-to-plan report with any lost/unclassified source element: block.
- Backend constraint mismatch or unsupported required semantic feature: block before generation.
- Unsupported targets remain registered as targets; they refuse only the unsupported workload.

## 8. Acceptance work remaining

A4 is not universally complete until:

1. every production compiler entrypoint is inventoried and classified by actual reachability;
2. each production route proves it enters the canonical ISR and CompilerIR boundaries;
3. direct backend and frontend/mobile generation routes cannot bypass the common capability gate;
4. every adapter emits a durable mapping report bound to source/output hashes;
5. adversarial tests remove a source field, relationship, binding, or required capability and prove the route blocks before artifact generation;
6. route-level runtime evidence confirms the behavior, not just static imports or test doubles.

**Current assessment:** the first common report and gate exist, and three identified production/certification routes are wired through them. System-wide enforcement remains NOT ESTABLISHED pending route inventory, tests and CI evidence.
