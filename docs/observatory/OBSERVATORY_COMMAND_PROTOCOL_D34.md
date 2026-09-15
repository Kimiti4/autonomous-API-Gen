# VS-D34 — Observatory Control / Command Protocol Definition

**Gate:** VS-D34 · **Objective:** VS1-OBJ-001 · **Mode:** ANALYTICAL + CONTRACT-DEFINING ONLY
**Upstream:** D30 PASS/CLOSED · D31 PASS/CLOSED · D31A ACCEPTED/CLOSED (consumed
via D31B/D33 chains + transcript note — no silent dependence) · D31B COMPLETE ·
D32 PASS_WITH_BOUNDS (65/11/17/15/12; P-005 UNRESOLVED; DEBT-01..06) ·
D33 PASS (22 invariants, binding).
**Baseline:** branch main, HEAD ba952d4, tree stable (1 pre-existing line).
**Ruling (opening):** Constitutional Council / CEL have zero first-party
evidence → explicitly UNKNOWN authorities (fail-closed); STOP reserved for
conflicting-evidence ambiguity, not for evidenced absence.
**Discipline:** CURRENT = evidenced in OBS-PY-BE/FE today · PROTOCOL = defined
requirement. Protocol exceeding current is classified per §32 (never presented
as existing fact). No implementation, no authority granted, P-005 preserved.

## Central invariant (§3)

```text
REQUEST ≠ AUTHORIZATION ≠ EXECUTION · OBSERVATION ≠ DECISION ≠ AUTHORIZATION ≠
EXECUTION ≠ CERTIFICATION ≠ DEPLOYMENT
```

## 1. Command taxonomy (§4)

| Class | Observatory | Authoritative subsystem | Notes |
|---|---|---|---|
| READ | MAY_REQUEST (reads served per B-001 posture) | provide | policy-defined auth |
| INSPECT | MAY_REQUEST | provide | same |
| TRACE | MAY_REQUEST | provide | same |
| COMPARE | MAY_REQUEST | provide | same |
| REQUEST | create (PROTOCOL object §2) | decide | auth + audit required |
| CONTROL | request (CURRENT: safe_mode_enable/disable, workspace role ops via governed service) | decide/execute | auth + audit required |
| MUTATE | request only | execute | executor for authoritative mutation: see §8 (no wired executor evidenced → requests queue as PENDING/UNKNOWN, never execute) |
| CERTIFY | display/request only | certification authority (registry evidenced) | auth + audit required |
| DEPLOY | display/request only | deployment authority (UNKNOWN — no authority service evidenced) | requests to DEPLOY fail closed until authority evidenced |

CURRENT actions evidence: request_authorization, request_evolution_definition,
request_implementation, request_runtime, safe_mode_enable/disable,
stop_runtime/restart_runtime (request-semantics, D31A display-label rule
applies), workspace role grant/revoke (observatory-local AUTHORIZED_MUTATION
under workspace governor — the ONLY existing mutation class, authority =
workspace policy + token).

## 2. Command object (§5; CURRENT fields marked *)

```text
command_id* (REQ-{sha256[:20]} form TODAY is correlation handle only — PROTOCOL:
  command_id = stable canonical id, never timestamp-derived), request_id*,
subject_id*, actor_id*, actor_role*, action*, target*, requested_at*,
source* (=observatory), authorization_context*, preconditions*,
payload* (redacted at intake, CURRENT), correlation_id*, causation_id*,
idempotency_key (PROTOCOL-required for side-effect-capable; CURRENT: absent —
  GAP-class debt, see §6), schema_version (PROTOCOL-required; CURRENT: absent —
  versioning deferred AQ-009, contract tests pin behavior meanwhile).
```

Per-field purpose/authority/required/validation/privacy: companion JSON
`fields[]`. Privacy law: NO secrets in any field (§13); secure references only.

## 3. Identity (§6), actor (§7), authorization (§8)

