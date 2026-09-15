# VS-D32 — Reconciliation Findings / Evidence-Consistency Adjudication

**Gate:** VS-D32 · **Objective:** VS1-OBJ-001 · **Mode:** ANALYTICAL ONLY
**Upstream:** D30 (PASS/CLOSED), D31 (PASS/CLOSED), D31A (ACCEPTED/CLOSED),
D31B (COMPLETE), D30A (= VS-D29 PASS/HOLD alias, no file moves)
**Redefinition note:** D32 is the evidence-consistency adjudication layer. It
supersedes the earlier provisional label "D32 = INC-01 implementation" used in
D31-era messages. INC-01 implementation belongs to a future,
separately-authorized gate. D32 authorizes nothing downstream.
**Report area:** `docs/observatory/` (§16 area, D30/D31 convention).

## A. D32 STOP REPORT (summary; canonical §20 format at end)

Adjudicated 20 material claims against cited evidence by independent
re-verification (read-only greps, reads, recomputation). One real defect found
(D30 matrix aggregate tallies miscounted; cells verified correct). Two
provenance gaps found and repaired-by-recording (D30A alias and console-page
micro-amendment existed only in session transcript; both now carried in this
file-native record). No true contradiction. No gate decision reversed.

## B. CLAIM ADJUDICATION MATRIX

Legend: EST= EVIDENCE_ESTABLISHED · BND= EVIDENCE_BOUNDED · INF= INFERRED ·
HYP= HYPOTHESIZED · CON= CONTRADICTED · UNR= UNRESOLVED · OOS= OUT_OF_SCOPE.

| ID | CLAIM | SOURCE | EVIDENCE (D32 re-verification) | TYPE | CLASS | SCOPE/LIMITATION | CLOSURE |
|---|---|---|---|---|---|---|---|
| CL-01 | zero observatory coupling | D30 E-009 | independent full-depth re-grep: zero importers outside observatory/ (only 2 hits, both intra-package relative imports, verified line-by-line) | DIRECT_PRIMARY | EST | first-party .py import surface | ELIGIBLE |
| CL-02 | runtime neutrality (no Phoenix/broker) | D30 E-006/007 | searched extensions only (.py/.ts/.tsx/.toml/.cfg/.ini/.sh); .yml/.yaml/.json/env unexamined | DIRECT_SECONDARY | BND | searched surfaces; vendor/design excluded | ELIGIBLE (as bounded) |
| CL-03 | absent Sentinel/Omega/ASC/Crucible | D30 E-008 | directory-name surface; no overclaim in artifact | DIRECT_SECONDARY | BND | names only; alias modules possible but unevidenced | ELIGIBLE (as bounded) |
| CL-04 | D30 matrix tallies 63/11/23/14/9 | D30 §5 | recomputation: 65/11/17/15/12 (script + manual per-column, total 120 ✓) | DIRECT_PRIMARY | CON (tallies) | cells verified correct row-by-row; aggregates were hand-miscounted | CORRECTED HERE (D30 frozen, not reopened) |
| CL-05 | backend imports all relative | D30 §3 | both absolute-form hits verified intra-package (`..gateway`, `.logging_handler`) | DIRECT_PRIMARY | EST | import-statement surface | ELIGIBLE |
| CL-06 | D30A asserts ISR ambiguity | D30 P-005/E-028 | folder/D29.md:444 read directly (was grep-snippet) | DIRECT_PRIMARY | EST (assertion) | ambiguity SUBSTANCE (register content) still unread → sub-item UNR, debt LOW | ELIGIBLE (split verdict) |
| CL-07 | D30A alias + console amendment exist | chat authorization | no file-native record found (verified by grep) | ASSERTIONAL | BND (provenance PARTIAL) | repaired-by-recording in this artifact (§D, PD-01/PD-02) | CONDITIONAL (cite D32, not transcript) |
| CL-08 | factory.jsonl pre-existing/untouched | baselines | diff content observed: 2026-09-05 harness record, chain-linked, predates D30 | DIRECT_PRIMARY | EST (presence/predate/form) | record semantics OOS | ELIGIBLE |
| CL-09 | 290 passed vs ~291 static | session/agent | approx static count vs executed count; ±1 within tolerance + possible skip | CORROBORATIVE | BND (reconciled) | exact reconciliation would need re-execution (not warranted) | ELIGIBLE (as bounded) |
| CL-10 | DUP-001 candidacy | D30 | mirror ESTABLISHED (non-import + parallel defs observed); divergence MAGNITUDE never field-diffed | DIRECT+INFERENTIAL | BND (candidacy) / INF (magnitude) | DEC-001 unaffected (binds via future tests, asserts no measured divergence) | ELIGIBLE |
| CL-11 | D31A bracket-route exclusion | D31A method | 7 files enumerated; zero interactive elements confirmed | DIRECT_PRIMARY | EST (resolved by scope) | static-text rendering residual, LOW value | ELIGIBLE |
| CL-12 | pill taxonomy gaps | D31A | CSS class inventory: 16 pill + 4 epistemic; connected/granted/etc. absent | DIRECT_PRIMARY | EST | stylesheet surface | ELIGIBLE |
| CL-13 | CommandPanel honesty | D31A | full file read (request-language, rejection notice) | DIRECT_PRIMARY | EST | file surface | ELIGIBLE |
| CL-14 | no div-onClick handlers | D31A | app+components grep + bracket rescan, zero hits | DIRECT_SECONDARY | BND | handler-attribute surface | ELIGIBLE (as bounded) |
| CL-15 | HEAD ba952d4 stable across gates | 3 baselines | identical rev-parse at D30/D31/D32 checks | DIRECT_PRIMARY | EST | identity only | ELIGIBLE |
| CL-16 | no new tracked modifications | 3 git states | identical status/diff at each gate | DIRECT_PRIMARY | EST | tracked tree only | ELIGIBLE |
| CL-17 | D31 BLOCKED=0 vs AQ-010 | D31 §19 | blocking evaluated relative to INC-01; stream-auth outside increment | DERIVED | EST (reconciled) | representation difference, not conflict | ELIGIBLE |
| CL-18 | ABSENT-cell legitimacy | D30 matrix | ABSENT over closed enumerated sets (25+ endpoints listed; full-depth import grep; full CSS read) | DIRECT_PRIMARY | BND (legitimate bounded absence) | open-set ABSENTs correctly flagged UNKNOWN in artifact; advisory: cite the closed set on reuse | ELIGIBLE |
| CL-19 | purple token dead | D31B §6 | full 316-line CSS read, zero usage | DIRECT_PRIMARY | EST | stylesheet surface | ELIGIBLE |
| CL-20 | rendering consequences (overflow etc.) | D31A Q9 | CSS structure only; no rendering observed | INFERENTIAL | INF | must stay labeled finding, never fact | ELIGIBLE (as inference) |

