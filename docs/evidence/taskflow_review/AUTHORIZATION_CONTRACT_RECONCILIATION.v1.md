# TaskFlow Authorization Contract Reconciliation — v1

Status: **BLOCKED — source/schema reconciliation only; not certification**

Branch: `review/taskflow-group-1-kimityr-clean`

## Scope

This audit compares the typed consumer and structural semantic contract with the actual Group 2 reviewer decision record and its normalized ledger projection. It does not authorize generation or promote chat approval into a trusted cryptographic attestation.

## Authoritative source located

- `docs/evidence/taskflow_review/group_2_workspace_authorization.kimityr.json`
- SHA-256-like Git blob identifier: `5a2f62095cad2e9c5016d54e1264f676b3b88685`
- Reviewer: `Kimityr`
- Status: `APPROVED_IN_CHAT`
- The record explicitly says no cryptographic signature or trusted HMAC envelope is present, and `generation_authorized=false`.

The decision establishes these substantive rules:

- Every backend read/write must be scoped to authenticated, authorized workspace membership.
- Cross-workspace resources and assignees are rejected regardless of role; foreign resource details are not disclosed.
- Owners have administrative authority within their own workspace.
- Managers may manage projects/tasks, assignments, comments, archive/restore, and ordinary-member invitations/removals, but may not change owner/manager roles, transfer ownership, or permanently delete a workspace.
- Members may create projects, manage permitted content, view/create tasks, update permitted task fields/assignments, and comment; they may not change workspace settings, manage membership, or change roles.
- Membership changes must be authorized and audited; session/cache invalidation must follow the still-to-be-defined revocation rules.
- Workspace deletion is owner-only, with explicit confirmation, ownership checks, and audit evidence.

The same record preserves unresolved details: exact project/task fields editable by each role; project/task delete versus archive permissions; deletion behavior with active members/data; and session/cache invalidation behavior. The normalized ledger repeats these limitations and confirms that generation is not authorized.

## Schema mismatch discovered

The current consumer contract in `tiannara/domain/models/taskflow_semantic_contract.py` expects:

- `authorization.workspace_membership_scope`: `scoped_resources`, `scoped_operations`, `cross_scope_denial`
- `authorization.owner_manager_member_permissions`: `roles`, `action_permission_matrix`

However, the approved Group 2 record expresses policy as `owner`, `manager`, `member`, `membership`, `workspace_isolation`, `permanent_workspace_deletion`, and `verification`. The current `AuthorizationSemanticObligations` preserves opaque dictionaries and hashes them, but it does not map or validate the approved record's role-specific rules.

Therefore, the existing typed object proves only that two non-empty JSON objects were passed through and bound to a graph digest. It does **not** prove that the reviewed role matrix has been represented without loss, that every approved constraint is enforceable, or that unresolved details have not been defaulted.

## Required next implementation boundary

1. Treat the Group 2 chat record as the policy source for reconciliation, but not as trusted cryptographic authorization.
2. Define a lossless typed policy projection that explicitly carries owner, manager, member, membership-change, workspace-isolation, and owner-only deletion constraints. Preserve the original source record reference/hash and graph binding.
3. Validate the projection against the source decision payload; reject omitted, weakened, or invented rules. Do not fill the four unresolved policy areas with defaults.
4. Keep operational generation blocked while unresolved details or trusted-evidence prerequisites remain open.
5. Add mutation/omission/weakening tests that compare the typed projection to the reviewed payload, then runtime acceptance tests once the implementation boundary is complete.
6. Do not update `SEMANTIC_CONSUMER_TRACE.v1.json` to PASS until the generated runtime demonstrably enforces the policy and the required evidence is attached.

## Verification state

- Source comparison: **performed** by reading the Group 2 record, normalized decision-ledger entry, structural contract, and typed authorization consumer.
- Unit tests: **NOT RUN** in this audit.
- Generated runtime tests: **NOT RUN**.
- CI: not assessed by this document.
- Generation/certification: **BLOCKED**.