Five independent lifecycles, independently traceable: command_id (canonical
request) → authorization decision id → execution_id → result_id → audit_id.
Reuse across semantics FORBIDDEN. CURRENT REQ- form retained ONLY as
correlation handle (gateway doc), never as identity evidence.
ACTOR: actor_id · actor_type (HUMAN/AUTHORIZED_SERVICE/SYSTEM/AUTOMATION/
UNKNOWN) · role · clearance · session_reference · authority_context. UNKNOWN
actors acquire NOTHING (F-002 display convention `anonymous/observer` is
presentation-only, never authorization input). No credentials in the object.
AUTHORIZATION (evaluated SOLELY by authoritative subsystem): states AUTHORIZED/
DENIED/PENDING/UNKNOWN/INVALID with non-collapse law (DENIED≠UNKNOWN≠
AUTHORIZED; PENDING≠AUTHORIZED; INVALID≠DENIED). Unevaluable policy → FAIL
CLOSED. Decision record: policy · decision · reason · evidence · timestamp ·
authority_identity.

## 4. Preconditions, lifecycle, idempotency, replay (§9–§12)

PRECONDITIONS (declared per mutating/control request; failure blocks
execution): identity_valid · actor_authenticated · actor_authorized ·
target_exists · target_state_valid · required_evidence_present ·
required_confirmation_present (high-impact, §7) · required_gate_open ·
system_healthy · authority_version_current (§9). Each: id · description ·
authority · evaluation · failure_behavior.
LIFECYCLE: CREATED→VALIDATED→{AUTHORIZED|DENIED|PENDING|INVALID}→QUEUED→
EXECUTING→{SUCCEEDED|FAILED|CANCELLED}→AUDITED. Not all states mandatory per
command; legal/illegal tables §11. Timeout NEVER implies non-execution without
authoritative evidence (idempotency law).
IDEMPOTENCY: idempotency_key REQUIRED for side-effect-capable commands.
Duplicates/retries/timeout-unknown/replay/partial-execution defined in JSON
`idempotency{}`: retry with same key returns recorded outcome; unknown result →
RESULT_UNKNOWN (never success); partial execution → FAILED + audit, re-entry
requires new authorization.
REPLAY PROTECTION: issued_at · expires_at · authority_version · state_version ·
nonce-or-equivalent (adopted where the existing security model supports; NO
invented cryptography — HMAC session pattern already evidenced in Next layer).
Stale/superseded/expired-session commands → STALE_REQUEST, fail closed.

## 5. Confirmation, authorities, result, errors (§13–§16)

HIGH-IMPACT confirmation binds: confirmation_required · context · actor ·
timestamp · scope — to THE request (command_id); generic clicks never count;
confirmation for A never authorizes B. CURRENT: no binding evidenced → PROTOCOL
requirement (DERIVED_FROM_SECURITY), implementation-gate acceptance item.
AUTHORITY SEPARATION (requester/validator/authorizer/executor/auditor):
Observatory=requester (+validator of LOCAL schema only) · ISR=requirements
authority · constitutional kernel=governance/authorization authorizer ·
evolution engine=evolution executor · certification registry=certification
authority · deployment authorizer UNKNOWN (fail closed) · owning services=runtime
executors · ledgers/audit-chains=auditors. Council/CEL=UNKNOWN (ruling above).
No component occupies all roles.
RESULT: result_id · request/execution ids · status (ACCEPTED/REJECTED/DENIED/
PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/UNKNOWN) · result · error ·
authority · evidence_refs · started/completed_at · schema_version. Submission
success ≠ execution success (CURRENT UI already honors: "request accepted").
ERRORS (13, each with retryable/authority/evidence/audit/safe_to_display in
JSON): INVALID_REQUEST · UNAUTHENTICATED · UNAUTHORIZED · PRECONDITION_FAILED ·
STALE_REQUEST · DUPLICATE_REQUEST · CONFLICT · UPSTREAM_UNAVAILABLE ·
EXECUTION_FAILED · RESULT_UNKNOWN · PROVENANCE_FAILURE · POLICY_UNAVAILABLE ·
INTERNAL_FAILURE. Safe-to-display subset enforced at the UI boundary (D31B §15
binding here).

## 6. Fail-closed, provenance, audit, boundary (§17–§20)

