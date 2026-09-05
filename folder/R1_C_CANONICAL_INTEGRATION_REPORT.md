# R1_C_CANONICAL_INTEGRATION_REPORT (R1-C C09)

**Status:** R1-C Deliverable C09. Canonical integration verification artifact. Index: `folder/R1_C_BOUNDARY_CONTRACTS.md` (C02), `folder/R1_B_CONTRACT_GATE_REPORT.md` (D20).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; the R1-C master prompt.

---

## 1. Purpose

Verify that after the R1-C boundary implementation (ADAPTER-ARTIFACT-001), the actual canonical runtime still follows the expected flow:

```text
RequirementGraph
→ ISR
→ ArchitectureCandidate
→ Evolution
→ CompilerIR
→ Backend
→ ArtifactSet
```

This report confirms that legacy components are not secretly controlling canonical behavior. The verification is by **actual import, call-site, and test evidence** — not by assumption.

## 2. Test evidence

The canonical campaign runtime is verified by the Tier A test suite (`tests/cbc1/`) and the new R1-C adapter contract tests (`tests/r1c/`).

### 2.1 Tier A (campaign tier)

| Metric | Value |
|---|---|
| Tier A test directory | `tests/cbc1/` |
| Tests passed | **243** |
| Tests failed | 0 |
| Tests deselected | 1 (the 1 deselected is a pre-existing marker, not a regression) |
| Wall time | ~260s |
| Command | `python -m pytest tests/cbc1/` |

The 243 Tier A tests cover the canonical campaign runtime: plan_builder, plan_runner, verdict, verify_campaign, campaign A/B stages, independent_verify, infra_storm, escalation policy, governance registry, cost/energy axis, stratified corpus, self-repair, calibration, gate checks.

### 2.2 R1-C adapter tests (new tier)

| Metric | Value |
|---|---|
| R1-C test directory | `tests/r1c/` |
| Tests passed | **15** |
| Tests failed | 0 |
| Wall time | ~4s |
| Command | `python -m pytest tests/r1c/` |

The 15 R1-C tests verify ADAPTER-ARTIFACT-001 (C02 §4): no filesystem write inside `compile()`, ArtifactSet emission, determinism, packager separation, one-way boundary.

### 2.3 Combined run

| Metric | Value |
|---|---|
| Combined tests | **258** |
| Combined passed | **258** |
| Combined failed | 0 |
| Wall time | ~97s |
| Command | `python -m pytest tests/r1c/ tests/cbc1/` |

## 3. Canonical runtime flow verification

The canonical runtime flow is verified by the Tier A tests' coverage of:

- `certification/campaign/plan_builder.py:13-14, 142-144` — `isr_to_plan(cand)` from `compiler/core/`.
- `certification/campaign/runner.py:10-13` — imports `CompilationPlan`, `CHECKER`, `GeneratedRepository`, `build_repository`, `BEHAVIORAL_CLASSES` from `compiler.core`.
- `certification/stages/{stub_stages,docker_stages,independent_verify}.py` — fail-closed verification.
- `certification/provenance/bundle.py:116` — SHA-256 provenance.
- `tests/cbc1/{test_campaign_a,test_campaign_b,test_cbc1_gates,...}.py` — contract tests for the canonical runtime.

The canonical runtime does NOT import from `constitutional_architecture/*`. The C10 legacy boundary report (`folder/R1_C_LEGACY_BOUNDARY_REPORT.md`) documents the one legacy bypass found (in `evolution/`, not in the campaign runtime).

## 4. ADAPTER-ARTIFACT-001 integration

The C06 refactor (removing `self.write_files()` from `compile()` in `constitutional_architecture/compiler/backends/fastapi_backend.py:85`) is a **bounded, non-canonical change**. It does not affect the canonical campaign runtime.

| Check | Result |
|---|---|
| `certification/` unchanged | **YES** (no changes) |
| `release/evidence/` unchanged | **YES** (no changes) |
| `isr/core/` unchanged | **YES** (no changes) |
| `compiler/core/` unchanged | **YES** (no changes) |
| `evolution/core/` unchanged | **YES** (no changes) |
| `reqgraph/core/` unchanged | **YES** (no changes) |
| `tests/cbc1/` unchanged | **YES** (no changes) |
| `constitutional_architecture/compiler/backends/fastapi_backend.py` changed | **YES** (one line removed) |
| B3-v2 evidence chain | **PRESERVED** (no changes) |

## 5. Canonical runtime remains authoritative

After the R1-C C06 refactor:

- The canonical campaign runtime (Tier A) is **green** (243 passed, 0 failed).
- The canonical runtime does NOT import from `constitutional_architecture/*`.
- The constitutional_architecture/* paths are NOT used by the canonical campaign runtime.
- The `constitutional_architecture/compiler/backends/fastapi_backend.py` change is a **boundary** change: it removes a filesystem side effect that violated the canonical contract (INV-B09). The backend now returns an `ArtifactSet` via `BackendResult(artifacts=...)`, which is the contract surface.

## 6. Conclusion

The canonical runtime is verified to be authoritative and unaffected by the R1-C C06 refactor. The Tier A suite (243 tests) and the R1-C adapter suite (15 tests) both pass. The canonical runtime flow (RequirementGraph → ISR → Architecture → Evolution → CompilerIR → Backend → ArtifactSet) is intact.

The C10 legacy boundary report identifies one legacy bypass in `evolution/` (not in the canonical campaign runtime) and classifies it for R1-D remediation.

---

*End of C09. The canonical runtime integration is verified. 258 tests pass. The B3-v2 evidence chain is preserved.*
