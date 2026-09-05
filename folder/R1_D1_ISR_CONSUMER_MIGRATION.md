# R1_D1_ISR_CONSUMER_MIGRATION (R1-D.1 D5)

**Status:** R1-D.1 Deliverable D5. ISR consumer migration report. Index: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md` (D1), `folder/R1_D1_ISR_MIGRATION_MAP.md` (D4).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

---

## 1. Purpose

Document every consumer of the canonical ISR and its migration state. The R1-D.1 master prompt requires: "Identify all production consumers of non-canonical ISR implementations. For each: consumer, current ISR, dependency type, migration strategy, status."

---

## 2. Canonical ISR consumers

These are the consumers of the canonical ISR (`isr/core/*`). They are already on the canonical substrate and require **no migration** in R1-D.1.

| Consumer | Path | Import | Dependency type | Migration strategy | Status |
|---|---|---|---|---|---|
| Plan builder | `certification/campaign/plan_builder.py:19-20` | `isr.core.identity.compute_content_hash`, `isr.core.revision.ISRRevision` | Direct | None (already canonical) | **KEEP** |
| Evolution engine | `evolution/core/engine.py:21-22` | `isr.core.graph.{Edge, EdgeType, ISRGraph, Node, NodeType}` | Direct | None | **KEEP** |
| Evolution construction | `evolution/core/construction.py:5-6` | `isr.core.revision.ISRRevision` | Direct | None | **KEEP** |
| Evolution fitness | `evolution/core/fitness_evaluator.py:7-8` | `isr.core.*` | Direct | None | **KEEP** |
| Evolution materialize | `evolution/core/materialize.py:5` | `isr.core.*` | Direct | None | **KEEP** |
| Genesis mapper | `genesis/mapper.py:8` | `isr.core.*` | Direct | None | **KEEP** |
| Genesis validator | `genesis/validator.py:7-9` | `isr.core.*` | Direct | None | **KEEP** |
| ISR ports | `isr/ports/{reader,store}.py` | `isr.core.revision.ISRRevision` | Direct | None | **KEEP** |
| ISR adapters | `isr/adapters/inmemory.py` | `isr.core.*` | Direct | None | **KEEP** |
| ISR schema | `isr/schema/versions.py` | `isr.core.*` | Direct | None | **KEEP** |
| Tier A tests | `tests/cbc1/*` | `isr.core.*` | Test | None | **KEEP** |
| v12 tests | `tests/v12/*` | `isr.core.*` | Test | None | **KEEP** |
| v13 tests | `tests/v13/*` | `isr.core.*` | Test | None | **KEEP** |
| v14 tests | `tests/v14/*` | `isr.core.*` | Test | None | **KEEP** |
| Test substrate | `tests/test_isr_substrate_v12.py:18-22` | `isr.core.*` | Test | None | **KEEP** |
| R1-C tests | `tests/r1c/*` | None (uses constitutional) | Test | None | **KEEP** |
| R1-D.1 tests | `tests/r1d1/*` | `isr.core.*` | Test | None | **KEEP** |

**Total: 17 canonical ISR consumers, all KEEP (no migration required).**

---

## 3. Constitutional ISR consumers

These are the consumers of the constitutional ISR implementations. They are **not in the canonical runtime path** and are either **LEGACY** (to be retired) or **DEFER** (out of R1-D.1 scope).

| Consumer | Path | Import | Migration strategy | Status |
|---|---|---|---|---|
| Constitutional compiler | `constitutional_architecture/compiler/*` | `constitutional_architecture.isr.*` | Retired (R1-D.5; not in canonical runtime) | **LEGACY → RETIRE** |
| Constitutional engine | `constitutional_architecture/engine/*` | `constitutional_architecture.isr.*` | Retired (R1-D.5) | **LEGACY → RETIRE** |
| Constitutional per-category compilers | `constitutional_architecture/compilers/*` | `constitutional_architecture.isr.*` via `UniversalISR` | Retired (R1-D.5; INV-B14) | **LEGACY → RETIRE** |
| Constitutional tests | `constitutional_architecture/tests/test_end_to_end.py:68, 567` | `constitutional_architecture.isr.*` | Retired (R1-D.5; not in Tier A) | **LEGACY → RETIRE** |
| Constitutional TypedGraph tests | `constitutional_architecture/tests/test_{isr_to,graph_to_isr}.py` | `constitutional_architecture.isr.*` | Retired (R1-D.5) | **LEGACY → RETIRE** |
| Test: backend field order | `tests/test_backend_field_order_regression.py` | (uses `tiannara.application.compiler.fastapi_hexagonal_backend`, NOT constitutional) | None (not a constitutional consumer) | **N/A** |
| Test: production backends | `tests/test_production_backends.py` | `compiler.backends.production.fastapi_backend.FastAPIFoundationBackend` (Gen-A) | None (Gen-A is not constitutional) | **N/A** |
| Test: multi-backend | `tests/v14/test_multi_backend.py` | `compiler.backends.python_fastapi.PythonFastAPIBackend` (Gen-B, canonical) | None | **N/A** |

**Total: 5 constitutional ISR consumers, all LEGACY → RETIRE (R1-D.5).**

---

## 4. Consumer migration summary

| Category | Count | Status |
|---|---|---|
| Canonical ISR consumers | 17 | KEEP (no migration) |
| Constitutional ISR consumers | 5 | LEGACY → RETIRE (R1-D.5) |
| **Total** | **22** | |

---

## 5. Verdict

The canonical ISR has **17 direct consumers** in the canonical runtime. None require migration. The constitutional ISR has **5 consumers**, all in the constitutional substrate and all classified for retirement in R1-D.5 (per D17 L01).

The R1-D.1 MIGRATE semantics (M-01, M-02, M-03) are **additive** to the canonical ISR. They do not change the canonical ISR's existing API or contract. The 17 canonical consumers continue to work without changes.

---

## 6. Cross-references

- D1: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md`
- D4: `folder/R1_D1_ISR_MIGRATION_MAP.md`
- D6: `folder/R1_D1_ISR_LEGACY_DISPOSITION.md` (next)
- R1-C C10: `folder/R1_C_LEGACY_BOUNDARY_REPORT.md` (2 findings in `evolution/`)

---

*End of D5. The R1-D.1 consumer migration is complete. 17 canonical consumers KEEP; 5 constitutional consumers LEGACY → RETIRE. No canonical consumer requires migration.*
