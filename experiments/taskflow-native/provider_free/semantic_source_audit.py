"""Audit canonical TaskFlow inputs against mandatory semantic fields.

This is an evidence inventory, not a resolver. Presence of text never turns a
field into a resolved semantic value or authorizes generation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PROBLEM_PATH = ROOT / "experiments" / "taskflow-native" / "PROBLEM.md"
ACCEPTANCE_PATH = ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json"

# Each entry states what the supplied snapshot actually says and what remains
# underspecified. Do not promote these records to SemanticResolution values.
FIELD_AUDIT: tuple[dict[str, Any], ...] = (
    {"field_path": "identity.registration_and_authentication", "source": "PROBLEM.md", "needles": ["Users must be able to register and authenticate"], "coverage": "PARTIAL", "reason": "Registration and authentication are required, but identity fields, credential policy, recovery and authentication protocol are unspecified."},
    {"field_path": "authorization.workspace_membership_scope", "source": "PROBLEM.md", "needles": ["A user can access only workspaces to which they belong.", "Cross-workspace reads and writes fail closed."], "coverage": "SPECIFIED_INVARIANT", "reason": "Membership isolation and fail-closed cross-workspace behavior are explicit; enforcement points and error contract remain unspecified."},
    {"field_path": "authorization.owner_manager_member_permissions", "source": "PROBLEM.md", "needles": ["owner/manager/member roles", "Owner-only operations cannot be performed by ordinary members."], "coverage": "PARTIAL", "reason": "Role names and an owner-only constraint exist, but the complete permission matrix and manager permissions are not defined."},
    {"field_path": "data.workspace_project_task_relationships", "source": "PROBLEM.md", "needles": ["create workspaces", "create projects, create and assign tasks", "Task/project/workspace relationships remain consistent."], "coverage": "PARTIAL", "reason": "Entities and consistency are required, but cardinalities, deletion rules and complete relationship constraints are not defined."},
    {"field_path": "data.comments_and_activity_history", "source": "PROBLEM.md", "needles": ["comment on tasks, inspect activity history"], "coverage": "PARTIAL", "reason": "Comments and activity history are required, but schemas, visibility, retention and event coverage are unspecified."},
    {"field_path": "tasks.assignment_status_priority_and_due_dates", "source": "PROBLEM.md", "needles": ["create and assign tasks, change task status and priority, set due dates"], "coverage": "PARTIAL", "reason": "These task capabilities are named, but status/priority enumerations, transition rules and due-date semantics are unspecified."},
    {"field_path": "tasks.archive_visibility", "source": "PROBLEM.md", "needles": ["Archived records do not reappear in normal active queries."], "coverage": "SPECIFIED_INVARIANT", "reason": "The active-query invariant is explicit; archive/restore operations and exceptions are unspecified."},
    {"field_path": "sessions.revocation_and_expiry", "source": "PROBLEM.md", "needles": ["Authentication sessions can be invalidated and invalidated sessions cannot continue to authorize requests."], "coverage": "PARTIAL", "reason": "Revocation must immediately prevent authorization, but session lifetime, expiry policy and revocation mechanism are unspecified."},
    {"field_path": "api.request_response_and_error_contracts", "source": "PROBLEM.md", "needles": ["Cross-workspace reads and writes fail closed.", "Expose health/readiness information."], "coverage": "NOT_SPECIFIED", "reason": "Behavioral constraints are present, but no endpoint inventory, payload schemas, status codes or error envelope is specified."},
    {"field_path": "frontend.required_interactions_and_state_transitions", "source": "PROBLEM.md", "needles": ["search/filter tasks", "view a useful workspace dashboard"], "coverage": "PARTIAL", "reason": "Major user-facing capabilities are named, but screens, interaction details, loading/error states and navigation are unspecified."},
    {"field_path": "persistence.consistency_and_atomic_mutations", "source": "PROBLEM.md", "needles": ["Task/project/workspace relationships remain consistent."], "coverage": "PARTIAL", "reason": "Consistency is required, but transaction boundaries, isolation level and concurrency conflict behavior are unspecified."},
    {"field_path": "operations.idempotency_and_unique_effect_identity", "source": "PROBLEM.md", "needles": ["Requests explicitly declared idempotent do not create duplicate effects.", "Security-sensitive mutations have a unique auditable effect identity."], "coverage": "SPECIFIED_INVARIANT", "reason": "No duplicate effects for declared idempotent requests and unique auditable identities are explicit; key format, retention and retry contract remain unspecified."},
    {"field_path": "operations.health_readiness_and_audit_evidence", "source": "PROBLEM.md", "needles": ["Expose health/readiness information.", "Produce structured operational/audit evidence."], "coverage": "PARTIAL", "reason": "Health/readiness and structured evidence are required, but probe semantics, fields, sinks and retention are unspecified."},
    {"field_path": "deployment.reproducible_execution_environment", "source": "PROBLEM.md", "needles": ["Be deployable in a reproducible environment."], "coverage": "NOT_SPECIFIED", "reason": "Reproducibility is required, but deployment target, packaging, configuration and infrastructure constraints are intentionally unspecified."},
    {"field_path": "verification.required_capability_and_negative_case_mapping", "source": "ACCEPTANCE.json", "needles": ["required_capabilities", "negative_cases", "certification_rule"], "coverage": "PARTIAL", "reason": "Required capability names, negative cases and a no-theatrical-certification rule are listed, but field-level mapping to tests/evidence and detailed pass criteria are not fully defined."},
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_source_audit() -> dict[str, Any]:
    problem_bytes = PROBLEM_PATH.read_bytes()
    acceptance_bytes = ACCEPTANCE_PATH.read_bytes()
    problem = problem_bytes.decode("utf-8")
    acceptance_text = acceptance_bytes.decode("utf-8")
    entries = []
    for spec in FIELD_AUDIT:
        source_text = problem if spec["source"] == "PROBLEM.md" else acceptance_text
        found = [needle for needle in spec["needles"] if needle in source_text]
        entries.append({
            "field_path": spec["field_path"],
            "source_file": spec["source"],
            "matched_source_fragments": found,
            "required_source_fragments": list(spec["needles"]),
            "source_fragments_present": len(found) == len(spec["needles"]),
            "coverage": spec["coverage"],
            "reason": spec["reason"],
            "resolved": False,
        })
    return {
        "schema": "tiannara.taskflow.semantic-source-audit.v1",
        "audit_kind": "source_coverage_inventory_not_resolution",
        "problem_sha256": _sha256(problem_bytes),
        "acceptance_file_sha256": _sha256(acceptance_bytes),
        "entries": entries,
        "summary": {
            "mandatory_fields": len(entries),
            "source_fragments_complete": sum(item["source_fragments_present"] for item in entries),
            "specified_invariant": sum(item["coverage"] == "SPECIFIED_INVARIANT" for item in entries),
            "partial": sum(item["coverage"] == "PARTIAL" for item in entries),
            "not_specified": sum(item["coverage"] == "NOT_SPECIFIED" for item in entries),
            "resolved_fields": 0,
        },
        "generation_authorized": False,
        "certification_authorized": False,
        "limitation": "Textual source coverage is not trusted semantic resolution and does not authorize SystemModel construction, backend selection, generation, or certification.",
    }


def main() -> int:
    print(json.dumps(build_source_audit(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
