# VS1_IMPLEMENTATION_D25 (VS-D25)

**Status:** VS-1 Deliverable VS-D25. Implementation of the D24-selected
query-policy-separation architecture for VS1-OBJ-001.
**Governance:** IMPLEMENTATION ONLY. Compiles selection → executable
`vs1-impl-obj001-v1`; no deployment, observation, production change,
commit, or push.

---

## 1. What was built

`vertical_slice/app_v3/` (new namespace; parents untouched):
- `models.py` — TaskV3 (v1 Task + closed priority), all other models reused.
- `policy.py` — PriorityQueryPolicy: validation, MEDIUM legacy default,
  filter-semantics decisions. Authorization-adjacent, never authorization.
- `tasks.py` — TaskV3Repository adapter over the shared store (parent task
  methods construct v1 Task and cannot hold priority; parent unmodified).
- `service.py` — v2-identical behavior for all prior ops; priority paths
  delegate to the policy; membership always precedes priority logic.
- `api.py` — same routes + priority in create/update bodies, `?priority=`
  filter with fail-closed validation, priority serialized on reads.

Priority is data, never authority; invalid values 422; legacy (incl.
v2-written) records read MEDIUM; restart durability verified both ways;
events unchanged in name/producer.

## 2. Fidelity & lineage

14 component mappings implementation → architecture → candidate → ISR →
obligation, all resolving. Structural drift detection proves both policy
delegations, the repository seam, and no new event/auth boundaries.
SC01–SC07 answered by components; SC08–SC13 are downstream-gate
obligations with named proof sites (never faked as rows).

## 3. Frontend scope note

This slice has no UI layer; the display/filter surface is the API read
model (priority serialized, `?priority=` contract), which a UI consumes.
No UI invented to satisfy SC06/SC07 cosmetically.

## 4. Integrity & tests

D01–D24 + ISR unchanged; parents byte-stable; B3-v2 chain intact.
`tests/vs1/test_implementation_d25.py`: 63/63 (T01–T62). Identity
`7dbbf34fe75660f1…` content-addressed over canonical sources.
Uncommitted per contract.

---

## 5. Actuator supplement (folder/D25.md assessment)

The D25.md actuator model was assessed line-by-line (1973 lines) against
this implementation. Adopted as a supplement, not a replacement:

- `vertical_slice/d25_authority_actuator.py` — verify-before-write
  transaction (`--plan-only` emits nothing; `--write` emits only the
  actuator-owned manifest + handoff), runtime `ActionFirewall`, upstream
  overwrite guard, systematic `redact()`, standardized BLOCKED report.
- `vertical_slice/behavior_evidence_d25.json` — 33/33 checks generated
  from a fresh D25 suite run, bound to the actuator identity hash.
- `vertical_slice/implementation_d25_manifest.json`,
  `vertical_slice/deployment_handoff_d25.json` — standalone delivery
  artifacts; downstream gates consume proofs without rerunning tests.
- `tests/vs1/test_d25_authority_actuator.py` — 13/13.

Documented deviations (constitutional, not convenience): real artifact
paths; canonical ISR hash (spec text slip); `ensure_ascii=False` repo
standard; D24 validated in its frozen shape via an explicit adaptation
table (D24 never rewritten to fit); frontend proven via the API read
model (no UI layer in slice). Verified live: plan-only green with zero
writes; tampered/missing behavior evidence BLOCKS with exit 1.

---

*End of VS-D25 artifact. Report follows separately (uncommitted).*
