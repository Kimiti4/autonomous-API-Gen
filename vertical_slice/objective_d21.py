"""VS-D21 — evolution objective definition & cycle-opening gate.

Determines whether an explicit, constitutionally grounded objective exists
that lawfully opens a new evolutionary cycle. Governance ONLY: validates
objectives, never invents them. Missing/empty objective → HOLD (a lawful
outcome, not a failure). Malformed objective → fail closed. No candidate
generation, selection, implementation, deployment, observation,
optimization, production change, commit, or push. No ISR mutation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

OBJECTIVE_CONTRACT = "vs1-objective-d21"
D20_PATH = "vertical_slice/post_decision_d20_evidence.json"
D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"

VALID_SOURCES: tuple[str, ...] = (
    "requirement_delta",
    "new_requirement_set",
    "observation_trigger",
    "explicit_authorization",
)

# Sources that must never ground an objective (D21 §3).
FORBIDDEN_SOURCES: tuple[str, ...] = (
    "test_failures",
    "absence_of_work",
    "pipeline_position",
    "desire_to_continue",
    "implementation_differences",
    "unknowns_alone",
    "performance_assumptions",
    "architectural_curiosity",
)

REQUIRED_FIELDS: tuple[str, ...] = (
    "objective_id",
    "objective_type",
    "objective_statement",
    "source",
    "source_reference",
    "affected_obligations",
    "scope",
    "constraints",
    "success_criteria",
    "security_constraints",
    "authorization_reference",
)

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_D19_DECISION = "NO_ACTION"


class ObjectiveError(Exception):
    """Fail-closed objective failure (malformed/forbidden objective)."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _load_json(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as exc:
        raise ObjectiveError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise ObjectiveError(f"input malformed: {path}")
    return record


def verify_upstream() -> dict[str, str]:
    """D20 closed-hold state + D19/D12/ISR pins (read-only)."""
    d20 = _load_json(D20_PATH)
    d19 = _load_json(D19_PATH)
    d12 = _load_json(D12_PATH)
    if d20.get("contract") != "vs1-post-decision-d20":
        raise ObjectiveError("D20 contract drift")
    if d20.get("next_state", {}).get("pipeline_state") != \
            "WAITING_FOR_EXPLICIT_AUTHORIZATION":
        raise ObjectiveError("D20 hold-state drift")
    if d19.get("decision") != EXPECTED_D19_DECISION:
        raise ObjectiveError("D19 drift")
    if d12.get("decision") != "NO_CHANGE":
        raise ObjectiveError("D12 drift")
    from vertical_slice import implementation as IMPL
    if IMPL.frozen_input_identity()["vs-d02-isr-content-hash"] != EXPECTED_ISR:
        raise ObjectiveError("ISR drift")
    return {
        "d20_closure": d20["closure_hash"],
        "d19_decision": d19["decision"],
        "d19_hash": d19["decision_hash"],
        "d12_decision": "NO_CHANGE",
        "isr_hash": EXPECTED_ISR,
    }


def validate_objective(candidate: Any) -> dict[str, Any]:
    """Validate an explicit objective. Returns its canonical form.

    Raises ObjectiveError for malformed objectives or forbidden sources.
    Missing/empty input is NOT an error here — define_cycle() maps it to
    HOLD. Use validate_objective only for actually supplied material.
    """
    if not isinstance(candidate, dict):
        raise ObjectiveError("objective malformed: not a record")
    for field in REQUIRED_FIELDS:
        if field not in candidate or candidate[field] in (None, "", [], {}):
            raise ObjectiveError(f"objective missing: {field}")
    source = candidate["source"]
    if source in FORBIDDEN_SOURCES:
        raise ObjectiveError(f"forbidden objective source: {source}")
    if source not in VALID_SOURCES:
        raise ObjectiveError(f"untraceable objective source: {source}")
    scope = candidate["scope"]
    if not isinstance(scope, dict) or not scope.get("in_scope") \
            or not scope.get("out_of_scope"):
        raise ObjectiveError("objective scope not explicit")
    criteria = candidate["success_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ObjectiveError("success criteria missing")
    for criterion in criteria:
        if not isinstance(criterion, dict) or not criterion.get("criterion") \
                or not criterion.get("measurement"):
            raise ObjectiveError("success criterion not measurable")
    if not candidate.get("authorization_reference"):
        raise ObjectiveError("objective without authorization lineage")
    canonical = {field: candidate[field] for field in REQUIRED_FIELDS}
    canonical["objective_hash"] = _sha(_canon(
        {k: v for k, v in canonical.items() if k != "objective_hash"}))
    return canonical


def operation_in_scope(canonical: dict[str, Any], operation: str) -> bool:
    """True iff the operation falls inside the objective's declared scope."""
    scope = canonical.get("scope", {})
    in_scope = scope.get("in_scope", [])
    out_scope = scope.get("out_of_scope", [])
    if operation in out_scope:
        return False
    return operation in in_scope


def define_cycle(supplied: Any = None) -> dict[str, Any]:
    """Gate entry point. No supplied objective → HOLD (lawful, not failure).
    A supplied objective is validated; only a valid one opens the cycle —
    and even then, nothing is generated, selected, or implemented here.
    """
    upstream = verify_upstream()
    if supplied is None or supplied == {}:
        return {
            "status": "HOLD",
            "cycle_opened": False,
            "objective_present": False,
            "upstream": upstream,
        }
    canonical = validate_objective(supplied)
    return {
        "status": "PASS",
        "cycle_opened": True,
        "objective_present": True,
        "objective": canonical,
        "upstream": upstream,
    }


def assemble_evidence(supplied: Any, generated_at: str) -> dict[str, Any]:
    """Canonical D21 evidence. HOLD when no objective; PASS only with a
    validated objective. Either way: nothing downstream is performed."""
    outcome = define_cycle(supplied)
    record: dict[str, Any] = {
        "contract": OBJECTIVE_CONTRACT,
        "status": outcome["status"],
        "cycle_opened": outcome["cycle_opened"],
        "objective_present": outcome["objective_present"],
        "objective": outcome.get("objective"),
        "upstream": outcome["upstream"],
        "d12_decision": "NO_CHANGE",
        "real_authorization": 0,
        "objective_authorization": "NONE",
        "production_authorization": False,
        "isr_hash": EXPECTED_ISR,
        "isr_unchanged": True,
        "cycle": {
            "cycle_opened": outcome["cycle_opened"],
            "candidate_generation": "NOT_PERFORMED",
            "architecture_selection": "NOT_PERFORMED",
            "implementation": "NOT_PERFORMED",
            "deployment": "NOT_PERFORMED",
            "observation": "NOT_PERFORMED",
            "optimization": "NOT_PERFORMED",
        },
        "next": ("WAITING_FOR_EXPLICIT_AUTHORIZATION"
                 if outcome["status"] == "HOLD"
                 else "D22_ONLY_IF_AUTHORIZED"),
        "provenance": {
            "contract": OBJECTIVE_CONTRACT,
            "d20_closure": outcome["upstream"]["d20_closure"],
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["objective_evidence_hash"] = _sha(_canon(check))
    return record