FAIL CLOSED on: authorization/identity/evidence/policy unavailable ·
malformed request · ambiguous authority/identity · safety-critical unknown
precondition · broken provenance · invalid state version. Banned substitutions:
unknown→allow · missing→default-allow · timeout→success · denied→retry-loop.
PROVENANCE LINKS (all five lifecycle records): request→actor→auth-context→
decision→execution→result→audit; broken links VISIBLE (I19). AUDIT OBJECT:
audit_id · request/actor/action/target · authorization_decision ·
execution_status · timestamp · authority · evidence_refs · previous/result
state refs; append-only, no destructive deletion (workspace_audit_chain +
command events are CURRENT conforming instances).
OBSERVATORY MAY: create requests · validate local schema · display
auth/execution/result/failure/provenance/audit states · cancel ONLY where
upstream explicitly permits. MAY NOT: self-authorize · override/rewrite policy,
authorization, evidence, audit · self-certify/deploy · mutate ISR,
constitutional authority, or evolution authorization (I01/I22 restated as
protocol law).

## 7. P-005, debts, security (§21–§23)

P-005 = UNRESOLVED (authority: constitutional track; substance: NOT_RECORDED
beyond D29.md:444 + D32 PD-03). Commands depending on P-005 carry
required_authority_state = UNKNOWN/UNRESOLVED and MUST NOT proceed silently;
UI MUST be capable of showing the qualifier (D33 §5 binding).
DEBT CONSEQUENCES: DEBT-01 (contract-test gate needs field diff — acceptance
input) · DEBT-02 = P-005 rule above · DEBT-03/04/05/06: no command depends
materially → no consequence beyond continued representation.
SECURITY: secret ban across payload/audit/evidence/results/state (GAP-006
constraint); references-not-material; S01–S15 conformance required of any
implementation gate (companion JSON maps each to protocol sections; no tests
executed here).

## 8. Versioning, concurrency, time, observability (§24–§28)

STALE_AUTHORITY: requests bind authority_version + state_version; material
change between authorization and execution → reauthorization required, no
silent reuse. Concurrency (semantic, no invented locking): state_version ·
conflict_detection · serialization_requirement · concurrency_policy declared
per mutating class; authority defines the mechanism later.
TIME: requested/validated/authorized/started/completed/audited_at kept
SEPARATE (F-001 law: absent timestamps render missing, never now — protocol
adopts D33 temporal rule over CURRENT backend default for COMMAND records;
backend event default unchanged/OUT_OF_SCOPE here). Ordering source declared
per authority; no invented global clock.
OBSERVABILITY (answerable per command): what/by-whom/against-what/under-which-
authority/authorized?/executed?/outcome/evidence. Telemetry ≠ authorization
evidence. VERSIONING: protocol_version · schema_version · authority_version ·
policy_version with explicit compat rules (newer clients never reinterpret
older schemas; older commands never gain authority).

## 9. Capability matrix (§29), state-machine (§30), invariants (§31)

Matrix (default; authoritative evidence overrides): READ/INSPECT/TRACE/COMPARE =
Observatory request + subsystem provide (policy auth, audit optional) ·
REQUEST = create/decide (auth+audit required) · CONTROL = request/decide-
execute (auth+audit) · MUTATE = request-only/unknown-executor (auth+audit;
fail-closed until executor evidenced) · CERTIFY/DEPLOY = display-or-request /
respective authority (auth+audit). KNOWN DEVIATION from default: none asserted
— matrix stands as PROTOCOL, not as existing-fact claim.
Legal transitions (§10 list) ACCEPTED; illegal list (created→succeeded,
created→executing, denied→succeeded, invalid→executing, failed→succeeded,
unknown→succeeded) REJECTED without explicit revalidation/retry edges.
D33 invariants applicable (I01/I04/I05/I06/I08/I09/I10/I14/I15/I16/I17/I18/I19/
I22): ALL HELD — mapping table in companion JSON; none weakened. I02/I03/I07/
I11/I12/I13/I20/I21 hold by construction (no evidence/identity/metric/tech
content redefined here).

## 10. Traceability, firewall, determinism (§32–§34)

Per-requirement classification in `OBSERVATORY_COMMAND_TRACEABILITY_D34.json`
(REQUIRED_BY_D33 / DERIVED_FROM_AUTHORITY / DERIVED_FROM_SECURITY / PROPOSED /
OUT_OF_SCOPE). PROPOSED items (explicit, non-authoritative): nonce-or-
equivalent where unsupported; confirmation UX shape; concurrency mechanisms.
TECH FIREWALL: no HTTP/REST/GraphQL/WS/NATS/Kafka/PG/Redis/FastAPI/Elixir/
React/queues/cloud prescribed — semantic behavior only. DETERMINISM:
canonicalization (field order, optionals, nulls, identifier normalization,
schema version, payload form) with timestamps EXCLUDED from command identity.

