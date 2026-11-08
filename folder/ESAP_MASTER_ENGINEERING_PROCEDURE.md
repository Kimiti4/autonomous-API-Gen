# ESAP — Master Autonomous Engineering Procedure

**Status:** Governing operating specification (normative intent)  
**Scope:** Tiannara / ESAP cognitive architecture workspace  
**Evidence posture:** Capability claims below are mapped to code and FS-00 checkpoints; default honest verdict is **`PARTIAL_EVIDENCE`** until independently verified.

## Governing principle

> ESAP is not finished when it generates code. ESAP is finished when it has produced a usable result whose requirements, architecture, implementation, security, and operational behaviour have been sufficiently verified by trustworthy evidence.

**Governing equation:**

`Intent → ISR → Architecture → Software → Evidence → Verified Outcome`

Governance, provenance, security and authorization apply at every transition — not only at delivery.

## Twelve-stage lifecycle (one workflow, multiple profiles)

The fourteen logical stages in the full procedure collapse to **twelve orchestrated stages** for implementation planning. A **workflow classifier** selects which stages are mandatory for a given `RequestKind` (new application, feature, bug fix, migration, incident, …).

| Stage | Name | Primary artifact(s) |
| --- | --- | --- |
| 01 | Understand | `EngineeringRequest` (normalized request, assumptions, open questions) |
| 02 | Specify (requirements) | Versioned **Requirement Graph** with measurable oracles |
| 03 | Investigate (discovery) | `SystemSnapshot`, dependency / execution-surface maps |
| 04 | Specify (ISR) | Canonical **ISR** + obligation traceability; current vs target views |
| 05 | Analyse | `EngineeringPlan`, impact analysis, work packages, risk register |
| 06 | Design | `ArchitectureSpecification`, interface contracts, ISR mappings |
| 07 | Plan (compile) | `CompilationPlan`, backend capability manifest, obligations |
| 08 | Implement | Versioned executable artifacts + lineage |
| 09 | Build & integrate | Build artifacts, integration evidence, provenance |
| 10 | Verify | Independent verification report, residual risk |
| 11 | Repair | Defect lineage, classified root cause, reverification |
| 12 | Execute · Deliver · Evolve | Runtime / UX evidence, delivery package, evolution loop |

**Rule:** Stages share one **governed workflow coordinator**; they are not independent authorities that may reinterpret upstream contracts.

## Six architectural layers

| Layer | Responsibility | Must not |
| --- | --- | --- |
| L1 — Experience & intake | Clarification, progress, delivery UX | Become implementation authority |
| L2 — Engineering intelligence | Requirements, discovery, planning, architecture decisions | Silently rewrite ISR |
| L3 — Constitutional representation | ISR, requirement graph, contracts, traceability | Admit technology into ISR |
| L4 — Compiler & implementation | Domain compilers and registered backends | Certify unsupported semantics |
| L5 — Verification, repair, certification | Independent oracles, evidence, defect repair | Self-certify generator output |
| L6 — Execution, deployment, evolution | Sandboxed run, release, observation, improvement | Conflate build with runtime |

**Cross-cutting:** authorization, audit, artifact integrity, human gates where required (CP052, promotion lifecycle).

## Non-negotiable invariants (executable, not documentary)

1. No prompt-to-code shortcut without requirements + ISR.  
2. Registered ≠ supported ≠ certified.  
3. No silent obligation drop — defer, block, or implement explicitly.  
4. No architecture drift without authorized change.  
5. Fail closed on auth, validation, uncertainty.  
6. No self-certification.  
7. No test-count certification — trace requirement → oracle → evidence.  
8. No false runtime claims (build ≠ working application).  
9. Controlled repair with lineage and targeted regression.  
10. Unapproved production changes blocked.  
11. Bounded autonomy (limits, cancel, audit).  
12. Disclosed limitations and residual risk.

## Engineering completion contract (profiles)

Overall **ACCEPTED** only when the **declared completion profile** is satisfied — e.g. debug fix may omit production deploy; production deploy requires staging/production evidence.

Minimum gates for **product-grade** completion:

- Normalized request and requirements with acceptance oracles where applicable.  
- Validated canonical ISR (human and/or governed synthesis path).  
- Authorized architecture / compilation plan with **honest** backend capability match.  
- Build + integration evidence.  
- Independent verification (not generator-asserted).  
- Critical security and data-integrity obligations **PASS** or **BLOCKED** — never **UNKNOWN → PASS**.  
- Runtime journeys at declared environment depth.  
- Complete evidence manifest and lineage.

