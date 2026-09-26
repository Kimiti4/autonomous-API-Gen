# Bandit-Fix Verification Track (EV-A01-001 follow-up)

- **Canonical audited state (unchanged):** `6e1aa1a` (PR #1 head, 20 commits, `evolution/second-backend-lowering-hardening`).
- **Verified at:** the same exact commit and PR state — no later collaborator push exists (`git ls-remote` tip = `6e1aa1a`; PR `updatedAt` = comment time only).
- **Method:** READ-ONLY. Independent re-run of the CI Bandit invocation, parent-tree comparison, GitHub Actions job conclusions, and the collaborator's PR comment. **EV-A02 findings are NOT retroactively altered by this track.**
- **Taxonomy/confidence:** same registers as EV-A01 (`IMPLEMENTED_*` / `CONFIRMED`).

---

## 1. Exact commit / PR state

| Fact | Value | Confidence |
|---|---|---|
| PR #1 head | `6e1aa1acf96d4f619d5331ff9d1056a7c4e46034` | CONFIRMED |
| Head commit subject | `fix: suppress Bandit false positive in Go SQL template` | CONFIRMED |
| Head commit time | 2026-09-22T14:48:39Z | CONFIRMED |
| Commits on PR | 20 | CONFIRMED |
| Diff vs parent | **1 file, +1/−1** — `autonomous-api/app/engine/backends.py` only | CONFIRMED |
| Changed line (old) | `db, err := sql.Open("sqlite", dsn)` | CONFIRMED |
| Changed line (new) | `db, err := sql.Open("sqlite", dsn) // # nosec B608` | CONFIRMED |
| Proven alternate fix | PR comment `#issuecomment-5779014985` (2026-09-22T15:12:57Z, module-level SQL constants + strip `// # nosec` from artifact) — **not applied to any commit** | CONFIRMED |
| Remote main | `1f26e42` (still lacks `7b593d6` ancestry; unrelated to this fix) | CONFIRMED |

## 2. Does the fix clear the Bandit finding?

**NO — the finding remains live. Verdict: FIX INEFFECTIVE.**

### 2.1 CI (authoritative gate)

| Run | Head | Job | Conclusion |
|---|---|---|---|
| `35742917271` (`autonomous-api CI/CD`, PR) | `6e1aa1a` | **`security-scan`** | **`failure`** |
| same run | `6e1aa1a` | `lint` | `success` |
| same run | `6e1aa1a` | `test (3.12)` | `failure` (separate EV-A01-002 track) |
| same run | `6e1aa1a` | `test (3.11)` / `test (3.13)` | `cancelled` (fail-fast) |

CI invocation (`.github/workflows/ci-cd.yml:115`): `bandit -ll -r app/ -f json -o bandit-report.json`.

### 2.2 Local reproduction (exact CI flags)

Environment: system Python 3.14.0, Bandit **1.9.4** (same major as collaborator comment), scan root `autonomous-api/app` (the CI `working-directory: autonomous-api` equivalent of `app/`).

| Tree | Command result |
|---|---|
| **HEAD `6e1aa1a`** (with `// # nosec B608`) | **exit 1**; Medium: **1**; finding **B608** at `app/engine/backends.py:192` (f-string start: `return f'''package main`); `Total lines skipped (#nosec): **0**`; `specifically disabled: **0**` |
| **Parent `6e1aa1a^`** (pre-fix, same file only) | B608 at line **192** — identical finding |

So the pushed change does not reduce, relocate, or suppress the Bandit result under the CI gate.

### 2.3 Why the `// # nosec B608` form cannot work here

1. Bandit attributes B608 to the **multi-line f-string start line** (`backends.py:192`), not to the physical line inside the Go template body where the comment sits (`:207`).
2. Bandit's `# nosec` matcher only honors directives on the **reported Python source line**. A `// # nosec` **inside** the string body is opaque to it (`nosec` counters stay 0).
3. Putting a Python `# nosec` on line 192 would become **literal content** of the generated Go file (the line is inside `f'''…'''`), which is why the collaborator comment rejects inline suppression and hoists SQL to module-level constants instead.
4. Side effect of the pushed form (CONFIRMED by source read): the text `// # nosec B608` is **part of the template that is written into every generated `main.go`** — a Python-lint directive leaking into the artifact. That is an artifact-hygiene regression, not a security control.

## 3. Relationship to EV-A02 (explicit non-retroactivity)

**The fix does not change any EV-A02 security implication. It only attempts (and fails) to close the single Bandit B608 scanner finding tracked as EV-A01-001.**

| Question | Answer | Confidence |
|---|---|---|
| Does `6e1aa1a` alter EV-A02-001…012 classifications? | **No.** Those findings concern static-evidence certification, promotion identity binding, stale materialization, provenance, path traversal, Go fail-open default credentials, scoring contract lies, build gates, Go runtime absence, dependency drift, publish identity — none of which is the B608 line. | CONFIRMED |
| Does it change EV-A02's FAIL status / trust-chain conclusion? | **No.** STATUS remains **FAIL** on the same three joints (static evidence, promotion binding, Go stub). | CONFIRMED |
| Was B608 itself an EV-A02 security finding? | **No.** EV-A02 never registered B608. The query text in the template is **parameterized** (`?` placeholders; `db.Query`/`db.Exec` with bound args) — Bandit's MEDIUM hit is a **scanner false positive on Go source embedded in a Python f-string**, as the head commit message itself states. | CONFIRMED |
| Does the nosec text in the template affect EV-A02 determinism (E1/E2)? | Byte-determinism is same-code ⇒ same-bytes; still holds at `6e1aa1a`. Cross-version artifact bytes differ by the one comment line (hygiene only). | CONFIRMED / bounded |
| EV-A02 two-state note (`docs/EV-A02-artifact-correctness.md` §header) | Remains accurate: canonical state `6e1aa1a` still carries the `// # nosec B608` template form; the *effective* remediation (module-level constants) is still NOT incorporated. **No edit required, and none made.** | CONFIRMED |

**Security-implication delta for EV-A02: ZERO.**  
**Security-implication delta for EV-A01-001: ZERO positive** — gate still red; fix status moves from `UNIMPLEMENTED` → `ATTEMPTED_INEFFECTIVE` (register row may be updated only by a future EV-A01 revision, not by this note rewriting history).

## 4. Register delta (this track only)

| ID | Finding | Taxonomy | Conf | State |
|---|---|---|---|---|
| **BANDIT-V-001** | Head commit `6e1aa1a` changes exactly one line to add `// # nosec B608` inside the Go template f-string | change `IMPLEMENTED_REAL` (content) | CONFIRMED | — |
| **BANDIT-V-002** | CI `security-scan` on run `35742917271` @ `6e1aa1a` = **failure** | gate `IMPLEMENTED_REAL`; remediation `INEFFECTIVE` | CONFIRMED | **OPEN** |
| **BANDIT-V-003** | Local `bandit -ll` @ `6e1aa1a` exits 1; B608 @ `backends.py:192`; `#nosec` skip counters = 0 | remediation `INEFFECTIVE` | CONFIRMED | **OPEN** |
| **BANDIT-V-004** | Comment-proven fix (module-level `_SQL_*` constants, bandit exit 0, artifact without nosec text) **never committed** | fix `UNIMPLEMENTED` @ remote | CONFIRMED | **OPEN** (collaborator) |
| **BANDIT-V-005** | Pushed form embeds `// # nosec B608` into generated Go source (template body) | artifact hygiene `PARTIAL` | CONFIRMED | **OPEN** (hygiene; not an EV-A02 reclassification) |
| **BANDIT-V-006** | EV-A02 security implications unchanged by this remediation attempt | non-impact statement | CONFIRMED | closed (no action) |

EV-A01-001 remains the CI-merge blocker of record; this track does not close it.

## 5. What would close EV-A01-001 (unchanged criteria)

1. Apply the comment shape (or any equivalent) so `bandit -ll -r app/` exits **0** with **no MEDIUM/HIGH** findings on a clean tree.
2. CI job **`security-scan`** on the PR head = **`success`**.
3. Generated `main.go` (or equivalent artifact) contains **no** `nosec` / lint-suppression text.
4. Re-verify independently (this track's commands in §7) before flipping EV-A01-001 from OPEN.

Out of scope here (still EV-A01-002): non-hermetic `tests/engine/test_evolution_fail_closed.py` reds on fresh CI.

## 6. Verdict

| Item | Result |
|---|---|
| Exact state verified | **`6e1aa1a` = PR #1 head** |
| Collaborator fix present at that state | **Yes, but only the ineffective `// # nosec` one-liner** |
| Bandit finding closed? | **No** (CI failure + local exit 1 + nosec counters 0) |
| Proven fix landed? | **No** (comment-only) |
| EV-A02 findings altered? | **No — explicitly not, and not required** |
| EV-A02 security implications changed? | **No — zero delta** |
| Nature of change | **Attempt to silence a specific Bandit false positive; fails to silence it; no effect on artifact trust-chain security** |

**Overall: REMEDIATION NOT VERIFIED. EV-A01-001 stays OPEN. EV-A02 stays FAIL with unchanged findings.**

## 7. Verification appendix (reproducible)

```bash
# state
gh pr view 1 --repo Kimiti4/autonomous-API-Gen --json headRefOid,state,updatedAt,commits
git show 6e1aa1a --stat -p -- autonomous-api/app/engine/backends.py

# CI job conclusions
gh api repos/Kimiti4/autonomous-API-Gen/actions/runs/35742917271/jobs \
  --jq '.jobs[] | [.name, (.conclusion // .status)] | @tsv'
# expect: security-scan  failure

# local gate (from autonomous-api/, mirrors ci-cd.yml:115)
bandit -ll -r app/ -f json -o bandit-report.json
# expect: exit 1; B608 backends.py:192; #nosec skipped = 0

# proven-but-unapplied fix
gh api repos/Kimiti4/autonomous-API-Gen/issues/comments/5779014985 --jq .body
```

Artifacts (ephemeral, outside repo):  
`C:\Users\user\AppData\Local\Temp\opencode\bandit-head.json`, `bandit-pre.json`.
