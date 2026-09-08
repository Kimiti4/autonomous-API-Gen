# VS1_CANDIDATES (VS-D03)

**Status:** VS-1 Deliverable VS-D03. Candidate set + deterministic selection.
**Spec:** VS-D03 authorization prompt (§§1–21).
**Governance:** SELECTION ONLY. Ends at SELECTION DECISION — see §14.

---

## 1. Governance status

VS-D03 executed under explicit authorization. Upstream frozen inputs verified
before work (§4): `folder/VS1_REQUIREMENTS.md` last committed at `7340e93`,
`folder/VS1_ISR.md` at `0c06f48`, working tree clean for tracked files.
No upstream modification performed.

## 2. Frozen upstream inputs

| Artifact | Commit | Content identity |
|---|---|---|
| VS-D01 requirements graph | `7340e93` | sha256 `28548494e754e9b8…` (canonical JSON) |
| VS-D02 ISR revision | `0c06f48` | content hash `48e53dcef47aad84…` |
| Builder | `vertical_slice/candidates.py` | `vs1-candidates-v1` |
| Candidate schema | — | `vs1-candidate-v1` |
| Selection policy | — | `vs1-selection-v1` |

Upstream identities are recorded in every candidate's provenance tuple, so
accidental drift is detectable by hash comparison.

## 3. Candidate schema

Per authorization §5. Each candidate carries: `candidate_id`,
`candidate_version`, `description`, `implementation_profile`,
`technology_profile`, `requirement_coverage`, `isr_coverage`,
`constraints_satisfied`, `security_posture`, `operational_complexity`,
`cross_service_dependencies`, `resource_units`, `risk_ordinal`,
`risk_rationale`, `provenance`. IDs are stable strings; no timestamps enter
generation, scoring, ranking, or selection.

## 4. Candidate set

Exactly 2 candidates (bounded; each a materially distinct profile).

### vs1-candidate-a — consolidated-monolith

- Exists because a single-service profile is the simplest topology satisfying
  the ISR's three services without cross-service calls.
- Architectural choice: consolidate identity/task/workspace behind one runtime.
- Satisfies: all 12 covered requirements (8 MUST functional incl. CRUD+auth,
  SHOULD assign/membership/durability, MUST credential-safety/isolation,
  both constraints), all 8 capabilities + 3 services + APIs/models/policies.
- Tradeoffs: single failure domain; scaling is coarse.
- Risks: low (risk_ordinal=1) — fewest moving parts, no network partitions
  between services.

### vs1-candidate-b — decomposed-services

- Exists because the ISR declares three services with explicit DEPENDS_ON
  edges; a profile mirroring that topology is the natural alternative.
- Architectural choice: one runtime per ISR service (identity/task/workspace).
- Satisfies: same requirement/ISR coverage as candidate A.
- Tradeoffs: isolation and independent evolution per service; 2 cross-service
  dependencies; 4 resource units vs 2.
- Risks: medium (risk_ordinal=2) — cross-service calls, more failure modes.

No candidate was fabricated for count: both profiles are grounded in the ISR
topology (consolidate vs mirror). Technology profiles name fastapi/postgres/
session-tokens as *evaluated alternatives*; neither profile mutates upstream
truth (pinned by test).

## 5. Admissibility results

Gates A1–A9 (§8), no compensating scores:

| Gate | A | B |
|---|---|---|
| A1 requirement lineage | pass | pass |
| A2 ISR lineage | pass | pass |
| A3 mandatory capabilities | pass | pass |
| A4 mandatory security | pass | pass |
| A5 explicit constraints | pass | pass |
| A6 conflict freedom (anon-sharing absent) | pass | pass |
| A7 no forbidden dependency | pass | pass |
| A8 deterministic evaluation | pass | pass |
| A9 upstream immutable | pass | pass |

Admissible: 2. Rejected: 0.

## 6. Selection policy (`vs1-selection-v1`)

Hard gates: A1–A7 + A9 must all pass (else `admissible=false`, unranked).
Soft scoring (fixed weights): coverage 0.4, security 0.3, simplicity 0.2
(`1 − complexity/max`), risk 0.1 (`1 − ordinal/max`), all scales [0,1],
rounded to 6 decimals. Tie-break: total desc → risk asc → complexity asc →
candidate_id asc. Full tie after all breakers → fail closed
(`selected=None`, reason recorded).

## 7. Scoring model

Defined in `score_candidate` and §6 above. Missing values: coverage/security
metrics degrade to 0.0 by construction (absent coverage entries simply do not
count); a candidate missing mandatory entries already fails hard gates and is
never scored. Equal scores resolve through the deterministic tie-break chain.

## 8. Candidate ranking

| Rank | Candidate | Total | Coverage | Security | Simplicity | Risk |
|---|---|---|---|---|---|---|
| 1 | vs1-candidate-a | 0.883333 | 1.0 | 1.0 | 0.666667 | 0.5 |
| 2 | vs1-candidate-b | 0.7 | 1.0 | 1.0 | 0.0 | 0.0 |

## 9. Selected candidate

**SELECTED: `vs1-candidate-a`** — score 0.883333, rank
`[vs1-candidate-a, vs1-candidate-b]`, policy `vs1-selection-v1`.
Rationale: identical coverage/security, strictly better simplicity (1 vs 5
complexity units) and risk (1 vs 2); deterministic on every tie-breaker.
Requirement refs: 12 covered IDs. ISR refs: 8 capabilities, 3 services, 3
APIs, 3 models, 2 policies. Provenance: upstream hashes + builder/policy/
schema versions (see §2).

## 10. Full requirement lineage

Every covered requirement ID resolves in the frozen VS-D01 graph (pinned by
test): 8 MUST functional, assign/membership/durability SHOULD, credential
safety, isolation, both constraints. Deferred `req-anon-sharing` is absent
from both candidates (correct: deferred requirements do not enter selection).

## 11. Full ISR lineage

Every covered ISR ID resolves in the frozen VS-D02 revision (pinned by test):
8 capabilities, 3 services, 3 APIs, 3 models, 2 policies. Builder raises
`ValueError` on any unknown requirement/ISR ID (fail-closed; pinned).

## 12. Provenance

Each candidate embeds: VS-D01/VS-D02 builder identities, requirement-graph
sha256, ISR content hash, builder/schema/policy versions. Decision rationale
and provenance travel with the selection record (§9). No timestamps influence
the decision path.

## 13. Determinism evidence

- Repeated generation: identical (`test_repeated_generation_identical`).
- Repeated scoring/ranking/selection: identical, including under reversed
  input order (`test_ranking_deterministic`, `test_same_inputs_same_winner`).
- Full tie (identical profiles+ids) fails closed with TIE reason; empty set
  yields NONE — never an arbitrary pick.

## 14. Explicit STOP boundary

```
REQUIREMENTS → ISR → CANDIDATE SET → SELECTION DECISION
                                                  X ← STOP HERE
                                            IMPLEMENTATION (not authorized)
```

No backend code, deployment manifests, deployments, runtime observation,
telemetry, evolution, compiler/ISR/requirements/certification modifications,
migrations, frontends, intake, or infrastructure were created or touched.
`vertical_slice/candidates.py` imports only stdlib + frozen upstream builders
(pinned by AST test). VS-D04 is NOT authorized.

---

*End of VS-D03 artifact. Report follows separately per §21 (uncommitted).*
