# VS1_REQUIREMENTS (VS-D01)

**Status:** VS-1 Deliverable VS-D01. Slice requirements + RequirementGraph.
**Spec:** `folder/vs1.md` §§2 (VS-D01), 6 (VS-D01), 10 (commit group 1).
**Product:** Task-tracking CRUD SaaS (one category, one representative product).
**Intake:** manual (`vs1-manual-intake-v1`). Autonomous intake is NOT required for VS-1.

---

## 1. Product statement

A multi-user task tracker: people authenticate, organize in workspaces with
member roles, and perform full task lifecycle (create, read, update, delete,
assign) with credential safety, workspace isolation, and durable state.

Out of scope for the slice: anonymous link sharing (deferred by explicit
decision `decision-vs1-01`), notifications, file attachments, search, and any
second product category.

## 2. RequirementGraph construction

Builder: `vertical_slice/requirements.py:build_task_tracker_requirements()`
(deterministic; stable string IDs; frozen Pydantic via `reqgraph/core`).

| Surface | Count | Detail |
|---|---|---|
| Nodes | 19 | 2 stakeholders, 3 domain concepts, 8 functional (auth ×2, CRUD ×4, assign, membership), 3 non-functional, 2 constraints, 1 deferred alternative |
| Edges | 36 | 17 OWNED_BY, 10 DEPENDS_ON, 8 REFINES, 1 resolved CONFLICTS_WITH |
| Conflicts | 1 | `req-anon-sharing` vs `req-tenant-isolation`, resolved by `decision-vs1-01` (deferred; auth required) |
| Ambiguity | ≤ 0.3 everywhere | only `req-anon-sharing` (0.3) carries ambiguity, with resolution_ref |

Key dependency chains: login → register; CRUD → login; update/delete/assign →
create; membership → login; isolation → membership; credential-safety →
register; durability → create. Refinements bind each functional requirement to
its domain concept (task, workspace, user-account).

## 3. Technology neutrality

Every statement and acceptance criterion avoids implementation terms
(`FORBIDDEN_IMPLEMENTATION_TERMS`: no fastapi/postgres/docker/react/pytest/…).
"Durable storage" and "process restarts" are used instead of product names.
Enforced fail-closed by `validate_requirement_graph` (leakage check over
properties and acceptance criteria) and pinned by test
`test_technology_neutral_statements`.

## 4. Manual-intake rationale

Per `folder/vs1.md`, autonomous intake is out of scope: VS-1 proves the
generation/evolution loop, not requirement mining. Manual intake is recorded
via `source_refs=[vs1-manual-intake-v1]` on every node, preserving provenance
for the downstream ISR (VS-D02 consumes these IDs).

## 5. Evidence

- `python -m pytest tests/vs1/ -q` → **7 passed**.
- `validate_requirement_graph` passes fail-closed on the built graph.
- Determinism: two builds compare equal.
- Baseline suites untouched by this deliverable (verified at gate time).

## 6. Forward reference (not implemented here)

VS-D02 consumes: node IDs (especially `REQUIREMENT_REF`-eligible functional
requirements), `ref_id` lineage, and the resolved-conflict decision. No ISR,
compiler, or backend work is part of VS-D01.

---

*End of VS-D01. Next: VS-D02 (canonical ISR) under separate authorization.*
