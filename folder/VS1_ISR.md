# VS1_ISR (VS-D02)

**Status:** VS-1 Deliverable VS-D02. Canonical ISR for the slice.
**Spec:** `folder/vs1.md` (VS-D02).
**Upstream (frozen):** `folder/VS1_REQUIREMENTS.md` (`7340e93`).

---

## 1. Construction

Builder: `vertical_slice/isr.py:build_task_tracker_isr()` (deterministic;
fixed provenance timestamp; stable IDs; no randomness). It consumes the
frozen VS-D01 graph and raises `ValueError` on any lineage break (requirement
ID missing upstream) before ISR construction.

| Surface | Count | Detail |
|---|---|---|
| Nodes | 32 | 8 CAPABILITY, 11 REQUIREMENT_REF (8 functional + 3 non-functional), 3 SERVICE, 3 API, 3 DATA_MODEL, 2 EVENT, 2 SECURITY_POLICY |
| Edges | 33 | 8 SATISFIES, 8 IMPLEMENTED_BY, 3 EXPOSES, 4 PERSISTS, 2 PUBLISHES, 6 SECURED_BY, 2 DEPENDS_ON |
| Identity | `vs1-task-tracker` / `vs1-rev1` / schema `1.0` | content hash (SHA-256, 64 hex) stable across builds |
| Provenance | `created_by=vs1-slice` | `requirement_refs` = all functional/non-functional/constraint IDs; `derivation_refs` = intake + builder versions |

## 2. Lineage

Every REQUIREMENT_REF `ref_id` resolves to a node in the frozen VS-D01 graph
(pinned by test). Provenance carries the full requirement ID list plus
`vs1-manual-intake-v1`. No requirement semantics are duplicated: the ISR
references requirements; it does not redefine them.

## 3. Technology neutrality

`validate_invariants` passes fail-closed, covering the 25 forbidden
implementation terms and the 10 R1-D.1 testing-mechanism terms. Service labels
("identity/task/workspace service"), entity names, and event labels use
domain language only.

## 4. Coverage notes (honest)

- Non-functional requirements are lineage-bound via REQUIREMENT_REF and
  structurally enforced (SECURED_BY policies, PERSISTS edges); only functional
  capabilities carry SATISFIES edges. This matches the canonical 9-node
  taxonomy without inventing node types.
- Events cover lifecycle occurrences (`task-created`, `task-updated`);
  assignment is a capability on the update path, not a separate event.
- Deferred `req-anon-sharing` has no ISR representation (correct: deferred
  requirements do not enter the canonical revision).

## 5. Evidence

- `python -m pytest tests/vs1/ -q` → **15 passed** (7 VS-D01 + 8 VS-D02).
- `validate_invariants` passes on the built revision.
- Determinism: two builds compare equal, content hash stable.
- Baseline suites untouched by this deliverable (verified at gate time).

## 6. Forward reference (not implemented here)

VS-D03 consumes: capability IDs, service topology, and the revision content
hash for candidate construction. No architecture/evolution, compiler, backend,
deployment, observation, or evolution work is part of VS-D02.

---

*End of VS-D02. Next: VS-D03 (candidates + selection) under separate authorization.*
