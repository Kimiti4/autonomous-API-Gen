"""VS-D29 — evidence-sufficiency and evolution decision gate.

Consumes the authoritative D28 interpretation and decides, per capability
and per evolution class, what the evidence supports. Governance/decision
ONLY: no implementation, repair, deployment, runtime execution,
production mutation, commit, or push. UNKNOWN stays UNKNOWN; the final
governance decision is PASS / HOLD (definition, not execution).

SC numbering follows the authoritative D22 record (not the illustrative
list in the D29 prompt prose): SC02-SC05/SC07/SC12-SC13 OBSERVED,
SC01/SC06/SC08-SC11 UNKNOWN, zero contradictions.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

DECISION_CONTRACT = "vs1-evolution-decision-d29"
D28_PATH = "vertical_slice/runtime_interpretation_d28_evidence.json"
D27_PATH = "vertical_slice/runtime_observation_d27_evidence.json"
D26_PATH = "vertical_slice/deployment_d26_evidence.json"
D25_PATH = "vertical_slice/implementation_d25_evidence.json"
D24_PATH = "vertical_slice/architecture_selection_d24_evidence.json"
D23_PATH = "vertical_slice/candidate_generation_d23_evidence.json"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"

# D28 coverage as recorded (authoritative; D29 does not recompute D28).
EXPECTED_COVERAGE = {
    "SC01": "UNKNOWN", "SC02": "OBSERVED", "SC03": "OBSERVED",
    "SC04": "OBSERVED", "SC05": "OBSERVED", "SC06": "UNKNOWN",
    "SC07": "OBSERVED", "SC08": "UNKNOWN", "SC09": "UNKNOWN",
    "SC10": "UNKNOWN", "SC11": "UNKNOWN", "SC12": "OBSERVED",
    "SC13": "OBSERVED",
}


class DecisionError(Exception):
    """Fail-closed decision failure."""


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
        raise DecisionError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise DecisionError(f"input malformed: {path}")
    return record


def verify_upstream() -> dict[str, Any]:
    """Record-level verification of the D22-D28 chain (read-only)."""
    d28 = _load_json(D28_PATH)
    d27 = _load_json(D27_PATH)
    d26 = _load_json(D26_PATH)
    d25 = _load_json(D25_PATH)
    d24 = _load_json(D24_PATH)
    d23 = _load_json(D23_PATH)
    d22 = _load_json(D22_PATH)
    if d28.get("interpretation_version") != "d28-interpretation-v1":
        raise DecisionError("D28 contract drift")
    coverage = {item["criterion_id"]: item["status"]
                for item in d28.get("requirement_coverage", [])}
    if coverage != EXPECTED_COVERAGE:
        raise DecisionError("D28 coverage drift")
    if d28.get("isr_hash") != EXPECTED_ISR:
        raise DecisionError("ISR drift")
    if d27.get("normalized_hash") != d28.get("source_evidence_hash"):
        raise DecisionError("D28→D27 lineage break")
    if d26.get("deployment", {}).get("deployment_hash") != d27.get(
            "deployment_hash"):
        raise DecisionError("D27→D26 lineage break")
    if d25.get("implementation_hash") != d27.get("implementation_hash"):
        raise DecisionError("D27→D25 lineage break")
    if d24.get("selected_candidate") != "vs1-obj001-candidate-313b071dd7d4":
        raise DecisionError("D24 drift")
    if d23.get("candidate_count") != 3:
        raise DecisionError("D23 drift")
    if d22.get("objective_id") != "VS1-OBJ-001":
        raise DecisionError("D22 drift")
    return {"d28": d28, "d27": d27, "d26": d26, "d25": d25,
            "d24": d24, "d23": d23, "d22": d22}


def capability_table() -> list[dict[str, Any]]:
    """Per-capability decisions under the authoritative coverage map."""
    cap = [
        {"id": "CAP-001", "claim": "Priority create/retrieve/filter/update "
                                  "behaved in the exercised fixture.",
         "sc": ["SC02", "SC03", "SC04", "SC05", "SC07"],
         "status": "OBSERVED", "decision": "HOLD",
         "rationale": "Supported within fixture scope; insufficient for "
                      "closure, production, or evolution.",
         "next": "authorized runtime/suite evidence for remaining SCs"},
        {"id": "CAP-002", "claim": "Migration/defaulting established.",
         "sc": ["SC01"], "status": "UNKNOWN", "decision": "HOLD",
         "rationale": "UNKNOWN cannot be upgraded by D29.",
         "next": "authorized evidence run covering legacy defaulting"},
        {"id": "CAP-003", "claim": "UI/read-model display established.",
         "sc": ["SC06"], "status": "UNKNOWN", "decision": "HOLD",
         "rationale": "No UI observation; read model is display data, "
                      "not display proof.",
         "next": "UI/read-model evidence or governed acceptance elsewhere"},
        {"id": "CAP-004", "claim": "CRUD/contract suites pass.",
         "sc": ["SC08", "SC09"], "status": "UNKNOWN", "decision": "HOLD",
         "rationale": "Suite proof lives at D25/test level, not runtime.",
         "next": "suite-level evidence mapped to SC08/SC09"},
        {"id": "CAP-005", "claim": "Candidate/deployment proven at runtime.",
         "sc": ["SC10", "SC11"], "status": "UNKNOWN", "decision": "HOLD",
         "rationale": "Selection quality and deployment success are not "
                      "runtime-establishable from a fixture.",
         "next": "governed acceptance per SC10/SC11"},
        {"id": "CAP-006", "claim": "Run occurred; chain traceable.",
         "sc": ["SC12", "SC13"], "status": "OBSERVED", "decision": "RETAIN",
         "rationale": "The governed chain is valid as evidence.",
         "next": "none"},
        {"id": "CAP-007", "claim": "Security correct in exercised cases.",
         "sc": ["SEC"], "status": "QUALIFIED_PARTIAL", "decision": "HOLD",
         "rationale": "Bounded observation only; no certification.",
         "next": "threat-model-scoped evidence if evolution needs it"},
        {"id": "CAP-008", "claim": "System is production-ready.",
         "sc": [], "status": "INSUFFICIENT", "decision": "BLOCK",
         "rationale": "No production evidence or authorization exists.",
         "next": "separate production track if ever proposed"},
        {"id": "CAP-009", "claim": "Autonomous evolution established.",
         "sc": [], "status": "INSUFFICIENT", "decision": "BLOCK",
         "rationale": "Higher-order capability; no evidence or authority.",
         "next": "none actionable under D29"},
        {"id": "CAP-010", "claim": "D22→D28 governed chain valid.",
         "sc": ["SC13"], "status": "SUPPORTED", "decision": "RETAIN",
         "rationale": "Valid as evidence; authorizes no execution.",
         "next": "repository-level verification before any execution gate"},
    ]
    # Enforce: UNKNOWN/INSUFFICIENT SCs can never yield ADVANCE-family outcomes.
    for entry in cap:
        if entry["status"] in ("UNKNOWN", "INSUFFICIENT") and entry[
                "decision"] not in ("HOLD", "BLOCK"):
            raise DecisionError(f"UNKNOWN upgraded: {entry['id']}")
    return cap


def evolution_decisions() -> list[dict[str, Any]]:
    """EV-001..EV-006 under E0-E5 classes (definition only, never execution)."""
    return [
        {"id": "EV-001", "class": "E0/E1", "claim": "Close VS1-OBJ-001.",
         "decision": "HOLD",
         "rationale": "Six SCs UNKNOWN; closure requires sufficient evidence.",
         "next": "evidence for SC01/SC06/SC08/SC09/SC10/SC11 or "
                  "separately authorized scope modification"},
        {"id": "EV-002", "class": "E1",
         "claim": "Define next bounded evidence-gap closure gate.",
         "decision": "ADVANCE",
         "rationale": "D28 unknowns + provenance suffice to define (not "
                      "execute) the next analytical step.",
         "next": "explicit authorization for the next gate"},
        {"id": "EV-003", "class": "E3", "claim": "Bounded implementation evolution.",
         "decision": "HOLD",
         "rationale": "UNKNOWNs identify gaps but do not justify mutation.",
         "next": "proposal + impact analysis + explicit authorization"},
        {"id": "EV-004", "class": "E4", "claim": "Runtime evolution.",
         "decision": "BLOCK",
         "rationale": "No runtime evolution authority exists.",
         "next": "runtime authorization + track evidence if proposed"},
        {"id": "EV-005", "class": "E5",
         "claim": "Production/autonomous evolution.",
         "decision": "BLOCK",
         "rationale": "No production/autonomy evidence or authority.",
         "next": "none actionable under D29"},
        {"id": "EV-006", "class": "E0", "claim": "Retain frozen artifacts.",
         "decision": "RETAIN",
         "rationale": "Upstream record remains authoritative.",
         "next": "none"},
    ]


def knowledge_ledger() -> list[dict[str, str]]:
    return [
        ("K-001", "D22 objective admission occurred", "SUPPORTED"),
        ("K-002", "D23 generated three candidates", "SUPPORTED"),
        ("K-003", "D24 selected candidate 313b071dd7d4", "SUPPORTED"),
        ("K-004", "D25 compiled vs1-impl-obj001-v1", "SUPPORTED"),
        ("K-005", "D26 compiled deployment artifact", "SUPPORTED"),
        ("K-006", "D27 observed runtime in loopback fixture", "QUALIFIED_PARTIAL"),
        ("K-007", "D28 produced epistemic interpretation", "SUPPORTED"),
        ("K-008", "Priority create/update/read/filter behaved in fixture",
         "QUALIFIED_PARTIAL"),
        ("K-009", "Migration/defaulting established at runtime", "UNKNOWN"),
        ("K-010", "UI display established", "UNKNOWN"),
        ("K-011", "CRUD/contract suites pass at runtime level", "UNKNOWN"),
        ("K-012", "Candidate/deployment proven at runtime", "UNKNOWN"),
        ("K-013", "Security correct beyond exercised cases", "UNKNOWN"),
        ("K-014", "System production-ready", "UNKNOWN"),
        ("K-015", "Autonomous evolution authorized", "BLOCKED"),
        ("K-016", "ISR unchanged through D28", "QUALIFIED_PARTIAL"),
        ("K-017", "D22→D28 chain defines next bounded step", "SUPPORTED"),
    ]


def contradiction_registry() -> list[dict[str, Any]]:
    """CON-001 preserved (prose-level transcription ambiguity, all machine
    records canonical). The example's CON-002 framing is inapplicable: under
    the authoritative coverage map there is no observation-to-criterion gap
    (D28's UNKNOWNs are genuinely unobserved at runtime), so no contradiction
    is manufactured to fill the registry."""
    return [{
        "id": "CON-001",
        "field": "ISR hash string",
        "left": "prompt prose containing f961a626f (D25/D26/D28/D23 docs)",
        "right": "canonical 48e53dcef47aad84… in all machine records",
        "classification": "provenance/transcription ambiguity",
        "impact": "prevents off-repo ISR certification; repository artifact controls",
        "resolution": "UNRESOLVED",
        "decision_effect": "contributes to HOLD posture, not BLOCK of definition",
    }]


def assemble_evidence(generated_at: str) -> dict[str, Any]:
    """Canonical D29 decision record. The final governance decision is
    PASS / HOLD: definition warranted, execution not."""
    upstream = verify_upstream()
    d28 = upstream["d28"]
    record: dict[str, Any] = {
        "contract": DECISION_CONTRACT,
        "decision_id": "vs1-decision-d29",
        "final_governance_decision": "PASS / HOLD",
        "capabilities": capability_table(),
        "evolution_decisions": evolution_decisions(),
        "knowledge": [{"id": k, "proposition": p, "classification": c}
                      for k, p, c in knowledge_ledger()],
        "contradictions": contradiction_registry(),
        "unknowns_preserved": len(d28.get("unknowns", [])),
        "authorizations": {
            "implementation": "NONE", "deployment": "NONE",
            "production": "NONE", "runtime_execution": "NONE",
            "autonomy": "NONE", "optimization": "NONE",
            "architecture_mutation": "NONE", "commit": "NONE", "push": "NONE",
        },
        "next_required_evidence": [
            "UNKNOWN closure evidence (SC01/SC06/SC08/SC09/SC10/SC11)",
            "repository-level provenance re-verification before execution",
            "explicit authorization artifact for any execution gate",
        ],
        "provenance": {
            "contract": DECISION_CONTRACT,
            "d28_interpretation": d28["interpretation_hash"],
            "d27_evidence": d28["source_evidence_hash"],
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["decision_hash"] = _sha(_canon(check))
    return record
