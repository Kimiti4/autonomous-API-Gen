# VS-D31B — Observatory Visual / Interaction Constitution v1

**Gate:** VS-D31B (side gate of D31) · **Objective:** VS1-OBJ-001
**Mode:** ANALYTICAL / DESIGN-DEFINITION / NON-IMPLEMENTING
**Upstream:** D31 scope (CLOSED), D31A audit (ACCEPTED/CLOSED as UX baseline)
**Status:** BINDING on all future Observatory UI work. Non-authoritative over
backend semantics, ISR, evidence, or governance — this document constrains
presentation only. Amendable by gate decision only, never by implementation
convenience.

**Visual identity (one line):** clarity of authority + clarity of evidence +
clarity of uncertainty + safe action. Not a SaaS dashboard.

---

## 1. Information hierarchy (target)

```text
Authority → State → Evidence → Interpretation → Action
```

Every Observatory view MUST order information toward this hierarchy. Current
implementation (uniform Section grids) is COMPLIANT-BY-STRUCTURE but not
yet expressive of it; reordering is a later UX increment (deferred, AQ-005
gated), NOT D32. No view may place Action above Authority, or Interpretation
above Evidence.

## 2. Layout grammar

- Preserved: `Section` (titled panel) + `.grid` / `.grid-2` / `.grid-3`
  composition; sticky header; `main` content column. This grammar is FROZEN —
  future work extends it, never replaces it piecemeal.
- Required direction (later increment): persistent status bar —
  `CONNECTION / AUTHORITY / FRESHNESS / VERSION` — on every view. No view may
  imply liveness without showing connection and freshness together.
- DISPLAY zones and CONTROL zones MUST be visually distinct constructs (see §9).
  Sharing identical `Section` styling for both is deprecated as of this
  constitution (migration: later increment).

## 3. Navigation model

- Preserved: flat, honest, ten-link header nav. Labels MUST name the destination
  domain truthfully.
- Required corrections (later increment, non-blocking): `Audit`→ destination is
  `/provenance` — relabel to `Provenance` or `Provenance & Audit`; add sign-in
  state/entry to nav; add Evolution/Evidence indexes (currently reachable only
  via search links); `.app-nav` MUST wrap (no overflow).
- No navigation entry may imply authority it does not carry (e.g., no
  `Authorize` link that leads to a request form without qualifier).

## 4. Epistemic state vocabulary (binding)

Display vocabulary (exact lowercase labels; text MUST always render):

```text
observed · inferred · unknown · contradiction        (backend EpistemicStatus)
not_measured · missing · not_applicable · recorded   (projection states)
unverified                                           (provenance/claim qualifier)
stale · freshness-unknown                            (once signals exist; §14)
```

Rules: INFERRED ≠ OBSERVED (distinct badge, never same color). UNVERIFIED must
be labelable on any carried claim (C-09). Projection states MUST have badge
mapping (they currently fall through to unstyled StatusPill — gap, later
increment). No other epistemic synonyms may be introduced without gate review.

## 5. Status taxonomy (binding)

`StatusPill` remains the generic status renderer; `EpistemicBadge` remains the
typed epistemic renderer — separation PRESERVED. Completeness is REQUIRED:

- Every status string the backend can emit MUST have a pill class. Unmapped
  statuses MUST render neutral gray (`unknown` treatment) — NEVER green, NEVER
  red by default. Silent unstyled fallthrough is FORBIDDEN after the later
  increment implements this section (current fallthrough documented as gap).
- `connected`/`disconnected` (stream) REQUIRE encoding — the most glanceable
  live indicator MUST NOT be the least styled element.
- Severity REQUIRE distinct encoding — `error`/`fatal` MUST NOT look like `info`.

## 6. Semantic color tokens (binding)

Frozen base (`globals.css` `:root`): background/panel/border/text/muted/accent +
`--green #2fbf71 · --yellow #e5b93d · --red #e05252 · --blue #5aa9ff ·
--purple #b48cff`. Semantics, collision-resolved:

```text
green   verified / certified / healthy / pass / operational        (NOT merely-seen)
blue    observation channel / inferred / safe-mode / informational
amber   qualified / pending / attention / in-progress (moved off blue)
red     failure / violation / blocked / contradiction
purple  evolution / candidate / transformation                    (token adopted; was dead)
gray    unknown / unavailable / not-measured / unmapped-default
```

Resolutions (later increment implements; D32 implements NONE of them):
blue triple-collision ends by moving `in-progress`→amber; green collision ends
by F-003 (genome `observed`→gray badge); purple adopted for evolution/candidate
surfaces. Color is ALWAYS secondary to the text label (§4). No page-local
palette may override these tokens.

## 7. Typography hierarchy (preserved)

Inter/Segoe UI for prose; JetBrains Mono for values/ids/hashes; 20px view
title / 15px section / 14px body / 13px meta / 11px uppercase-tracked pills.
FROZEN as baseline. Values that are identifiers MUST stay monospace (copyability
is an audit property).

## 8. Component rules

