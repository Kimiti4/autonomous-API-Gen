"""Lossless typed projection of the approved-in-chat TaskFlow Group 2 policy.

This is a policy-source parser, not a trusted attestation or runtime authorization
engine. It rejects unknown fields and does not resolve open operational decisions.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OwnerPolicy(_StrictModel):
    scope: str = Field(min_length=1)
    allowed: tuple[str, ...]
    constraints: tuple[str, ...]


class ManagerPolicy(_StrictModel):
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]


class MemberPolicy(_StrictModel):
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]


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
        expected = {"explicit confirmation", "ownership checks", "audit evidence"}
        if set(self.requirements) != expected:
            raise ValueError("workspace deletion must retain all three reviewed safeguards")
        return self


class VerificationPolicy(_StrictModel):
    backend_enforcement_required: Literal[True]
    required_cases: tuple[str, ...]


class AuthorizationDecisions(_StrictModel):
    owner: OwnerPolicy
    manager: ManagerPolicy
    member: MemberPolicy
    membership: MembershipPolicy
    workspace_isolation: WorkspaceIsolationPolicy
    permanent_workspace_deletion: PermanentWorkspaceDeletionPolicy
    verification: VerificationPolicy


class ReviewedAuthorizationPolicy(_StrictModel):
    """Parsed policy tied to the source record's identity and exact canonical content."""

    schema_version: Literal["tiannara.taskflow.reviewer-decision.chat-record.v1"]
    decision_group: Literal[
        "authorization.workspace_membership_scope+authorization.owner_manager_member_permissions"
    ]
    reviewer_id: str = Field(min_length=1)
    approval_status: Literal["APPROVED_IN_CHAT"]
    cryptographic_signature_present: Literal[False]
    trusted_hmac_envelope_present: Literal[False]
    generation_authorized: Literal[False]
    decisions: AuthorizationDecisions
    unresolved_operational_details: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)
    source_record_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_record(cls, record: dict, *, source_record_sha: str) -> "ReviewedAuthorizationPolicy":
        """Parse an exact source record; the Git blob SHA binds source provenance."""
        try:
            canonical = json.dumps(
                record, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("authorization source must be canonical JSON data") from exc

        expected_git_blob_sha = hashlib.sha1(
            b"blob " + str(len(canonical_source_bytes(record))).encode("ascii") + b"\x00"
            + canonical_source_bytes(record)
        ).hexdigest()
        if source_record_sha != expected_git_blob_sha:
            raise ValueError("authorization source record Git blob SHA does not match its bytes")

        payload = dict(record)
        payload["source_record_sha"] = source_record_sha
        payload["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
        return cls.model_validate(payload)


def canonical_source_bytes(record: dict) -> bytes:
    """Git blob bytes use the source file bytes; JSON canonicalization is not equivalent."""
    # The API consumer must provide the original JSON serialization in the next
    # revision. This helper intentionally fails closed rather than guessing it.
    raise ValueError(
        "original source bytes are required to verify a Git blob SHA; "
        "use from_source_bytes instead"
    )
