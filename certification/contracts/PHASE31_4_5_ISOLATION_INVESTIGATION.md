# Phase 31.4 / 31.5 — Phase Isolation Investigation

**Status:** INVESTIGATED (no parallelization justified at this time)
**Scope:** `tests/test_r29_31_4_scale_ramp.py` and
`tests/test_r29_31_5_certification.py` running concurrently in the
authoritative certification tier.
**Owner:** Governance Kernel

This is the investigation required by §4 of
[`PHASE31_EXECUTION_CONTRACT.md`](PHASE31_EXECUTION_CONTRACT.md) before
controlled parallelism can be introduced between 31.4 and 31.5. Each
of the five isolation conditions is examined against the actual code,
not against the conceptual architecture.

---

## Verdict

**The five isolation conditions are NOT met today.** 31.4 and 31.5
share mutable state at multiple layers. Running them in parallel
(either as concurrent threads within one pytest process, or as two
separate pytest processes) would either:

  (a) corrupt the evidence ledger,
  (b) produce non-reproducible evidence (race on the
      ConformanceEvidenceRegistry), or
  (c) produce non-replayable hash chains (the
      EvolutionLedger is process-internal, not inter-process safe).

This is a deliberate outcome of the architecture, not a defect:
the certification harness was designed around a single in-process
linear execution path (calibration → matrix → taxonomy → ramp →
certification, all on one ledger with one CampaignReadinessHarness),
and the contract is honest about that.

Therefore **the speedup mechanism for the certification tier remains
the shared-evidence bundle introduced in commit `ebe8712`** (one ramp
per session, one matrix per session, one taxonomy per session,
consumed by all five phase files). 31.5's 33-minute baseline is the
validated execution cost; 31.4's full ~30-min runtime is amortized
into 31.5 because 31.5 consumes 31.4's evidence.

---

## §4.1 — Do they share a mutable campaign state? — **YES**

**Finding:** Both phases bind to the SAME
`CampaignReadinessHarness` instance via the session-scoped
`phase31_base` fixture in `tests/conftest.py`.

What 31.4 mutates on the shared harness:

  - `scale_ramp_harness` (module-scoped) — consumes the
    pre-produced `phase31_ramp` report (already built once). No
    additional mutation.
  - `drift_ramp_harness` (module-scoped) — runs a full 26/100/500
    scale ramp with `campaign_id="drift-ramp"` on the shared
    `phase31_base.harness`, `phase31_base.intent_pipeline`,
    `phase31_base.registry`, `phase31_base.evaluator`,
    `phase31_base.verifier`, `phase31_base.conformance_registry`,
    `phase31_base.ledger`. The CampaignHarness.run() uses a
    `ThreadPoolExecutor(max_workers=4)`, so the drift ramp itself
    parallelizes across intents inside the harness.
  - `envelope_ramp_harness` (module-scoped) — runs a ramp with
    `campaign_id="envelope-probe"` and `budget_seconds=0.001` on
    the SAME shared state.

What 31.5 mutates on the shared harness:

  - `certification_rig` (module-scoped) — uses `phase31_base` and
    `phase31_evidence`. The `certify()` method calls the canary
    RE-RUN, which in turn calls the `MatrixHarness` (re-running the
    canary subset against all 7 backends) on the shared
    `phase31_base.ledger` and `phase31_base.registry`.
  - `test_grounding_rejects_foreign_semantics` — calls
    `rig.base.compilation.compile(isr, target)` on the shared
    `CampaignCompilation`, which routes through the shared
    `BackendRegistry`.

The shared mutable surfaces are:

  - `EvolutionLedger._events` and `_records` (in-memory lists,
    guarded by `threading.Lock`).
  - `ConformanceEvidenceRegistry._refs` (a `set[str]`, NO LOCK).
  - `BackendRegistry._backend_factories`, `_seams`, `_targets`
    (read-only after construction).
  - `ArtifactVerifier._ledger`, `ArtifactVerifier._conformance_registry`
    (read-only references; writes are routed through the ledger).
  - `BackendConformanceAdapter.findings` (read-only per compile
    call; populated at construction).

**Concurrent-write risk to `ConformanceEvidenceRegistry._refs`:**
The registry has no lock. `ArtifactVerifier.verify()` reads
`conformance_registry.has(ref)` while a concurrent `register()`
mutates `_refs`. CPython's GIL protects dict/set operations at the
C level (atomicity for single opcodes), but the compound
read-then-decide pattern in `has()` is not transactional. Under
concurrent drift-ramp + certifier execution, a verify call could
see a `_refs` state inconsistent with the ledger at the moment of
its decision.

---

## §4.2 — Do they share a port range? — **N/A**

**Finding:** Neither 31.4 nor 31.5 uses real Docker, allocated
ports, or the port pool.

