"""VS-D22 — objective intake & authorization gate.

Admits an explicitly supplied evolution objective into the pipeline iff it
is valid, traceable, bounded, and authorized — without inventing one.
Outcome states: HOLD (nothing supplied, or valid synthetic fixture which
proves mechanics only), PASS (real objective admitted; downstream stages
still NOT performed here), BLOCK (supplied objective violates the
constitution; fail closed). No candidate generation, selection,
implementation, deployment, observation, optimization, production change,
commit, or push. No ISR mutation.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

INTAKE_CONTRACT = "vs1-objective-intake-d22"
D20_PATH = "vertical_slice/post_decision_d20_evidence.json"
D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"

SOURCE_TYPES: tuple[str, ...] = (
    "REQUIREMENT_DELTA",
    "NEW_REQUIREMENT_SET",
    "EVIDENCE_TRIGGER",
    "GOVERNING_DECISION",
)

FORBIDDEN_SOURCES: tuple[str, ...] = (
    "PIPELINE_POSITION",
    "DESIRE_TO_CONTINUE",
    "ABSENCE_OF_WORK",
    "TEST_RESULTS_ALONE",
    "UNKNOWNS_ALONE",
    "LATENCY_ALONE",
    "ARCHITECTURE_CURIOSITY",
    "IMPLEMENTATION_PREFERENCE",
    "TECHNOLOGY_PREFERENCE",
    "CANDIDATE_AVAILABILITY",
    "OPTIMIZATION_WITHOUT_OBLIGATION",
    "MODEL_SUGGESTION_WITHOUT_AUTHORITY",
)

REQUIRED_FIELDS: tuple[str, ...] = (
    "objective_id",
    "objective_type",
    "objective_statement",
    "source_type",
    "source_reference",
    "affected_obligations",
    "scope",
    "constraints",
    "success_criteria",
    "security_constraints",
    "authorization_reference",
)

# Technology tokens that mark an implementation mandate (objective/solution
# confusion) unless an authoritative requirement explicitly mandates them.
TECH_TOKENS: tuple[str, ...] = (
    "redis", "kubernetes", "postgres", "mongodb", "docker", "kafka",
    "react", "vue", "angular",
)

ISR_MUTATION_TOKENS: tuple[str, ...] = (
    "rewrite isr", "mutate isr", "modify isr", "change isr",
    "isr rewrite", "isr mutation",
)

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"


class IntakeError(Exception):
    """Fail-closed intake failure (STATUS = BLOCK)."""


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
        raise IntakeError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise IntakeError(f"input malformed: {path}")
    return record


def known_identities() -> set[str]:
    """Traceable in-repo reference registry (read-only)."""
    ids = {
        EXPECTED_ISR, "vs1-d17-run-001", "vs1-decision-d19",
        "vs1-closure-d20", "vs1-deploy-v2", "vs1-impl-v2",
        "vs1-evolved-96fe2d29fd76",
    }
    for path in (D20_PATH, D19_PATH, D18_PATH, D17_PATH, D12_PATH):
        record = _load_json(path)
        for key in ("closure_hash", "decision_hash", "content_hash",
                    "normalized_hash", "d18_hash", "d17_hash",
                    "d18_interpretation_hash", "d17_observation_hash",
                    "evidence_hash", "selection_hash"):
            value = record.get(key)
            if isinstance(value, str) and value:
                ids.add(value)
    return ids


def reference_traceable(reference: Any) -> str:
    """Classify a source/authorization reference: KNOWN, EXTERNAL,
    SYNTHETIC, or UNTRACEABLE.

    Content-addressed in-repo records (REPO#<relpath>#sha256:<hex>) resolve
    to KNOWN only when the file bytes hash exactly to the stated digest.
    This is a strict general rule — any byte drift, missing file, or
    malformed digest is UNTRACEABLE — so persisted objective source
    records can ground admission without weakening traceability.
    """
    if not isinstance(reference, str) or not reference.strip():
        return "UNTRACEABLE"
    if reference in known_identities():
        return "KNOWN"
    match = re.fullmatch(
        r"REPO#([A-Za-z0-9_.\-/]+)#sha256:([0-9a-f]{64})", reference)
    if match:
        relpath, digest = match.group(1), match.group(2)
        if ".." in relpath or relpath.startswith("/"):
            return "UNTRACEABLE"
        try:
            with open(relpath, "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return "UNTRACEABLE"
        return "KNOWN" if actual == digest else "UNTRACEABLE"
    if reference.startswith("SYNTHETIC-TEST-ONLY:"):
        return "SYNTHETIC" if len(reference) > len("SYNTHETIC-TEST-ONLY:") else "UNTRACEABLE"
    if reference.startswith("EXT-"):
        parts = reference.split(":")
        if len(parts) >= 3 and all(p for p in parts):
            return "EXTERNAL"
        return "UNTRACEABLE"
    return "UNTRACEABLE"


def validate_objective(candidate: Any) -> dict[str, Any]:
    """Full validation. Returns canonical form with validation metadata.

    Raises IntakeError (BLOCK) on any constitutional violation. Synthetic
    fixtures validate mechanically but are marked non-admissible: a
    passing synthetic proves the validator works, never real authority.
    """
    if not isinstance(candidate, dict):
        raise IntakeError("objective malformed: not a record")
    for field in REQUIRED_FIELDS:
        if field not in candidate or candidate[field] in (None, "", [], {}):
            raise IntakeError(f"objective missing: {field}")
    source_type = candidate["source_type"]
    if source_type in FORBIDDEN_SOURCES:
        raise IntakeError(f"forbidden objective source: {source_type}")
    if source_type not in SOURCE_TYPES:
        raise IntakeError(f"invalid source type: {source_type}")
    source_trace = reference_traceable(candidate["source_reference"])
    if source_trace == "UNTRACEABLE":
        raise IntakeError("untraceable source reference")
    scope = candidate["scope"]
    if not isinstance(scope, dict) or not scope.get("in_scope") \
            or not scope.get("out_of_scope"):
        raise IntakeError("scope missing or unbounded")
    if not isinstance(scope["in_scope"], list) \
            or not isinstance(scope["out_of_scope"], list):
        raise IntakeError("scope malformed")
    criteria = candidate["success_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise IntakeError("success criteria missing")
    for criterion in criteria:
        if not isinstance(criterion, dict) or not criterion.get("criterion") \
                or not criterion.get("measurement"):
            raise IntakeError("success criterion not measurable")
    statement = str(candidate["objective_statement"]).lower()
    if candidate.get("requires_isr_change") is True or any(
            t in statement or t in _canon(scope).lower()
            for t in ISR_MUTATION_TOKENS):
        raise IntakeError("ISR_CHANGE_REQUIRED")
    if any(t in statement for t in TECH_TOKENS) \
            and "requirement mandates" not in statement:
        raise IntakeError("implementation masquerading as objective")
    authorization = candidate["authorization_reference"]
    if isinstance(authorization, dict):
        granted_by = str(authorization.get("granted_by", ""))
        auth_ref = authorization.get("reference", "")
        auth_scope = authorization.get("scope", [])
        if not granted_by or granted_by.strip().lower() in ("self", "model", ""):
            raise IntakeError("insufficient authorization: grantor")
        if reference_traceable(auth_ref) == "UNTRACEABLE":
            raise IntakeError("insufficient authorization: reference")
        if isinstance(auth_scope, list) and auth_scope and not set(
                auth_scope) & set(scope["in_scope"]):
            raise IntakeError("conflicting objective authority")
    elif reference_traceable(authorization) == "UNTRACEABLE":
        raise IntakeError("missing authorization")
    canonical = {field: candidate[field] for field in REQUIRED_FIELDS}
    canonical["synthetic"] = source_trace == "SYNTHETIC" or reference_traceable(
        candidate["authorization_reference"]
        if isinstance(candidate["authorization_reference"], str)
        else authorization.get("reference", "")) == "SYNTHETIC"
    canonical["objective_hash"] = _sha(_canon(
        {k: v for k, v in canonical.items() if k != "objective_hash"}))
    return canonical


def operation_in_scope(canonical: dict[str, Any], operation: str) -> bool:
    """Scope membership incl. silent-expansion detection (unknown op = out)."""
    scope = canonical.get("scope", {})
    if operation in scope.get("out_of_scope", []):
        return False
    return operation in scope.get("in_scope", [])


def verify_upstream() -> dict[str, str]:
    """D20 closed-hold + D19/D12/ISR pins + latest commit (read-only)."""
    d20 = _load_json(D20_PATH)
    d19 = _load_json(D19_PATH)
    d12 = _load_json(D12_PATH)
    if d20.get("contract") != "vs1-post-decision-d20":
        raise IntakeError("D20 contract drift")
    if d20.get("next_state", {}).get("pipeline_state") != \
            "WAITING_FOR_EXPLICIT_AUTHORIZATION":
        raise IntakeError("D20 hold-state drift")
    if d19.get("decision") != "NO_ACTION":
        raise IntakeError("D19 drift")
    if d12.get("decision") != "NO_CHANGE":
        raise IntakeError("D12 drift")
    from vertical_slice import implementation as IMPL
    if IMPL.frozen_input_identity()["vs-d02-isr-content-hash"] != EXPECTED_ISR:
        raise IntakeError("ISR drift")
    try:
        import subprocess as _sp
        commit = _sp.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception as exc:
        raise IntakeError(f"commit identity unavailable: {exc}")
    return {
        "d20_closure": d20["closure_hash"],
        "d19_decision": d19["decision"],
        "d19_hash": d19["decision_hash"],
        "d12_decision": "NO_CHANGE",
        "isr_hash": EXPECTED_ISR,
        "latest_commit": commit,
    }


def intake(supplied: Any = None) -> dict[str, Any]:
    """Gate entry point. HOLD when nothing supplied; PASS (admitted) only
    for a real, valid, authorized objective; synthetic-valid proves
    mechanics with admission closed."""
    upstream = verify_upstream()
    if supplied is None or supplied == {}:
        return {"status": "HOLD", "objective_present": False,
                "objective_admitted": False, "cycle_opened": False,
                "upstream": upstream}
    canonical = validate_objective(supplied)
    if canonical.get("synthetic"):
        return {"status": "HOLD", "objective_present": True,
                "objective_admitted": False, "cycle_opened": False,
                "objective": canonical, "synthetic_only": True,
                "upstream": upstream}
    return {"status": "PASS", "objective_present": True,
            "objective_admitted": True, "cycle_opened": True,
            "objective": canonical, "upstream": upstream}


def assemble_evidence(supplied: Any, generated_at: str) -> dict[str, Any]:
    """Canonical intake evidence. Admission opens the cycle only; every
    downstream stage remains NOT_PERFORMED here by construction."""
    outcome = intake(supplied)
    objective = outcome.get("objective")
    record: dict[str, Any] = {
        "contract": INTAKE_CONTRACT,
        "status": outcome["status"],
        "objective_present": outcome["objective_present"],
        "objective": objective,
        "objective_id": (objective or {}).get("objective_id"),
        "objective_type": (objective or {}).get("objective_type"),
        "objective_hash": (objective or {}).get("objective_hash"),
        "source": (objective or {}).get("source_type"),
        "source_reference": (objective or {}).get("source_reference"),
        "objective_authorization": ("SYNTHETIC_ONLY"
                                    if outcome.get("synthetic_only")
                                    else "ADMITTED" if outcome["status"] == "PASS"
                                    else "NONE"),
        "evolution_authorization": "NONE",
        "production_authorization": False,
        "deployment_authorization": "NONE",
        "push_authorization": "NONE",
        "isr_hash": EXPECTED_ISR,
        "isr_unchanged": True,
        "upstream": outcome["upstream"],
        "admission": {
            "objective_admitted": outcome["objective_admitted"],
            "cycle_opened": outcome["cycle_opened"],
        },
        "downstream": {
            "candidate_generation": "NOT_PERFORMED",
            "architecture_selection": "NOT_PERFORMED",
            "implementation": "NOT_PERFORMED",
            "deployment": "NOT_PERFORMED",
            "observation": "NOT_PERFORMED",
            "optimization": "NOT_PERFORMED",
        },
        "provenance": {
            "contract": INTAKE_CONTRACT,
            "d20_closure": outcome["upstream"]["d20_closure"],
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["intake_hash"] = _sha(_canon(check))
    return record
