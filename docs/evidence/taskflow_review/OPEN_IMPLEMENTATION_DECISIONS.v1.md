# TaskFlow Open Implementation Decisions v1

**Status:** OPEN — requires explicit reviewer resolution before the affected semantics can be frozen for generation.  
**Scope:** Only details not fixed by the canonical problem, acceptance suite, or Groups 1–14 chat-approved records.  
**Authority:** This docket proposes no silent defaults. A selected value must be added to the canonical decision record/ledger, traced into typed semantics, and tested.  
**Machine-readable register:** `docs/evidence/taskflow_review/OPEN_IMPLEMENTATION_DECISIONS.v1.json`.
**Generation:** NOT AUTHORIZED.

## Decision register

| ID | Area | Unresolved question | Why it blocks implementation qualification | Required resolution |
|---|---|---|---|---|
| OID-001 | Session lifetime | What exact absolute session lifetime and idle timeout apply? What min/max bounds may configuration use? | Group 7 requires both values and bounded configuration but intentionally supplies no numbers. | Approve durations, units, and permitted configuration bounds. |
| OID-002 | Role/action matrix | Which exact project and task fields may Members edit, and which operations are Owner-only, Manager-allowed, or Member-allowed? | The role policy names broad capabilities, but field-level actions must be enforced by the backend, not inferred by the UI. | Approve a complete operation × role × resource-state allow/deny matrix. |
| OID-003 | Delete versus archive | May Members permanently delete projects/tasks, or only archive them? Can Managers permanently delete individual projects/tasks? | Existing decisions clearly restrict permanent workspace deletion to Owners, but do not fully define all project/task deletion boundaries. | Approve delete/archive permissions per role and resource type; define confirmation and audit requirements. |
| OID-004 | Workspace deletion with dependants | Is Owner workspace deletion blocked while other members or records exist, or does it remove/cascade data? If cascade is allowed, what retention/legal/audit constraints apply? | “Owner-only deletion” does not determine destructive cascade semantics. Guessing risks irreversible data loss or orphaned records. | Approve preconditions, cascade/retention behavior, confirmation, and recovery expectations. |
| OID-005 | Membership removal dependencies | What happens if a user is the last Owner, owns projects, or is assigned open tasks when removal is requested? Which transfers/reassignments are mandatory first? | Existing rules prohibit invalid ownership/assignment states but do not specify all resolution workflows. | Approve preconditions and atomic transfer/reassignment policy for each dependency. |
| OID-006 | MFA recovery | Which recovery process is permitted when a user loses their passkey/TOTP device? Are recovery codes or administrator-assisted recovery allowed, and what re-authentication/audit steps apply? | MFA is mandatory; recovery must prevent account takeover, but exact recovery proof and lockout behavior are not specified. | Approve recovery methods, proof requirements, rate limits, notifications, and session invalidation behavior. |
| OID-007 | API pagination and versioning | What default/max page size, cursor/offset contract, stable ordering, and API versioning/compatibility policy apply? | Pagination and versioning are required but the exact interoperable contract is not frozen. | Approve request/response schema, limits, ordering, and compatibility rules. |
| OID-008 | Idempotency contract | What key retention period and reuse/conflict policy apply? Which mutation endpoints declare idempotency, and how is the request fingerprint canonicalized? | Exactly-once effect behavior cannot be implemented consistently without scope, retention, and conflict semantics. | Approve endpoint inventory, key scope, retention, payload mismatch response, and replay authorization checks. |
| OID-009 | Audit retention and access | What retention duration applies to activity/audit/security events, and which roles may inspect sensitive security events? What deletion/export rules apply? | Append-only evidence and narrower access for sensitive events are required, but retention/access details are not fully specified. | Approve event classes, retention, access matrix, export/deletion policy, and tamper-evidence requirements. |
| OID-010 | Comment deletion | Can an author delete their own comment, or only edit it? Can Owner/Manager moderation permanently remove the comment body while retaining a separate audit event? | Group 4 requires moderation and no retention of deleted comment text, but the full author-delete policy is not fully explicit. | Approve author/moderator delete rights and the exact retained audit metadata. |
| OID-011 | Date/time semantics | Are due dates calendar dates in a workspace timezone or instants with timezone offsets? What timezone governs display, filtering, and date-only deadlines? | “Timezone-aware timestamps normalized consistently” does not fully determine user-visible due-date semantics. | Approve the canonical data type, workspace/user timezone rule, DST handling, and API serialization. |
| OID-012 | Conflict responses | What API status/error code should represent stale concurrent updates, idempotency-key payload conflicts, and illegal state transitions? | Atomicity and deterministic error contracts require stable, testable conflict semantics. | Approve the machine codes/status mapping and retryability classification. |

## Freeze protocol

For each OID:
1. Record the explicit reviewer answer without paraphrasing away constraints.
2. Update the corresponding original decision record or create a versioned amendment; preserve the prior record and provenance.
3. Regenerate the normalized ledger and update the matrix's source hashes if canonical sources change.
4. Bind each resolved value into a typed semantic field and document its native consumer.
5. Add positive and negative tests for the exact boundary.
6. Keep unresolved values as BLOCKED; do not substitute compiler heuristics, framework defaults, or assumed industry conventions.

## Current disposition

- Open implementation decisions: **12**
- Typed semantic carrier/consumer proof: **BLOCKED**
- Trusted reviewer envelope: **BLOCKED**
- Compiler pair qualification: **BLOCKED**
- TaskFlow generation: **NOT AUTHORIZED / NOT RUN**
- Certification: **NOT CERTIFIED**
