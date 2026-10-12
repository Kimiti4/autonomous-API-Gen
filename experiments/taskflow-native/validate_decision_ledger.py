#!/usr/bin/env python3
"""Fail-closed consistency checks for TaskFlow review decisions and coverage.

This validates record integrity and traceability only. It does not establish that
chat approvals are trusted attestations, that semantics reach compiler consumers,
or that the generated application is correct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("docs/evidence/taskflow_review/decision_ledger.v1.json")
MATRIX_PATH = Path("experiments/taskflow-native/decision_coverage_matrix.v1.json")
PROBLEM_PATH = Path("experiments/taskflow-native/PROBLEM.md")
ACCEPTANCE_PATH = Path("golden-projects/taskflow/ACCEPTANCE.json")

EXPECTED_SEMANTIC_IDS = {
    "identity.registration_and_authentication",
    "authorization.workspace_membership_scope",
    "authorization.owner_manager_member_permissions",
    "data.workspace_project_task_relationships",
    "data.comments_and_activity_history",
    "tasks.assignment_status_priority_and_due_dates",
    "tasks.archive_visibility",
    "sessions.revocation_and_expiry",
    "api.request_response_and_error_contracts",
    "frontend.required_interactions_and_state_transitions",
    "persistence.consistency_and_atomic_mutations",
    "operations.idempotency_and_unique_effect_identity",
    "operations.health_readiness_and_audit_evidence",
    "deployment.reproducible_execution_environment",
    "verification.required_capability_and_negative_case_mapping",
}


def _load(root: Path, relative_path: Path, errors: list[str]) -> Any | None:
    path = root / relative_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{relative_path}: cannot read valid JSON ({exc})")
        return None


def git_blob_sha(content: bytes) -> str:
    """Return the Git SHA-1 for a blob, including Git's object header."""
    header = b"blob " + str(len(content)).encode("ascii") + b"\\0"
    return hashlib.sha1(header + content).hexdigest()


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    ledger = _load(root, LEDGER_PATH, errors)
    matrix = _load(root, MATRIX_PATH, errors)
    acceptance = _load(root, ACCEPTANCE_PATH, errors)
    if not all(item is not None for item in (ledger, matrix, acceptance)):
        return errors

    # Bind the matrix to the exact canonical specification and acceptance bytes.
    for key, path in (("problem", PROBLEM_PATH), ("acceptance", ACCEPTANCE_PATH)):
        expected = matrix.get("canonical_sources", {}).get(key, {}).get("git_blob_sha")
        source_path = root / path
        try:
            actual = git_blob_sha(source_path.read_bytes())
        except OSError as exc:
            errors.append(f"{path}: cannot read canonical source ({exc})")
            continue
        if expected != actual:
            errors.append(f"{path}: Git blob SHA mismatch (matrix={expected!r}, actual={actual})")

    records = ledger.get("records")
    if not isinstance(records, list):
        errors.append("ledger.records must be an array")
        records = []
    if ledger.get("reviewer_decision_group_count") != 14 or len(records) != 14:
        errors.append("ledger must contain exactly 14 reviewer decision records")
    if ledger.get("semantic_group_count") != 15:
        errors.append("ledger semantic_group_count must be 15")

    seen_groups: list[int] = []
    seen_semantics: list[str] = []
    seen_sources: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("ledger record must be an object")
            continue
        group = record.get("group")
        if not isinstance(group, int) or isinstance(group, bool):
            errors.append(f"record has invalid group number: {group!r}")
        else:
            seen_groups.append(group)
        semantics = record.get("semantic_ids")
        if not isinstance(semantics, list) or not semantics or not all(
            isinstance(value, str) and value for value in semantics
        ):
            errors.append(f"group {group!r}: semantic_ids must be a non-empty string array")
        else:
            seen_semantics.extend(semantics)
        source = record.get("source_record")
        digest = record.get("source_git_blob_sha")
        if not isinstance(source, str) or not source or source.startswith("/") or ".." in Path(source).parts:
            errors.append(f"group {group!r}: invalid source_record path")
        elif source in seen_sources:
            errors.append(f"group {group!r}: duplicate source_record {source}")
        else:
            seen_sources.add(source)
            try:
                actual_source_sha = git_blob_sha((root / source).read_bytes())
            except OSError as exc:
                errors.append(f"{source}: cannot read source record ({exc})")
            else:
                if digest != actual_source_sha:
                    errors.append(
                        f"{source}: Git blob SHA mismatch (ledger={digest!r}, actual={actual_source_sha})"
                    )
        if record.get("reviewer_id") != ledger.get("reviewer_id"):
            errors.append(f"group {group!r}: reviewer_id differs from ledger reviewer")
        if record.get("cryptographic_signature_present") is not False:
            errors.append(f"group {group!r}: must not claim a cryptographic signature")
        if record.get("trusted_hmac_envelope_present") is not False:
            errors.append(f"group {group!r}: must not claim a trusted HMAC envelope")
        if record.get("generation_authorized") is not False:
            errors.append(f"group {group!r}: generation must remain unauthorized")
        if record.get("implementation_or_runtime_verified") is not False:
            errors.append(f"group {group!r}: chat record must not claim implementation/runtime verification")

    if sorted(seen_groups) != list(range(1, 15)):
        errors.append("ledger groups must be unique and cover exactly 1..14")
    if len(seen_semantics) != len(set(seen_semantics)):
        errors.append("ledger semantic IDs contain duplicates")
    if set(seen_semantics) != EXPECTED_SEMANTIC_IDS:
        errors.append(
            "ledger semantic coverage mismatch: "
            f"missing={sorted(EXPECTED_SEMANTIC_IDS - set(seen_semantics))}; "
            f"unexpected={sorted(set(seen_semantics) - EXPECTED_SEMANTIC_IDS)}"
        )
    policy = ledger.get("normalization_policy", {})
    for flag in (
        "original_records_modified",
        "chat_approval_is_cryptographic_attestation",
        "trusted_evidence_envelope_present",
        "generation_authorized",
        "implementation_or_runtime_verified",
    ):
        if policy.get(flag) is not False:
            errors.append(f"ledger normalization_policy.{flag} must be false")
    if policy.get("certification_status") != "NOT_CERTIFIED":
        errors.append("ledger certification_status must remain NOT_CERTIFIED")

    matrix_semantics = matrix.get("semantic_groups", [])
    matrix_ids = [item.get("id") for item in matrix_semantics if isinstance(item, dict)]
    if len(matrix_ids) != 15 or len(matrix_ids) != len(set(matrix_ids)):
        errors.append("matrix semantic_groups must contain 15 unique IDs")
    if set(matrix_ids) != EXPECTED_SEMANTIC_IDS:
        errors.append("matrix semantic_groups do not exactly match the canonical 15 semantic IDs")
    for item in matrix_semantics:
        if not isinstance(item, dict):
            continue
        if item.get("implementation_status") != "UNKNOWN":
            errors.append(f"semantic {item.get('id')}: implementation status must remain UNKNOWN")
        if item.get("test_status") != "NOT_RUN":
            errors.append(f"semantic {item.get('id')}: test status must remain NOT_RUN")
        if item.get("evidence_ref") is not None:
            errors.append(f"semantic {item.get('id')}: evidence_ref must remain null absent verified evidence")

    expected_capabilities = set(acceptance.get("required_capabilities", []))
    matrix_capabilities = {
        item.get("id") for item in matrix.get("required_capabilities", []) if isinstance(item, dict)
    }
    if matrix_capabilities != expected_capabilities:
        errors.append("matrix required capabilities do not match acceptance suite")
    expected_gates = set(acceptance.get("quality_gates", {}).keys())
    matrix_gates = {item.get("id") for item in matrix.get("quality_gates", []) if isinstance(item, dict)}
    if matrix_gates != expected_gates:
        errors.append("matrix quality gates do not match acceptance suite")
    expected_negative = set(acceptance.get("negative_cases", []))
    matrix_negative = {item.get("id") for item in matrix.get("negative_cases", []) if isinstance(item, dict)}
    if matrix_negative != expected_negative:
        errors.append("matrix negative cases do not match acceptance suite")

    if matrix.get("generation_authorized") is not False:
        errors.append("matrix generation_authorized must be false")
    if matrix.get("certified") is not False:
        errors.append("matrix certified must be false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="repository root (defaults to detected checkout root)")
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        print("TASKFLOW DECISION LEDGER VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("TASKFLOW DECISION LEDGER VALIDATION: PASS")
    print("Validated: source blob hashes, 14 unique records, 15 semantic IDs,")
    print("acceptance capability/gate/negative-case coverage, and fail-closed status flags.")
    print("Not validated: trusted attestation, semantic compiler consumption, application behavior, or certification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