Delivery statuses are **not interchangeable** (`IMPLEMENTED` … `ACCEPTED`).

## Engineering evidence graph (target)

Bidirectional links: `REQ → ISR → ARCH → CMP → IMPL → TEST → EV`.

**Workspace today:** partial bindings via TOR/requirement digests, ISR content hashes, canonical API contract digests, trusted evidence registry, orchestration run store, conformance parity cells — **not** a unified queryable graph across all domains.

---

# Capability map — procedure vs repository (2026-11-07)

Legend: **I** implemented with tests or checkpoints · **P** partial / fixture-scoped · **M** missing or design-only · **N** not in scope yet

### Stage map

| Stage | Maturity | Primary implementation | FS-00 / test evidence |
| --- | --- | --- | --- |
| 01 Intake | **P** | `FullStackOrchestrationRequest`, workload registry, CP056/057 HTTP ingress guards | CP055–057; no general `EngineeringRequest` interview loop |
| 02 Requirements | **P** | `reqgraph.core.graph.RequirementGraph`, TOR registry, synthesis validators | CP054–059; vague-req rejection partial (validator heuristics) |
| 03 Discovery | **M** | Ad hoc repo tests, vertical_slice scaffolding | No `SystemSnapshot` / execution-surface product |
| 04 ISR authority | **P** | `constitutional_architecture.isr`, `isr_to_plan`, synthesis + provenance CP058–060 | CP058–060 `PARTIAL_EVIDENCE`; multi-surface reconciliation ongoing |
| 05 Analyse / plan | **P** | Senior gate, product acceptance blockers, synthesis impact in validators | CP044+, senior engineering gate tests |
| 06 Architecture | **P** | ISR architecture nodes, full-stack synthesis (routes, services, persistence) | CP060; not full alternative architecture comparison |
| 07 Compile plan | **P** | `CompilationPlan`, `BackendCapabilities`, `capability_declaration.py` | CP053, CP061 |
| 08 Implement | **P** | `compiler.backends.*`, ordinary workload path | Five proving workloads; synthesized payroll HTTP defect (CP062) |
| 09 Build / integrate | **P** | Full-stack verify, compile matrix, frontend+backend bundles | CP054, CP060 |
| 10 Verify | **P** | Independent validators, conformance semantic suite, trusted evidence CP052 | CP050–053, CP061; req→oracle trace **incomplete** globally |
| 11 Repair | **P** | CBC1 self-repair suite, synthesis remediation loops | Not unified defect taxonomy across ESAP |
| 12 Runtime / deliver / evolve | **P** | HTTP differential oracle CP062, durable execution CP051 (Python), evolution ingress guarded | Rust runtime **ENVIRONMENT_UNAVAILABLE**; E2E Playwright opt-in |

### Layer map

| Layer | Maturity | Anchors |
| --- | --- | --- |
| L1 | **P** | `autonomous-api` orchestration routes, dashboard ingress (CP056–057) |
| L2 | **P** | `reqgraph/synthesis/*`, senior engineering evaluator |
| L3 | **P** | ISR model, requirement merge, governance gate, CP052 registry |
| L4 | **P** | Python/Rust/React/Elixir backends; `support_ladder.py`, `backend_inventory.py` |
| L5 | **P** | `certification/conformance/*`, product acceptance, authorization campaign |
| L6 | **M** | Production deploy proof partial; monitoring → evolution wiring partial |

### Orchestrator (§4.1)

| Capability | Maturity | Location |
| --- | --- | --- |
| Single canonical full-stack authority | **I** | `FullStackOrchestrationAuthority` (CP055) |
| Entry-point inventory & bypass detection | **I** | `certification/orchestration/inventory.py` |
| Workflow profiles by request kind | **P** | `RequestKind`, governed vs ordinary paths; no full 12-stage classifier |
| Repair / resume / cancel | **P** | Run store, CBC1 resume patterns; not ESAP-wide |

### Compiler registry (§4.4)

| Concern | Maturity | Evidence |
| --- | --- | --- |
| Capability declarations | **I** | `compiler.core.capabilities`, `capability_declaration.py` |
| Cross-backend compile parity (5 workloads) | **P** | CP061 |
| Cross-backend **runtime** parity | **P** | CP062 — Python HTTP oracle; Rust blocked on host |
| Durable execution (CP051) | **P** | Python verified; Rust **UNSUPPORTED_FAIL_CLOSED** |
| JWT / fine auth on Rust | **P** | CP053 explicit fail-closed |