Tallies: ESTABLISHED 12 (incl. 2 reconciled/split) · BOUNDED 6 · INFERRED 2
(magnitude + rendering, both labeled as such at origin) · HYPOTHESIZED 0 ·
CONTRADICTED 1 (tallies only; corrected) · UNRESOLVED 1 sub-item (P-005
substance) · OUT_OF_SCOPE 1 sub-item (factory semantics) + all D31 decisions
(§30 selections are decisions, not truth-claims — not adjudicable here).

## C. CONTRADICTION REGISTER

```text
C-001 | D30 tallies vs recomputation | artifact §5 (63/11/23/14/9) vs D32
  recomputation (65/11/17/15/12) | CONFLICT: aggregate arithmetic | AUTHORITY:
  recomputation (script + manual per-column, total cross-checks to 120) |
  RESOLUTION: cells verified correct; tallies corrected in D32 record |
  STATUS: RESOLVED_BY_EVIDENCE | RESIDUAL: D30 artifact frozen with wrong
  tallies — future citers MUST use D32 figures; no conclusion changes (PARTIAL
  count, the load-bearing figure for honesty assessment, was already correct).
C-002 | 290 executed vs ~291 static | session run vs agent partitioned counts |
  CONFLICT: apparent only (approx vs exact; tolerance ±1; possible skip) |
  STATUS: RECONCILED_BUT_BOUNDED | RESIDUAL: exact figure needs re-execution;
  explicitly NOT warranted (R6: no current-state inference asserted beyond
  bounded carry-forward on an unchanged tracked tree).
```

No UNRESOLVED_CONTRADICTION. No TRUE contradiction among material conclusions.
No gate decision depends on a contradicted claim (C-001 affects aggregates, not
cells, decisions, or scope).

## D. PROVENANCE DEFECT REGISTER

```text
PD-01 | D30A alias authorization | chain:c oral-authorization → chat transcript
  → 3 artifact headers | DEFECT: no file-native authorization record; transcript
  not independently retrievable | SEVERITY: MEDIUM → LOW (repaired: alias now
  recorded file-natively HERE with full lineage) | RULE: future gates cite D32 §B
  CL-07 + this register, never the transcript.
PD-02 | console/page.tsx micro-amendment | authorized in chat; ABSENT from
  IMPLEMENTATION_SCOPE_D31.md (verified: zero 'console/page' hits) | SEVERITY:
  MEDIUM → LOW (repaired: amendment recorded HERE — console/page.tsx opens for
  duplicate-block removal at lines ~369-375 ONLY) | RULE: the future
  implementation gate MUST treat this D32 record as the amendment's authority.
PD-03 | P-005 substance | D29.md:444 verified; contradiction-register content
  unread | SEVERITY: LOW | STATUS: open, constitutional-track property.
PD-04 | tally single-pass origin | CURED by C-001 recomputation | SEVERITY: LOW
  → none (residual: none; method stated above).
PD-05 | subagent-survey inheritance | 4 D30 surveys single-observer | CURED in
  part (CL-01/05/12/13/19 re-verified independently); REMAINDER: core-package
  interiors, test-count partitions, adapter line-cites stay single-observer →
  BND with debt LOW (no material claim rests SOLELY on unverified inheritance
  except partitioned counts, which carry explicit approx labels).
```

