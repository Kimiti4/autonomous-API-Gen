# AGENTS.md

Local engineering guidance for the **Cognitive Architecture** workspace
(`C:\Users\user\New folder (2)`).

## Project at a glance

This workspace is a multi-phase cognitive-architecture build. The canonical
Python project is configured in `pyproject.toml` ("Phase 23 Enterprise Knowledge
Graph runtime"). Its **unit-test suite lives under `tests/`**.

Notable top-level packages (all importable from the workspace root):
`compiler`, `knowledge`, `civilization`, `evolution`, `product_factory`,
`learning`, `constitutional_architecture`.

## Running the tests

Canonical command:

```bash
python -m pytest
```

What this does (configured in `pyproject.toml` under `[tool.pytest.ini_options]`):

- `testpaths = ["tests"]` — runs the project unit suite only.
- `addopts = "--import-mode=importlib -m 'not docker_integration and not certification'"` — avoids the
  `ModuleNotFoundError: No module named 'tests.test_*'` collection collisions
  caused by the multiple `*/tests/` packages across `autonomous-api/`,
  `constitutional_architecture/`, and `generated/`, and excludes the
  real-Docker integration gates and the expensive Phase 31 certification
  harness from the canonical run.
- `pythonpath = ["."]` — puts the workspace root on `sys.path` so root-level
  packages (`compiler`, `knowledge`, `learning`, …) import cleanly when pytest
  is invoked directly.

### Test tiers

The suite is split into three scheduling tiers so the normal development loop
stays fast while the authoritative release gate still runs the full evidence.

- **Tier A — fast unit/contract (default).** `python -m pytest` runs only the
  fast suite: classifiers, policies, contracts, ledger invariants, lineage,
  serialization, gates, and the `tests/cbc1/` self-repair suite. Expected:
  **~2786 passed** in ~12 minutes (markers `certification` and
  `docker_integration` are deselected).
- **Tier C — certification (expensive, explicit).**
  `python -m pytest -m certification` runs the authoritative Phase 31
  certification harness — scale ramp 26/100/500, full 7-backend matrix, full
  failure-taxonomy validation, fresh calibration. Last verified: **40/40
  passed in 33 min**. MUST NOT be weakened to speed the suite up. **The
  release pipeline runs this complete suite before any new B3 wave.**
- **Tier B — integration.** Real-Docker gates are opt-in with
  `python -m pytest -m docker_integration`.

### Phase 31 execution contract

The Phase 31 certification tier follows the no-workload-reduction contract in
[`certification/contracts/PHASE31_EXECUTION_CONTRACT.md`](certification/contracts/PHASE31_EXECUTION_CONTRACT.md).
Key points:

  - Calibration + matrix + taxonomy + scale-ramp are produced exactly **once
    per session** as immutable evidence, via session-scoped fixtures in
    `tests/conftest.py` (`phase31_base`, `phase31_calibration`,
    `phase31_matrix`, `phase31_taxonomy`, `phase31_ramp`, `phase31_evidence`).
  - The certification (`test_r29_31_5_certification.py`) CONSUMES the shared
    evidence bundle — it never rebuilds the campaign. The canary RE-RUN
    remains mandatory (reproducibility proof) and the novelty check remains
    live.
  - Permitted optimizations: fixture/evidence reuse, layer/artifact caching,
    process isolation, test scheduling.
  - Forbidden optimizations: workload reduction (fewer scale levels /
    backends), evidence substitution, skipped stages, weakened assertions,
    mutable state reuse, hidden parallelism on shared ledgers/ports.

### Integration / out-of-suite tests

The following are **not** part of the canonical run and require extra
infrastructure — do not treat their absence as a unit-suite regression:

- `autonomous-api/**/*.py` tests (e.g. `autonomous-api/test_production.py`,
  `autonomous-api/test_system.py`) — exercise a live FastAPI service on
  `localhost:8000` and depend on the `autonomous-api/.venv` virtual environment.
  Start the API (`uvicorn app.main:app`) inside that venv first.
- `generated/testshop` and `generated/monolithshop` tests — `async def`
  in-process FastAPI tests marked `@pytest.mark.asyncio`; they require
  `pytest-asyncio` (or the asyncio fallback in
  `autonomous-api/tests/conftest.py`) and the `generated/*` packages to be
  importable.
- `constitutional_architecture/tests/test_end_to_end.py` — imports a symbol
  (`Dependency`) that does not exist in `constitutional_architecture.isr.model`.

## Adding/editing files

- Prefer editing existing files over creating new ones.
- Follow existing code conventions (see neighboring modules).
- The `learning/` package (Phase 26) converts telemetry into governed
  evolutionary feedback; it must **not** mutate the ISR directly — output flows
  through governance and the Evolution Engine.

## Notes

- The stray `C:\Users\user\New folder (2)\(2)` directory is a partial duplicate
  of `constitutional_architecture/` and is intentionally ignored (it is not in
  `testpaths`).
- Phase 28 (Governance Kernel) is wired and covered by the unit suite:
  - **Cryptographic evidence signing** — `GovernedKernel`'s evidence path is
    config-gated via `new_evidence_recorder()` (`AUDIT_EVIDENCE_SIGNING_KEY`
    env var). When set, each `AuditEvidenceISR` is HMAC-SHA256 signed over its
    chain-linked content (including `chain_link`); when unset, records are
    unsigned and an observable warning is emitted. `EvidenceSigner` is a
    Protocol seam — an asymmetric (e.g. Ed25519) signer can be dropped in
    later for true non-repudiation.
  - **Durable version repository** — `FileBackedConstitutionVersionRepository`
    (atomic writes + `fsync`) is a drop-in swap for the in-memory reference
    adapter; `test_governance_versioning_durable.py` proves the ratified
    constitutional version chain survives instance restarts.
- **Phase 31 — Stratified Calibration Harness (`tiannara/`).** Implements the
  certification harness from `folder/31.md`: a dependency-inverted
  Intent→ISR→Evolution→Compile→Verify→Gate→Evidence-Ledger→Publish pipeline
  with local reference adapters (JSONL SHA-256 hash-chain evidence ledger, local
  execution environment, minimal compiler backend, stub intent compiler,
  baseline evolution engine, local/git-over-HTTPS repository publisher,
  env-based settings, CLI composition root). GitHub/Docker/workflow-engine are
  plug-in ports; see `folder/31.md` Closure Record.
- **Infra-storm side-channel (`certification/evidence/infra_storm.py`).** A
  separate, hash-chained JSONL ledger (`cbc1-{wave}-infra-storm.jsonl`) that
  captures every infrastructure-classified trial failure during a Campaign B
  wave. It is LEARN-ONLY — never feeds the certifier, never auto-evolves
  (per master prompt §13). Opt-out via `CBC1_INFRA_STORM=0`. See
  `certification/contracts/PHASE31_EXECUTION_CONTRACT.md` §1.5 and
  `tests/cbc1/test_infra_storm_ledger.py` for the contract and tests.
- **100-project stratified corpus (`certification/corpus/stratified_corpus.py`).**
  Phase 31's scale-up milestone (the spec's "Immediate Next Step"): 100
  technology-free `CorpusIntent` entries stratified across the 13
  `ProjectCategory` × 3 complexity tiers (4 simple + 2 moderate + 2 complex
  per category = 8; 4 simple entries dropped to land at exactly 100,
  documented). Reproducible (SHA-256 hash) and technology-leakage-free
  (no postgres, fastapi, rust, etc.). See `tests/cbc1/test_stratified_corpus.py`
  for the 17 contract tests.
- Python: 3.14.0 is the interpreter on PATH for `python -m pytest`.