### Verification engine (§4.5)

| Concern | Maturity | Evidence |
| --- | --- | --- |
| Generator vs reviewer vs verifier separation | **P** | Synthesis reviewer JSONL CP059; trusted evidence roles CP052 |
| Contract-derived HTTP oracle | **P** | `http_contract_vectors.py` (independent of Python output) |
| Change-impact reverification | **M** | Conceptual in docs; not automated evidence invalidation graph |
| Certification harness (Phase 31) | **I** | `certification/` + `tests/cbc1/` (tiered pytest) |

### §8 audit concerns — current disposition

| Concern | Disposition | Next programme item |
| --- | --- | --- |
| Single ISR authority | **P** — Model C trusted ingress; F-01 slice IV | CP068 / universal surfaces |
| ISR hash / canonicality | **P** — five §N P0 **`CLOSED_SCOPED`** (governed ratification 2026-11-08) | F-03 / F-07…F-17 contracts |
| Semantic preservation across bridges | **P** — B-04 obligation verifier + CP061 compile parity | Inverse plan→ISR; runtime gaps |
| Backend parity | **P** — CP061–062 | **P1** reproducible Rust lane + differential |
| Execution contract unity | **P** — CP051 Python; Rust partial | **P0** compiler authority |
| Req → oracle traceability | **P** — payroll/orders fixtures; not universal | **P0** + **P1** |
| Production ingress enforcement | **P** — CP067-R8 HTTP + ingress matrix slice | Full CP056–057 matrix |
| E2E deploy guarantees | **M** | **P2** |

### Recommended build order (affirmed)

Do **not** add a second top-level orchestration abstraction before **universal** P0 claims are evidenced:

1. **P0 (scoped)** — §N findings **`CLOSED_SCOPED`** with IV + human ratification (2026-11-08); not universal ISR.  
2. **P1** — Discovery, planner, expert FE/BE/data, independent verification, repair engine.  
3. **P2** — Full-stack runtime validation, delivery/release, production feedback.  
4. **P3** — Evidence-driven evolution.

FS-00 checkpoints **051–062** are the **evidence ledger** for compiler/verification P0–P1 slices — not a substitute for the full twelve-stage product.

---

## FS-00 programme index (engineering evidence)