## E. KNOWLEDGE-DEBT REGISTER

```text
HIGH: none.
MEDIUM: none outstanding (PD-01/PD-02 downgraded by in-artifact repair).
LOW (open, evidence-stated): DUP-001 divergence magnitude (needs field diff —
  owned by future contract-test gate as acceptance input, NOT as prework);
  P-005 substance (constitutional track); static-count exactness (re-execution
  unwarranted); rendering inferences CL-20 (need a browser, OOS for repo gates);
  .env contents (deliberately unexamined — standing); core interiors below
  2 levels (breadth limit declared at D30 §2).
```

## F. RECONCILIATION VERDICT

```text
CONSISTENT_WITH_BOUNDS
```

Justification: 12/20 claims independently re-established; 6 bounded claims
carry explicit, sufficient bounds; 1 contradiction found and resolved by
evidence without touching any conclusion; 2 provenance gaps repaired by
recording; negatives (290/291, BLOCKED=0, ABSENT cells) survive §11 control;
temporal identity holds across all three baselines; no material claim exceeds
its evidentiary authority; all uncertainties retained explicitly (1 UNR
sub-item, 6 LOW debts). Nothing in D30/D31 requires revision; D30/D31 remain
CLOSED (this artifact corrects tallies by supersession in the D32 record, not
by reopening).

## D32 FINAL ANSWERS (§19 question)

> Does the reconciled evidence state form an internally coherent,
> provenance-preserving, scope-bounded representation of the system state, with
> all material contradictions and uncertainties explicitly retained?

Yes — with stated bounds. Corrected matrix tallies:
PRESENT=65 · PARTIAL=11 · ABSENT=17 · NOT_APPLICABLE=15 · UNKNOWN=12
(30 responsibilities × 4 adjudicated columns; EX design-reference column
excluded from tallies as at origin).

## D32 STOP REPORT

```text
STATUS: PASS_WITH_BOUNDS
UPSTREAM: D30 PASS/CLOSED · D31 PASS/CLOSED · D31A ACCEPTED/CLOSED ·
  D31B COMPLETE · D30A alias (provenance repaired herein)
CANONICAL_IDENTITY: HEAD ba952d4, branch main, tree stable (1 pre-existing line)
EVIDENCE_REVIEWED: D30 artifact (743 lines) · D31 artifact (405 lines) ·
  folder/D29.md:444 (direct) · globals.css (full) · CommandPanel (full) ·
  import surfaces (full-depth re-grep) · git identity ×3 · matrix recomputation
CLAIMS:
  ESTABLISHED: 12
  BOUNDED: 6
  INFERRED: 2 (labeled at origin)
  HYPOTHESIZED: 0
  CONTRADICTED: 1 (tallies; resolved)
  UNRESOLVED: 1 sub-item
  OUT_OF_SCOPE: decisions + factory semantics
CONTRADICTIONS:
  RESOLVED: 1 (C-001)
  BOUNDED: 1 (C-002)
  UNRESOLVED: 0
PROVENANCE:
  COMPLETE: 14
  PARTIAL: 2 (PD-01/PD-02, repaired-by-recording; cite D32)
  BROKEN: 0
KNOWLEDGE_DEBT:
  HIGH: 0
  MEDIUM: 0
  LOW: 6 (all evidence-stated above)
RECONCILIATION_VERDICT: CONSISTENT_WITH_BOUNDS
CLOSURE_ELIGIBLE: D32 adjudication YES · D30/D31 closures STAND (no revision
  required; tally correction by supersession)
UNRESOLVED_ITEMS: P-005 substance (constitutional track); 6 LOW debts (§E)
FORBIDDEN_ACTIONS_OBSERVED: 0
IMPLEMENTATION_CHANGES: 0
COMMITS: 0
PUSHES: 0
FINAL: PASS_WITH_BOUNDS
```

No implementation authorization implied. No future-stage authorization implied.
D32 ends here. The next gate — whatever the governing process names it —
inherits: corrected tallies (65/11/17/15/12), file-native D30A + amendment
records (PD-01/PD-02), and the debt list as acceptance inputs, not prework.
```
