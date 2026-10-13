"""Regression tests for exact-source authorization policy projection."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tiannara.domain.models.reviewed_authorization_policy import ReviewedAuthorizationPolicy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/evidence/taskflow_review/group_2_workspace_authorization.kimityr.json"


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def test_group_2_policy_parses_with_source_binding_and_open_decisions_preserved():
    raw = SOURCE.read_bytes()
    policy = ReviewedAuthorizationPolicy.from_source_bytes(raw, source_record_sha=_blob_sha(raw))

    assert policy.reviewer_id == "Kimityr"
    assert policy.generation_authorized is False
    assert policy.cryptographic_signature_present is False
    assert policy.decisions.workspace_isolation.cross_workspace_resources_and_assignees == "Reject regardless of role."
    assert policy.decisions.permanent_workspace_deletion.authorized_role == "owner_only"
    assert len(policy.unresolved_operational_details) == 4
    assert len(policy.canonical_sha256) == 64


def test_source_bytes_cannot_be_changed_while_reusing_original_git_blob_sha():
    raw = SOURCE.read_bytes()
    changed = json.loads(raw)
    changed["decisions"]["workspace_isolation"]["foreign_resource_details"] = "May disclose"
    changed_raw = json.dumps(changed, indent=2).encode("utf-8")

    with pytest.raises(ValueError, match="Git blob SHA does not match"):
        ReviewedAuthorizationPolicy.from_source_bytes(
            changed_raw, source_record_sha=_blob_sha(raw)
        )


def test_missing_policy_section_is_rejected():
    raw = SOURCE.read_bytes()
    changed = json.loads(raw)
    del changed["decisions"]["membership"]
    changed_raw = json.dumps(changed).encode("utf-8")

    with pytest.raises(ValidationError):
        ReviewedAuthorizationPolicy.from_source_bytes(
            changed_raw, source_record_sha=_blob_sha(changed_raw)
        )


def test_owner_only_deletion_safeguards_cannot_be_weakened():
    raw = SOURCE.read_bytes()
    changed = json.loads(raw)
    changed["decisions"]["permanent_workspace_deletion"]["requirements"].remove("audit evidence")
    changed_raw = json.dumps(changed).encode("utf-8")

    with pytest.raises(ValidationError, match="all three reviewed safeguards"):
        ReviewedAuthorizationPolicy.from_source_bytes(
            changed_raw, source_record_sha=_blob_sha(changed_raw)
        )