| CP | Engineering procedure focus |
| --- | --- |
| 050 | Contract / auth coherence |
| 051 | Durable execution |
| 052 | Trusted evidence & certification gates |
| 053 | Backend semantic parity declarations |
| 054–055 | Ordinary workloads & unified orchestration |
| 056–057 | Production ingress & requirements→ISR |
| 058–060 | Synthesized ISR integration & full-stack synthesis |
| 061 | Cross-backend semantic + compile parity |
| 062 | Rust runtime lane + HTTP differential (Python reference) |
| 063 | Engineering Evidence Graph v0 |
| 064 | Graph-bound synthesized Payroll codegen repair |
| 065 | Synthesized obligation, security and validation |
| 066 | Rust runtime lane + Python–Rust HTTP differential (seven-vector slice verified on WSL; see `release/evidence/cp066_synth_payroll_rust_http_observations.json`) |
| 067 | Universal ISR-family canonicality audit — `folder/fs00_checkpoint_067_isr_family_canonicality_and_semantic_preservation_audit.md` (`PARTIAL_EVIDENCE`: 17 families; **§N registers 5 P0 IDs**; §A executive rollup 8 P0-class themes) |
| 067-R1 | P0 remediation ownership & dependency plan — `folder/fs00_checkpoint_067_r1_p0_remediation_ownership_and_dependency_plan.md` (register **v1.3.0**: all **5** §N findings **`CLOSED_SCOPED`**; **10** work packages `R1-W01`…`W10`; CP068 **`CONDITIONAL_ISOLATED_TESTING_ONLY`**; ADRs ratified under **067-R2**) |
| 067-R2 | ADR ratification & Wave 0 authorization — `folder/fs00_checkpoint_067_r2_architecture_decision_ratification_and_wave0_authorization.md` (**6/6** ADRs **APPROVED** — `release/evidence/cp067_r2_human_adr_ratification_2026-11-08.json`; W01–W02 **IV** under R3; W03–W10 **AUTHORIZED_TO_START** via `cp067_r3_expanded_remediation_authorization_2026-11-08.json`; wave ledger `certification/atlas/esap/cp067_r2_wave0_authorization.json`) |
| 067-R3 | Wave 1 implementation + IV — `folder/fs00_checkpoint_067_r3_remediation_wave1_isr_identity_and_canonicalization.md`, `folder/fs00_checkpoint_067_r3_independent_verification.md` (W01/W02 **IV**; evidence `cp067_r3_independent_verification_report.json`) |
| 067-R4 | Wave 2 + IV — `folder/fs00_checkpoint_067_r4_remediation_wave2_plan_binding_and_implir_ingress.md`, `folder/fs00_checkpoint_067_r4_independent_verification.md` (W04/W05 **IV**; evidence `cp067_r4_independent_verification_report.json`) |
| 067-R5 | Expanded IV — `folder/fs00_checkpoint_067_r5_expanded_verification.md` (payroll/orders/appointments; W08 matrix slice) |
| 067-R5b | W03 closure assessment & W10 verification — `folder/fs00_checkpoint_067_r5_w03_closure_w10_verification.md`; evidence `cp067_r5_w03_closure_w10_assessment_report.json` (**does not** close W03/W08) |
| 067-P0-IV | P0 closure independent proof — `folder/fs00_checkpoint_067_p0_closure_independent_proof.md`; evidence `cp067_p0_closure_independent_proof_report.json` + `cp067_p0_closure_human_ratification_2026-11-08.json` |
| 067-R6 | B-04 obligation verifier + ISR-002 supplement — `folder/fs00_checkpoint_067_r6_w06_b04_obligation_verifier.md`; evidence `cp067_isr002_supplement_ratification_2026-11-08.json` |
| 067-R6-W07-PLAN | W07 semantic-preservation remediation **plan only** — `folder/fs00_checkpoint_067_r6_w07_semantic_preservation_remediation_plan.md`; register `cp067_r6_w07_semantic_preservation_plan.json` (**no implementation** until ratified) |
| 067-R7 | F-06 + F-01..F-17 inventory — `folder/fs00_checkpoint_067_r7_w02_canonicalization_expansion.md`; evidence `cp067_isr004_supplement_ratification_2026-11-08.json` |
| 067-R8 | HTTP ingress wiring — `folder/fs00_checkpoint_067_r8_w08_http_ingress_wiring.md` |
| 067-R10 | W10 integration gate — `folder/fs00_checkpoint_067_r10_w10_integration_gate.md`; evidence `release/evidence/cp067_r10_w10_integration_gate_report.json` |
| 067-W07 | ADR-R1-03 bridge semantic evidence — `folder/fs00_checkpoint_067_w07_adr_r1_03_bridge_evidence.md`; evidence `release/evidence/cp067_w07_bridge_semantic_evidence_report.json` |
| 067-W09 | ImplIR enforcement expansion — `folder/fs00_checkpoint_067_w09_implir_enforcement_expansion.md`; evidence `release/evidence/cp067_w09_implir_enforcement_expansion_report.json` |
| 067-W03 | Revision integrity at W08 ingress — `folder/fs00_checkpoint_067_w03_revision_integrity_w08.md`; evidence `release/evidence/cp067_w03_revision_integrity_report.json` |
| 068 | *(planned)* Expanded runtime conformance corpus — **`CONDITIONAL_ISOLATED_TESTING_ONLY`**; CP068 promotion **not** authorized (scoped P0 closure ≠ governed runtime conformance) |

**CP067 §N P0 register (v1.3.0):** all five findings **`CLOSED_SCOPED`** — `certification/atlas/esap/cp067_r1_p0_remediation_register.json`.

Detailed closure records: `folder/fs00_checkpoint_*.md`.

## Workflow classifier (target behaviour)

| Request profile | Mandatory stage subset (minimum) |
| --- | --- |
| New application | 01–12 full, strongest completion profile |
| New feature | 03–04 reconcile, 05–11, runtime slice of 12 |
| Small bug fix | 03, 11, 10 regression, narrow 12 |
| Security | 03, 10 security dimension, 11, 12 containment evidence |
| Dependency upgrade | 03, 09–10, 12 smoke |
| Refactor | 03 behavioural baseline, 10 equivalence, 11 |
| Architecture modernization | 03–06 full, 07–12 |

**Implementation note:** encode profiles as `RequestKind` → `StageObligationSet` on `FullStackOrchestrationAuthority` extensions — not parallel orchestrators.

---

*This document is the master operating specification for ESAP engineering procedure. Normative stage prose (interview patterns, verification dimensions, payroll acceptance journey, quality vector) lives in the programme directive that established this file; the capability map above is maintained against the repository and FS-00 checkpoints.*