## 11. Mutation proof + STOP (§37)

```text
implementation changes = 0 · runtime mutation = 0 · command execution = 0 ·
deployment = 0 · commit = 0 · push = 0 · authority changes = 0 · ISR changes = 0 ·
D30-D33 changes = 0
artifacts: OBSERVATORY_COMMAND_PROTOCOL_D34.md (this file) +
  OBSERVATORY_COMMAND_PROTOCOL_D34.json + OBSERVATORY_COMMAND_TRACEABILITY_D34.json
```

## D34 STOP REPORT

```text
STATUS: PASS
UPSTREAM:
  D30: PASS/CLOSED
  D31: PASS/CLOSED
  D31A: ACCEPTED/CLOSED (via D31B/D33 chains + note)
  D31B: COMPLETE
  D32: PASS_WITH_BOUNDS (65/11/17/15/12; P-005 open; 6 LOW debts)
  D33: PASS (22 invariants; all applicable held)
AUTHORITY:
  request_authority: Observatory (intents) + operator session
  authorization_authority: constitutional kernel (governance); UNKNOWN where unevidenced (deployment, Council, CEL) — fail closed
  execution_authority: owning services (runtime); evolution engine (evolution); NONE wired for authoritative mutation via Observatory
  certification_authority: certification registry (evidenced)
  deployment_authority: UNKNOWN — DEPLOY requests fail closed
COMMAND_MODEL:
  command_identity: stable canonical id (CURRENT REQ- form = correlation handle only)
  request_identity: request_id + idempotency_key (side-effect-capable)
  execution_identity: execution_id (authority-issued)
  result_identity: result_id (submission ≠ execution)
  audit_identity: audit_id (append-only)
LIFECYCLE:
  states: CREATED/VALIDATED/AUTHORIZED/DENIED/PENDING/INVALID/QUEUED/EXECUTING/SUCCEEDED/FAILED/CANCELLED/AUDITED (+RESULT_UNKNOWN outcome qualifier)
  legal_transitions: §10 list accepted
  illegal_transitions: 6 rejected without revalidation edges
AUTHORIZATION:
  states: AUTHORIZED/DENIED/PENDING/UNKNOWN/INVALID (non-collapse law)
  fail_closed: 10 triggers (§6) + banned substitutions
  stale_authority: version-bound; reauthorization required
  replay_protection: issued/expires/authority+state versions/nonce-where-supported
  idempotency: key-required; timeout≠non-execution; partial→FAILED + re-auth
PROVENANCE: 5 lifecycle links required; breaks visible
SECURITY:
  authentication: session/token bounds preserved; UNKNOWN actors gain nothing
  authorization: subsystem-evaluated only
  secret_isolation: ban across all five records + representations
  escalation_protection: S11-S13 (cross-role/self-authorize/ISR-alter rejected)
HUMAN_CONTROL:
  confirmation: bound, per-request, high-impact (protocol requirement; CURRENT gap recorded, not repaired)
  Observatory_authority: request + local-schema validation + display
  upstream_authority: decides, executes, certifies, deploys
P-005:
  status: UNRESOLVED
  preserved: yes (qualifier-renderable; dependent commands blocked-silent-proof)
KNOWLEDGE_DEBT:
  DEBT-01: carried (contract-test acceptance input)
  DEBT-02: carried (= P-005 rule)
  DEBT-03: carried (no command impact)
  DEBT-04: carried (no command impact)
  DEBT-05: carried (secret-absence aids compliance)
  DEBT-06: carried (no command impact)
TRACEABILITY:
  D33_REQUIREMENTS_MAPPED: 100% (companion JSON; PROPOSED items labeled)
  D33_REQUIREMENTS_UNMAPPED: none
COMPLETENESS:
  material_requirements: §§4-35 all represented
  represented: 100%
  missing: none (BLOCKED not triggered)
IMPLEMENTATION:
  source_changes=0
  runtime_mutation=0
  command_execution=0
  deployment=0
COMMITS: 0
PUSHES: 0
ARTIFACTS:
  docs/observatory/OBSERVATORY_COMMAND_PROTOCOL_D34.md
  docs/observatory/OBSERVATORY_COMMAND_PROTOCOL_D34.json
  docs/observatory/OBSERVATORY_COMMAND_TRACEABILITY_D34.json
FINAL: PASS
```