The certification tier (Tier C) operates entirely on the
in-process `CampaignHarness` plus its in-process
`CampaignCompilation` / `ArtifactVerifier` / `ConformanceEvidenceRegistry`.
The `CampaignHarness.run()` method runs each intent on a Python
thread, never spawning a Docker container. There is no port
preflight, no `port_preflight.json` evidence, and no port pool
allocation in this tier.

The port pool (`release/evidence/cbc1-B3-portpool.json`) is used
ONLY by the real-Docker Tier B (`pytest -m docker_integration`)
and by the B-wave executors. It is irrelevant to Phase 31.4/31.5.

**Parallelism risk on ports:** NONE.

---

## §4.3 — Do they share an evidence ledger? — **YES**

**Finding:** Both phases append events to the SAME
`EvolutionLedger` instance, which persists to the SAME JSONL file
on disk.

Mechanism (from `tests/conftest.py`):

```python
@pytest.fixture(scope="session")
def phase31_base():
    return CampaignReadinessHarness()
```

`CampaignReadinessHarness.__init__()` creates
`self.ledger = EvolutionLedger(root=self._tmp.name)`, where
`self._tmp` is a `tempfile.TemporaryDirectory()`. Therefore every
test that depends on `phase31_base` (directly or transitively) shares
ONE EvolutionLedger backed by ONE JSONL file inside ONE temp
directory.

What 31.4 appends to that ledger:

  - The shared `phase31_ramp` event (`scale-ramp-dry-run-1`,
    per-level events for 26/100/500).
  - The drift ramp event (`scale-ramp-drift-ramp`, per-level events).
  - The envelope ramp event (`scale-ramp-envelope-probe`,
    per-level events; one level because of the 1ms budget).

What 31.5 appends to that ledger:

  - The canary RE-RUN matrix event (from `CertificationHarness.certify()`).
  - The certification event (`cert-31-5`, payload includes
    dimensions, measured_envelope, content_hash).
  - Possibly a verification event from
    `test_grounding_rejects_foreign_semantics` if
    `rig.base.verifier` is invoked.

**Inter-process risk:** The `EvolutionLedger._append_lock` is a
`threading.Lock` — thread-safe within one process, NOT safe across
processes. Two pytest workers writing to the same JSONL file would
race on `open(..., "a")` and the `_last_hash` read, producing a
broken hash chain (the parent of event N+1 would be computed from
whichever process happened to write last).

**Inter-thread risk within one process:** The `_append_lock`
serializes appends. But the `EventType.SCALE_RAMP` event written
by 31.4's drift ramp and the `EventType.MATRIX` event written by
31.5's canary are ordered correctly because the lock governs both.
However, ordering is determined by the test scheduling: 31.4's
`test_verdict_not_ready_when_canary_drifts` runs the drift ramp
before 31.5's tests start (because 31.4's module-scoped
`drift_ramp_harness` is built on first use, and 31.4's tests
typically execute first by file order). This incidental ordering
is not a contract — pytest file order is a configuration knob.

---

## §4.4 — Do they share a backend singleton? — **YES**

**Finding:** Both phases read from the same `BackendRegistry`
(7 factories, 7 seams, 7 targets), the same `ArtifactVerifier`,
the same `BackendConformanceEvaluator`, and the same
`ContaminationGuard`.

The compiled backend classes
(`ReferenceCompilerBackend` instances for the 7 backends:
react, fastapi, postgres, terraform, cicd, pytest, markdown) are
**singletons** within the registry. Their `compile()` methods are
read-only (no `self.*` mutation) — verified by reading
`tiannara/application/compilation/reference_backend.py:110-185`
and `backend_conformance.py:282-333`. So no two concurrent compile
calls would corrupt each other's artifact output.

**However:** `BackendConformanceAdapter.findings` is a mutable
list (not a frozenset) populated at construction. It is shared
across all `conform()` calls on the same adapter. The
`BackendConformanceEvaluator.conform()` method (lines 422-477)
appends to local `findings: list[str]` and creates a NEW
`BackendConformanceReport` per call — so per-call report
construction is isolated. The shared adapter's `self.findings` is
only read, never appended to. So this is also safe.

**Concurrent-write risk to a backend singleton:** NEGLIGIBLE
(given read-only `compile()` and per-call report construction).

The dominant risk here is §4.3 (ledger) and §4.1
(`ConformanceEvidenceRegistry._refs`).

---

## §4.5 — Can each be run independently in a separate pytest
invocation and produce equivalent evidence? — **NO** (not without
fixture restructuring)

