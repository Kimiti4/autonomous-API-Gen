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


def _load():
    raw = SOURCE.read_bytes()
    return json.loads(raw)


def _parse_changed(record):
    raw = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    return ReviewedAuthorizationPolicy.from_source_bytes(
        raw, source_record_sha=_blob_sha(raw)
    )


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
    changed = _load()
    changed["decisions"]["workspace_isolation"]["foreign_resource_details"] = "May disclose"
    changed_raw = json.dumps(changed, indent=2).encode("utf-8")

    with pytest.raises(ValueError, match="Git blob SHA does not match"):
        ReviewedAuthorizationPolicy.from_source_bytes(
            changed_raw, source_record_sha=_blob_sha(raw)
        )


def test_missing_policy_section_is_rejected():
    changed = _load()
    del changed["decisions"]["membership"]

    with pytest.raises(ValidationError):
        _parse_changed(changed)


def test_owner_only_deletion_safeguards_cannot_be_weakened():
    changed = _load()
    changed["decisions"]["permanent_workspace_deletion"]["requirements"].remove("audit evidence")

    with pytest.raises(ValidationError, match="all three reviewed safeguards"):
        _parse_changed(changed)


def test_manager_permission_cannot_be_weakened_or_rewritten():
    changed = _load()
    changed["decisions"]["manager"]["forbidden"].remove("transfer ownership")

    with pytest.raises(ValidationError, match="manager.forbidden"):
        _parse_changed(changed)


def test_required_negative_case_cannot_be_omitted():
    changed = _load()
    changed["decisions"]["verification"]["required_cases"].remove("cross-workspace writes")

    with pytest.raises(ValidationError, match="verification.required_cases"):
        _parse_changed(changed)


def test_unresolved_operational_decisions_cannot_be_dropped():
    changed = _load()
    changed["unresolved_operational_details"].pop()

    with pytest.raises(ValidationError, match="all four reviewed unresolved"):
        _parse_changed(changed)


def test_trust_and_generation_limitations_cannot_be_dropped():
    changed = _load()
    changed["limitations"].remove("It does not authorize generation.")

    with pytest.raises(ValidationError, match="source limitations must remain explicit"):
        _parse_changed(changed)
