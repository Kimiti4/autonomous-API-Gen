"""Strict typed projection of the approved-in-chat TaskFlow Group 2 policy.

This parses reviewed policy; it is not a trusted attestation or runtime
authorization engine. Unresolved operational decisions remain unresolved.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _exact_items(actual: tuple[str, ...], expected: set[str], label: str) -> None:
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError(f"{label} must preserve the complete reviewed item set")


class OwnerPolicy(_StrictModel):
    scope: Literal["Full administrative control within the owner's own workspace"]
    allowed: tuple[str, ...]
    constraints: tuple[str, ...]

    @model_validator(mode="after")
    def preserve_reviewed_owner_rules(self) -> "OwnerPolicy":
        _exact_items(self.allowed, {
            "workspace settings", "membership and role administration", "projects",
            "tasks", "archive and restore",
            "permanent workspace deletion subject to confirmation and audit",
        }, "owner.allowed")
        _exact_items(self.constraints, {
            "cross-workspace isolation remains mandatory",
            "integrity safeguards remain mandatory",
        }, "owner.constraints")
        return self


class ManagerPolicy(_StrictModel):
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]

    @model_validator(mode="after")
    def preserve_reviewed_manager_rules(self) -> "ManagerPolicy":
        _exact_items(self.allowed, {
            "manage projects and tasks within own workspace",
            "manage assignments, comments, and archive/restore",
            "invite ordinary members", "remove ordinary members",
        }, "manager.allowed")
        _exact_items(self.forbidden, {
            "promote, demote, remove, or change roles of owners or managers",
            "transfer ownership", "permanently delete workspace",
        }, "manager.forbidden")
        return self


class MemberPolicy(_StrictModel):
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]

    @model_validator(mode="after")
    def preserve_reviewed_member_rules(self) -> "MemberPolicy":
        _exact_items(self.allowed, {
            "create projects within own workspace", "manage permitted project content",
            "view and create workspace tasks", "update permitted task fields and assignments",
            "comment",
        }, "member.allowed")
        _exact_items(self.forbidden, {
            "change workspace settings", "manage membership", "change roles",
        }, "member.forbidden")
        return self


class MembershipPolicy(_StrictModel):
    manager_boundary: Literal["no_privileged_roles"]
    manager_invite_remove: Literal["ordinary members only"]
    owner_controls_privileged_role_changes: Literal[True]
    membership_changes_must_be_authorized_and_auditable: Literal[True]
    affected_sessions_and_cached_permissions_must_follow_defined_revocation_rules: Literal[True]


class WorkspaceIsolationPolicy(_StrictModel):
    rule: Literal[
        "All backend reads and writes must be scoped to authenticated, authorized workspace membership."
    ]
    cross_workspace_resources_and_assignees: Literal["Reject regardless of role."]
    foreign_resource_details: Literal["Must not be disclosed in responses."]


class PermanentWorkspaceDeletionPolicy(_StrictModel):
    authorized_role: Literal["owner_only"]
    requirements: tuple[Literal["explicit confirmation", "ownership checks", "audit evidence"], ...]
    managers_and_members_forbidden: Literal[True]

    @model_validator(mode="after")
    def require_all_safeguards(self) -> "PermanentWorkspaceDeletionPolicy":
        if set(self.requirements) != {
            "explicit confirmation", "ownership checks", "audit evidence"
        } or len(self.requirements) != 3:
            raise ValueError("workspace deletion must retain all three reviewed safeguards")
        return self


class VerificationPolicy(_StrictModel):
    backend_enforcement_required: Literal[True]
    required_cases: tuple[str, ...]

    @model_validator(mode="after")
    def preserve_required_negative_cases(self) -> "VerificationPolicy":
        _exact_items(self.required_cases, {
            "cross-workspace reads", "cross-workspace writes",
            "unauthorized role changes", "member removal", "invalid task assignments",
            "workspace deletion without owner authority",
        }, "verification.required_cases")
        return self


class AuthorizationDecisions(_StrictModel):
    owner: OwnerPolicy
    manager: ManagerPolicy
    member: MemberPolicy
    membership: MembershipPolicy
    workspace_isolation: WorkspaceIsolationPolicy
    permanent_workspace_deletion: PermanentWorkspaceDeletionPolicy
    verification: VerificationPolicy


class ReviewedAuthorizationPolicy(_StrictModel):
    """Parsed policy tied to the source record's Git blob and canonical digest."""

    schema_version: Literal["tiannara.taskflow.reviewer-decision.chat-record.v1"]
    decision_group: Literal[
        "authorization.workspace_membership_scope+authorization.owner_manager_member_permissions"
    ]
    reviewer_id: str = Field(min_length=1)
    approval_status: Literal["APPROVED_IN_CHAT"]
    approval_source: str = Field(min_length=1)
    cryptographic_signature_present: Literal[False]
    trusted_hmac_envelope_present: Literal[False]
    generation_authorized: Literal[False]
    decisions: AuthorizationDecisions
    unresolved_operational_details: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def preserve_open_decisions_and_evidence_limits(self) -> "ReviewedAuthorizationPolicy":
        expected_unresolved = {
            "Exact editable project and task fields by role",
            "Whether members can delete projects/tasks or only archive them",
            "Whether workspace deletion is permitted while active members or data remain",
            "Session and cached-permission invalidation behavior after membership changes",
        }
        if set(self.unresolved_operational_details) != expected_unresolved or len(self.unresolved_operational_details) != len(expected_unresolved):
            raise ValueError("all four reviewed unresolved operational details must remain explicit")
        expected_limitations = {
            "This record documents chat approval only.",
            "It is not a cryptographic attestation or trusted evidence envelope.",
            "It does not authorize generation.",
            "Remaining semantic decisions and trusted-evidence requirements must be satisfied before generation.",
        }
        if set(self.limitations) != expected_limitations or len(self.limitations) != len(expected_limitations):
            raise ValueError("all reviewed source limitations must remain explicit")
        return self
    source_record_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_source_bytes(
        cls, source_bytes: bytes, *, source_record_sha: str
    ) -> "ReviewedAuthorizationPolicy":
        """Parse exact tracked bytes and verify their Git blob identity."""
        actual_blob_sha = hashlib.sha1(
            b"blob " + str(len(source_bytes)).encode("ascii") + b"\x00" + source_bytes
        ).hexdigest()
        if source_record_sha != actual_blob_sha:
            raise ValueError("authorization source record Git blob SHA does not match its bytes")
        try:
            record = json.loads(source_bytes)
            canonical = json.dumps(
                record, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("authorization source must be valid canonicalizable JSON") from exc
        payload = dict(record)
        payload["source_record_sha"] = source_record_sha
        payload["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
        return cls.model_validate(payload)