**Finding:** The current conftest pins 31.4 and 31.5 to the SAME
`phase31_base` and `phase31_evidence` fixtures. Separating them
would require:

  - Splitting `phase31_base` into two independent harnesses
    (e.g. `phase31_4_base` and `phase31_5_base`).
  - Producing the matrix + taxonomy + ramp once on the 31.4
    harness, and exposing them to 31.5 via a different mechanism
    (a snapshot/serialize step, or a second fixture that
    materializes from the 31.4 evidence).
  - Accepting that 31.5 would need to re-run matrix/taxonomy/ramp
    on its OWN harness, OR that the evidence is shipped across
    processes (which loses the hash chain continuity by
    construction — the chain is per-ledger).

**Equivalent evidence would be: a 31.5 certification that verifies
the same events on the same ISR/corpus, possibly produced by a
DIFFERENT ledger, and links to the 31.4 ledger via evidence_refs.**

Today, this is not implemented. The certifier is hard-wired to
read events from `self.base.ledger` (the shared session-scoped
ledger). It would need an `external_evidence_refs: dict[str, str]`
parameter to accept evidence from a sibling ledger.

---

## What the architecture gets right

These findings are not a critique of the current design — they
describe the intended single-process linear certification model.
The architecture is correctly optimized for:

  - A single pytest session that runs 31.1 → 31.2 → 31.3 → 31.4
    → 31.5 in sequence.
  - A single shared ledger with a single hash chain.
  - A single in-process CampaignHarness.
  - A single BackendRegistry of compiled backends.

This is exactly the model required by §1 of the contract
(evidence is immutable, retries are new executions, retries append
to the chain). Parallelization would require inventing a new
mechanism (multi-ledger cross-references, snapshot serialization,
process-safe file locking) that the contract currently prohibits
as "hidden parallelism on shared ledgers".

---

## What COULD be parallelized safely (but does not pay off)

These are the only safe parallelization surfaces in the current
architecture:

1. **Matrix × taxonomy × ramp — already shared once per session**
   (commit `ebe8712`). No additional parallelization is available
   without forking the ledger.

2. **Per-intent compilation within the campaign harness — already
   parallelized.** `CampaignHarness.run()` uses
   `ThreadPoolExecutor(max_workers=4)` (from `ResourceBudget`).
   Increasing `max_parallel` would parallelize the campaign
   further, but this is a CampaignHarness-level optimization, not
   a Phase 31.4/31.5 isolation question.

3. **Drift ramp (31.4) vs canary re-run (31.5) — could be
   parallelized in principle** if the drift ramp were to write
   to a SEPARATE ledger and the certification read from a
   UNION of ledgers via stable event_refs. This would require
   (a) ledger serialization, (b) a multi-ledger verification
   mode, (c) refactoring `CertificationRig.make_certifier()` to
   accept an `external_evidence: dict[str, str]` parameter, and
   (d) a re-verified test suite. Estimated effort: 1–2 days
   of refactoring plus full re-run. Estimated speedup: ~5–10
   minutes off the 33-min baseline (drift ramp is ~10 min, canary
   re-run is ~3 min; they don't fully overlap because the canary
   re-run reads the drift ramp's results via the shared ledger).

   **Verdict:** not worth the complexity at this time.

---

## Conclusion

**The 33-minute certification baseline is the validated execution
cost.** It is the result of the single-correct shared-evidence
architecture, not a defect of slow code.

The investigation confirms:

  - §4.1 (shared mutable state): NOT isolated
  - §4.2 (ports): N/A (in-process, no ports)
  - §4.3 (shared ledger): NOT isolated
  - §4.4 (backend singletons): isolated for compile reads, NOT
    isolated for the ConformanceEvidenceRegistry
  - §4.5 (independent pytest invocations): NOT supported

Therefore the **only certification-tier speedup mechanism
contract-permitted by §3 and proven by §4 to be safe** is the
shared-evidence bundle (commit `ebe8712`).

**Recommendation:** Keep the certification tier at the 33-minute
single-process baseline. Any further speedup is now bounded by
**the cost of a single full scale-ramp run** (~10 min for
reachable_top=500). Reducing that would require a separate
architectural change with its own risk profile and is out of
scope for the current no-workload-reduction contract.

---

## Next architectural step (out of scope here)

If a future contract revision allows safe multi-ledger
certification, the work would be:

1. Add a stable, content-addressed evidence export
   (write each event to a separate file keyed by
   `event_hash`).
2. Add a `MultiLedgerVerifier` that accepts a list of
   ledgers and cross-references via evidence_refs.
3. Refactor `CertificationRig.make_certifier()` to accept
   `external_evidence: dict[str, EvolutionEvent]`.
4. Refactor `test_r29_31_4_scale_ramp.py` to run drift_ramp
   on its own ledger.
5. Add a contract amendment allowing "multi-process
   certification with external evidence union" as a
   permitted optimization.

This is recorded as the Phase 32 candidate optimization,
NOT acted on now.