- `Section`: titled, single responsibility; CONTROL sections use zone styling (§9).
- `KeyValue`: facts only — MUST NOT be used for authority levels, command
  affordances, or mixed action/display rows (current `current_authority` flat
  dump migrates in later increment).
- `EventTimeline`: every item carries timestamp + epistemic badge + category/
  type/subject/severity meta; invalid timestamps render raw (never blank).
- `notice` (gray): information. `error` (red): failures with cause text.
  `empty` (muted): absence — MUST read as absence, never as health.
- One component, one instance per view unless the view's subject genuinely
  repeats (the double `ServerWorkspacePanel` is the anti-pattern reference).

## 9. Authority/control visual boundary (binding)

- CONTROL zones: labeled `Human Controls` or `Requested Action`; MUST carry the
  request-disclaimer pattern ("forwarded to the governance boundary and may
  still be rejected"); MUST show session identity + clearance; MUST show
  rejection/failure outcomes in-zone (never silent).
- Command verbs: REQUEST-language only. Display labels MUST carry the
  `request_` prefix semantics even where backend ids differ (`stop_runtime` →
  displayed as request; raw ids MUST NOT appear as button/select labels).
- No-authority and proxy-disabled states keep their current explicit notices
  (PRESERVED verbatim in spirit).
- UI filtering (clearance-gated action lists) MUST NEVER be presented as the
  security boundary — it is convenience; enforcement lives server-side.

## 10. Accessibility baseline (binding minimum)

Preserved: semantic header/nav/main; native button/input/select/label with
associated labels; no div-onClick. Required (later increment unless noted):
`aria-live` (polite) on live-update regions — screen readers MUST receive what
sighted users get from SSE/poll; skip link; visible `:focus` treatment; no
information by color alone (already satisfied — keep satisfying it); contrast
floor WCAG AA for text (unassessed — assessment required before any palette
change); `prefers-reduced-motion` respected (§12).

## 11. Responsive policy

Operator-desktop-first, DECLARED (not apologized for). Kept: 1000px grid
collapse; sticky header. Required: nav wrap; KV-row narrow behavior (stack or
scroll, never clip); no new breakpoints without gate note. No mobile target;
tablet/landscape must not lose CONTROL-zone distinction.

## 12. Animation/motion policy

No motion observed; policy: motion MUST NEVER imply liveness, freshness, health,
or progress without a backing data signal. No spinners-as-health. No
auto-animating attention-seekers on failure states (color + label carry it).
`prefers-reduced-motion` disables all non-essential motion once any exists.

## 13. Error/empty/unknown-state rules (binding)

- Errors: `.error` block with cause text; NEVER an empty view, NEVER a zeroed
  dashboard. Fetch failure MUST name the failed source.
- Empty: `.empty` with absence language ("No events", "No active gates" →
  extended forms MUST disambiguate *none exist* vs *none known*).
- Unknown: gray badge + `unknown` text; MUST NOT borrow green/red/amber.
- Invalid input (GAP-003 class): 400-style inline reason adjacent to the input,
  never a 500-styled crash block for user-correctable input.

## 14. Data freshness rules (binding direction; signals pending)

- No view may display a freshness implication it cannot evidence. `connected`
  (transport open) ≠ `fresh` (data current) ≠ `healthy` (source well) — three
  distinct claims, three distinct indicators once signals exist.
- Until staleness signals exist: views fed by SSE/poll MUST be capable of
  showing `freshness-unknown` (capability placeholder, not fake data).
- Silent source switching (SSE-items vs dashboard-timeline fallback) MUST carry
  a source label once the timeline contract is touched (CHANGE item, later
  increment).

## 15. Forbidden UI patterns (binding law)

```text
UNKNOWN → green                    ABSENT → zero
UNAVAILABLE → healthy              INFERRED → observed styling
REQUEST → executed/confirmed       DISPLAY → authority
stale → current                    missing → empty success
unverified → certified             connected → healthy
unmapped status → silent unstyled  failure → empty view
action list → security boundary    color → sole carrier of meaning
```

Any implementation introducing a listed pattern FAILS its gate regardless of
other correctness. Exemptions: none; amendments: gate decision only.

---

## Adoption map

```text
ALREADY COMPLIANT (preserve; future UI contract tests): text-carries-meaning;
  empty/error labels; disclaimers + warnings; request-language; semantic
  controls/landmarks; single token file; severity-as-text (keep text, add encoding).
D32-CONSUMABLE (only): F-003 badge direction (green→gray) inside the scoped
  projection fix; audit-hookup placement context; duplicate-panel removal.
LATER UX INCREMENT (everything else): pill taxonomy completion; severity +
  connected encoding; blue/green collision resolution; purple adoption; zone
  distinction; nav corrections; status bar; aria-live/focus/skip; freshness
  capability; IA reorder (AQ-005-gated); heartbeat investigation follow-up.
```

## Revision rule

This constitution changes by gate decision with cited evidence. Implementation
gates (D32+) may NOT reinterpret it; UX increments implement it section by
section with per-section acceptance. Conflicts between this document and older
design docs resolve in favor of this document for all presentation questions.
