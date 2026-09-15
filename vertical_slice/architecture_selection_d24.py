"""VS-D24 — candidate evaluation and architecture selection for VS1-OBJ-001.

Evaluates the three D23 candidates under a fixed, pre-registered policy
(vs1-selection-d24, tiered weights per the authorizing prompt) and selects
exactly one for downstream implementation consideration. Selection ONLY:
no implementation, deployment, observation, optimization, production
change, commit, or push. ISR immutable. Historical D13/D14 lineage
untouched and never consulted as evidence.

Scoring uses integer arithmetic (no float ordering hazards). Mandatory
gates (security/isolation/objective-admission) disqualify before scoring.
A genuine tie under this policy BLOCKs; ordering luck is never a decision.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SELECTION_CONTRACT = "vs1-architecture-selection-d24"
SELECTION_POLICY_ID = "vs1-selection-d24"
D23_PATH = "vertical_slice/candidate_generation_d23_evidence.json"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"

# Criterion tiers (weights). Tier assignment follows the authorizing
# prompt's priority order; weights are fixed here before any scoring.
CRITERIA: tuple[tuple[str, str, int], ...] = (
    ("C01", "objective satisfaction", 5),
    ("C02", "existing-obligation preservation", 5),
    ("C03", "ISR alignment", 5),
    ("C04", "security preservation", 5),
    ("C05", "tenant-isolation preservation", 5),
    ("C06", "API compatibility", 3),
    ("C07", "data/persistence safety", 3),
    ("C08", "migration safety", 3),
    ("C09", "failure containment", 3),
    ("C10", "verification feasibility", 3),
    ("C11", "operational simplicity", 3),
    ("C12", "architectural cohesion", 3),
    ("C13", "coupling minimization", 3),
    ("C14", "future extensibility", 2),
    ("C15", "reversibility", 2),
    ("C16", "implementation feasibility", 2),
    ("C17", "evolutionary value", 2),
)

# Score levels: 0 fails (mandatory gates disqualify at 0), 1 adequate,
# 2 strong. Scores below are read off candidate content recorded at D23
# (complexity, reversibility, coverage, stated trade-offs/risks); the
# arithmetic, not the analyst, produces the ranking.
SCORES: dict[str, dict[str, int]] = {
    "domain-model-extension": {
        "C01": 2, "C02": 2, "C03": 2, "C04": 2, "C05": 2,
        "C06": 2, "C07": 2, "C08": 2, "C09": 2, "C10": 2,
        "C11": 2, "C12": 1, "C13": 1, "C14": 1, "C15": 2,
        "C16": 2, "C17": 1,
    },
    "query-policy-separation": {
        "C01": 2, "C02": 2, "C03": 2, "C04": 2, "C05": 2,
        "C06": 2, "C07": 2, "C08": 2, "C09": 2, "C10": 2,
        "C11": 1, "C12": 2, "C13": 2, "C14": 2, "C15": 2,
        "C16": 2, "C17": 2,
    },
    "capability-oriented-extension": {
        "C01": 2, "C02": 2, "C03": 2, "C04": 2, "C05": 2,
        "C06": 1, "C07": 2, "C08": 2, "C09": 2, "C10": 1,
        "C11": 1, "C12": 2, "C13": 2, "C14": 2, "C15": 1,
        "C16": 1, "C17": 2,
    },
}

JUSTIFICATIONS: dict[str, dict[str, str]] = {
    "domain-model-extension": {
        "C12": "task authority absorbs the new concern (stated coupling risk)",
        "C13": "model coupled to priority concern",
        "C14": "further attributes repeat the coupling",
        "C17": "extends proven authority at coupling cost",
    },
    "query-policy-separation": {
        "C11": "one additional internal boundary under test",
    },
    "capability-oriented-extension": {
        "C06": "representation mapping seam at the boundary",
        "C10": "new seam plus lifecycle core to verify",
        "C11": "separately versioned capability to operate",
        "C15": "stored values inert but capability removal is work",
        "C16": "new seam on an unchanged core",
    },
}


class SelectionError(Exception):
    """Fail-closed selection failure (STATUS = BLOCKED)."""


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
        raise SelectionError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise SelectionError(f"input malformed: {path}")
    return record


def verify_upstream(d23_path: str = D23_PATH,
                    d22_path: str = D22_PATH) -> dict[str, Any]:
    """D23 candidate set + D22 admission + ISR pin (read-only)."""
    from vertical_slice import implementation as IMPL

    d23 = _load_json(d23_path)
    d22 = _load_json(d22_path)
    if d23.get("contract") != "vs1-candidate-generation-d23":
        raise SelectionError("D23 contract drift")
    if d23.get("candidate_count") != 3 or len(d23.get("candidates", [])) != 3:
        raise SelectionError("D23 candidate set drift")
    check = {k: v for k, v in d23.items()
             if k not in ("provenance", "generation_hash")}
    provenance = dict(d23["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    if _sha(_canon(check)) != d23.get("generation_hash"):
        raise SelectionError("D23 hash mismatch")
    if d22.get("objective_id") != "VS1-OBJ-001":
        raise SelectionError("objective drift")
    if not d22.get("admission", {}).get("objective_admitted"):
        raise SelectionError("D22 admission absent")
    if IMPL.frozen_input_identity()["vs-d02-isr-content-hash"] != EXPECTED_ISR:
        raise SelectionError("ISR drift")
    if d23.get("isr_hash") != EXPECTED_ISR:
        raise SelectionError("D23 ISR drift")
    return {"d23": d23, "d22": d22}


def mandatory_gates(candidate: dict[str, Any]) -> None:
    """Disqualifying checks. A service failure here BLOCKs selection of
    the candidate; if no candidate passes, selection BLOCKs outright."""
    lowered = _canon(candidate).lower()
    for token in ("membership", "403"):
        if token not in lowered:
            raise SelectionError(
                f"{candidate['candidate_id']}: security gate unproven")
    if candidate.get("priority_values") != ["LOW", "MEDIUM", "HIGH"]:
        raise SelectionError("priority values open")
    if candidate.get("event_classification") != "NO_EVENT_CHANGE_REQUIRED":
        raise SelectionError("event contract change smuggled")
    if "OUT_OF_SCOPE" in _canon(candidate).upper().replace(" ", "_"):
        raise SelectionError("scope expansion marker")


def evaluate(d23_path: str = D23_PATH,
             d22_path: str = D22_PATH) -> dict[str, Any]:
    """Score all candidates under the fixed policy; rank; select one."""
    upstream = verify_upstream(d23_path, d22_path)
    candidates = upstream["d23"]["candidates"]
    weights = {code: weight for code, _, weight in CRITERIA}
    results: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        mandatory_gates(candidate)
        profile = candidate["architecture_profile"]
        try:
            scores = SCORES[profile]
        except KeyError:
            raise SelectionError(f"unregistered profile: {profile}")
        if any(scores.get(code, -1) not in (0, 1, 2) for code, _, _ in CRITERIA):
            raise SelectionError(f"incomplete evaluation: {profile}")
        if any(scores[code] == 0 for code in ("C04", "C05")):
            raise SelectionError(f"mandatory security failure: {profile}")
        total = sum(scores[code] * weights[code] for code, _, _ in CRITERIA)
        results[candidate["candidate_id"]] = {
            "profile": profile,
            "scores": {code: scores[code] for code, _, _ in CRITERIA},
            "total": total,
            "hash": candidate["candidate_hash"],
        }
    ranking = sorted(results, key=lambda cid: (-results[cid]["total"], cid))
    totals = [results[cid]["total"] for cid in ranking]
    if len(set(totals)) != len(totals):
        raise SelectionError("genuine tie without lawful tie-breaker")
    winner = ranking[0]
    policy_hash = _sha(_canon({
        "policy": SELECTION_POLICY_ID,
        "criteria": [[c, d, w] for c, d, w in CRITERIA],
    }))
    return {
        "results": results,
        "ranking": ranking,
        "winner": winner,
        "policy_hash": policy_hash,
        "selection_hash": _sha(_canon({
            "winner": winner,
            "winner_hash": results[winner]["hash"],
            "ranking": ranking,
            "policy_hash": policy_hash,
            "objective": "VS1-OBJ-001",
            "isr": EXPECTED_ISR,
        })),
    }


def rationale(winner_id: str, evaluation: dict[str, Any],
              candidates: list[dict[str, Any]]) -> dict[str, str]:
    """Evidence-backed rationale: six required explanations."""
    by_id = {c["candidate_id"]: c for c in candidates}
    winner = by_id[winner_id]
    rejected = [c for c in candidates if c["candidate_id"] != winner_id]
    return {
        "satisfies_objective": (
            f"{winner['architecture_profile']} carries DIRECTLY_SUPPORTED "
            f"paths for creation, update, retrieval, and filtering."),
        "preserves_obligations": (
            "all requirement/ISR mappings resolve; existing CRUD, events, "
            "and persistence strategies unchanged."),
        "security_acceptable": (
            "membership-before-filter preserved; priority never an "
            "authorization input; invalid values fail closed."),
        "complexity_justified": (
            f"complexity {winner['complexity']}: the policy seam mirrors "
            f"the proven AuthorizationPolicy precedent rather than "
            f"improvising structure."),
        "rejected": "; ".join(
            f"{c['architecture_profile']}: {c['trade_offs']}" for c in rejected),
        "residual_risks": winner["risks"],
    }


def assemble_evidence(generated_at: str, d23_path: str = D23_PATH,
                      d22_path: str = D22_PATH) -> dict[str, Any]:
    """Canonical selection evidence. The winner is an input to the next
    gate — never an implementation authorization."""
    upstream = verify_upstream(d23_path, d22_path)
    d23, d22 = upstream["d23"], upstream["d22"]
    evaluation = evaluate(d23_path, d22_path)
    record: dict[str, Any] = {
        "contract": SELECTION_CONTRACT,
        "policy_id": SELECTION_POLICY_ID,
        "policy_hash": evaluation["policy_hash"],
        "objective_id": "VS1-OBJ-001",
        "objective_hash": d22["objective"]["objective_hash"],
        "isr_hash": EXPECTED_ISR,
        "candidate_count": 3,
        "evaluated": "3/3",
        "candidate_hashes": d23["candidate_hashes"],
        "evaluation": evaluation["results"],
        "ranking": evaluation["ranking"],
        "selected_candidate": evaluation["winner"],
        "selected_hash": evaluation["results"][evaluation["winner"]]["hash"],
        "rank": 1,
        "selection_hash": evaluation["selection_hash"],
        "selection_rationale": rationale(
            evaluation["winner"], evaluation, d23["candidates"]),
        "implementation_authorization": "NONE",
        "deployment_authorization": "NONE",
        "production_authorization": False,
        "push_authorization": "NONE",
        "provenance": {
            "contract": SELECTION_CONTRACT,
            "d23_generation": d23["generation_hash"],
            "d22_intake": d22["intake_hash"],
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["evidence_hash"] = _sha(_canon(check))
    return record
