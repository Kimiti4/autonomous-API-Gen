# POST_R1_D_LEGACY_BOUNDARY_RECONCILIATION (R1-RG-08)

**Status:** R1-RG-08. Legacy systems cannot become competing authorities. Spec: `folder/postr1d.md` §25.

---

## 1. Legacy status verification (baseline `66d7ceb`)

| Substrate | Status | Evidence |
|---|---|---|
| `constitutional_architecture/` (27+ engine files, EIR, Gen-C pipeline/passes/backends) | LEGACY, untouched in R1-D.3 | `git status` clean; zero canonical runtime imports (R1-D.3 + rg static tests) |
| Compiler bridge (`engine/compiler_bridge.py`) | DEAD, untouched | No callers (rg test) |
| Legacy ISR implementations (rich `System`, `UniversalISR`) | LEGACY, untouched | No canonical imports (rg tests); R1-D.1 PASS |
| Legacy EIR implementations | LEGACY, untouched | Canonical record surface is `EvolutionEvent`/history |
| Category-specific compilers (9, `compilers/*`) | LEGACY test-only | Consumers are `tests/test_*compiler*.py` only; none in `certification/` or canonical pipeline |
| Distributed evolution | INFRASTRUCTURE, untouched | Not imported by canonical evolution |
| `autonomous-api` | DEFERRED, untouched | Not in canonical path; `NotImplementedError` gap intact and documented |
| Legacy generated artifacts (`generated/`) | HISTORICAL, untouched | Not imported |

## 2. Authority test

For each legacy substrate: can it silently become a canonical authority? **No.** Canonical entry points (`plan_builder`, `runner`, `composition.build_backend_registry`, `ReferenceGenomeConstructor`, `SelfEvolutionEngine` defaults) resolve to canonical modules only (verified by import-walk in R1-D.2/R1-D.3 + rg tests). Legacy remains reachable only via explicit constitutional paths and tests.

## 3. Adapter audit

Adapters introduced across R1-C–R1-D.3: **zero bidirectional; zero new runtime adapters.** R1-C introduced one behavioral boundary fix (artifact purity) plus tests. R1-D.3 removed two bypasses by migration (no adapters). All cross-substrate references remaining are docstring provenance notes and test-only equivalence comparisons.

## 4. Verdict

Deletion is not required and not performed. Silent promotion is impossible by construction (import evidence). Gate requirement met.

---

*End of R1-RG-08.*
