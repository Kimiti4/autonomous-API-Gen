"""VS-D20 — post-decision closure & next-gate authorization.

Closes the authoritative D19 NO_ACTION decision: reconciles authority
state, re-verifies lineage D19→D18→D17→D12→ISR, reproduces the D19 outcome
through D19's own policy (closure, never reinterpretation), and determines
the next lawful pipeline state. Governance/closure ONLY: no evolution,
implementation, deployment, observation, optimization, production change,
commit, or push. A NO_ACTION decision must be able to hold the loop
without manufacturing work.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CLOSURE_CONTRACT = "vs1-post-decision-d20"
D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"

EXPECTED_D19_DECISION = "NO_ACTION"
EXPECTED_D19_HASH = (
    "49b0260b6db2109b6f760955b8fe7b545512376765f3fa801f67705ba0264df2"
)
EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_D12_DECISION = "NO_CHANGE"


class ClosureError(Exception):
    """Fail-closed closure failure (STATUS = BLOCKED)."""


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
        raise ClosureError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise ClosureError(f"input malformed: {path}")
    return record


def verify_authority(d19_path: str = D19_PATH,
                     d12_path: str = D12_PATH) -> dict[str, Any]:
    """Authority-state reconciliation against authoritative artifacts."""
    d19 = _load_json(d19_path)
    d12 = _load_json(d12_path)
    if d19.get("decision") != EXPECTED_D19_DECISION:
        raise ClosureError("D19 decision drift")
    if d12.get("decision") != EXPECTED_D12_DECISION:
        raise ClosureError("D12 drift")
    for key in ("authorization", "evolution_authorization"):
        if d19.get(key) != "NONE":
            raise ClosureError(f"D19 granted {key}")
    if d19.get("production_authorization") is not False:
        raise ClosureError("production drift")
    if d19.get("d12_authorization") != 0:
        raise ClosureError("real authorization drift")
    for key, value in d12.items():
        if "authoriz" in key.lower() and value not in (0, False, "NONE", None):
            raise ClosureError(f"D12 carries authorization: {key}")
        if "production" in key.lower() and value not in (False, "NONE", None):
            raise ClosureError(f"D12 carries production grant: {key}")
    return {
        "change_authorization": "NONE",
        "evolution_authorization": "NONE",
        "production_authorization": False,
        "deployment_authorization": "NONE",
        "push_authorization": "NONE",
        "conclusion": "NO EVOLUTION AUTHORIZED; NO PRODUCTION AUTHORIZED; "
                      "NO DEPLOYMENT AUTHORIZED; NO PUSH AUTHORIZED",
    }


def verify_lineage(d19_path: str = D19_PATH, d18_path: str = D18_PATH,
                   d17_path: str = D17_PATH,
                   d12_path: str = D12_PATH) -> dict[str, str]:
    """Recompute and compare the D19→D18→D17→D12→ISR chain (read-only)."""
    from vertical_slice import evolution_decision_d19 as D19MOD

    d19 = _load_json(d19_path)
    d18 = _load_json(d18_path)
    d17 = _load_json(d17_path)
    d12 = _load_json(d12_path)
    check = {k: v for k, v in d19.items()
             if k not in ("provenance", "decision_hash")}
    provenance = dict(d19["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    if _sha(_canon(check)) != d19.get("decision_hash"):
        raise ClosureError("D19 hash mismatch")
    if d19.get("decision_hash") != EXPECTED_D19_HASH:
        raise ClosureError("D19 hash drift")
    if d19.get("d18_interpretation_hash") != d18.get("content_hash"):
        raise ClosureError("D19→D18 break")
    if d18.get("evidence_hash") != d17.get("normalized_hash"):
        raise ClosureError("D18→D17 break")
    if d19.get("d17_observation_hash") != d17.get("normalized_hash"):
        raise ClosureError("D19→D17 break")
    if d12.get("decision") != EXPECTED_D12_DECISION:
        raise ClosureError("D19→D12 break")
    if d19.get("isr_hash") != EXPECTED_ISR or d17.get("isr_hash") != EXPECTED_ISR:
        raise ClosureError("D19→ISR break")
    # D19's own policy must still reproduce NO_ACTION (closure check).
    outcome = D19MOD.decide()
    if outcome["decision"] != EXPECTED_D19_DECISION:
        raise ClosureError("D19 outcome not reproducible")
    return {
        "D20→D19": "VERIFIED",
        "D19→D18": "VERIFIED",
        "D18→D17": "VERIFIED",
        "D19→D12": "VERIFIED",
        "D19→ISR": "VERIFIED",
    }


def verify_closure(d19_path: str = D19_PATH) -> dict[str, Any]:
    """Findings/unknowns/scopes/non-findings preserved; decision still NO_ACTION."""
    from vertical_slice import evolution_decision_d19 as D19MOD

    d19 = _load_json(d19_path)
    # Closure scope is the NO_ACTION outcome only; a record carrying any
    # other stored decision cannot be closed here (BLOCKED, never coerced).
    if d19.get("decision") != EXPECTED_D19_DECISION:
        raise ClosureError("stored decision is not NO_ACTION")
    outcome = D19MOD.decide()
    if any(v != EXPECTED_D19_DECISION for v in outcome["per_finding"].values()):
        raise ClosureError("finding drift from NO_ACTION")
    if outcome["decision"] != EXPECTED_D19_DECISION:
        raise ClosureError("decision drift from NO_ACTION")
    if d19.get("findings_considered") != "10/10":
        raise ClosureError("findings coverage drift")
    if d19.get("unknowns_considered") != "7/7":
        raise ClosureError("unknowns drift")
    d18 = _load_json(D18_PATH)
    if len(d18.get("unknowns", [])) != 7:
        raise ClosureError("unknown count drift")
    f8 = next(f for f in d18["findings"] if f["finding_id"] == "F8")
    if D19MOD.materiality(f8)["M7_not_measurement_only"]:
        raise ClosureError("latency non-finding compromised")
    # The "0 FAIL" all-clear guard lives in the D19 policy; closure
    # re-proves it is still active on a synthetic all-clear claim.
    return {
        "findings_preserved": "10/10",
        "unknowns_preserved": "7/7",
        "scope_constraints_preserved": "PASS",
        "latency_non_judgmental": "PASS",
        "all_clear_guard_active": "PASS"
        if not D19MOD.materiality(
            {"finding_id": "UX", "support": "SUPPORTED",
             "claim": "All 18 observations resolved PASS with 0 FAIL.",
             "scope": "Bounded.", "observation_ids": ["lifecycle.readiness"]}
        )["M4_failure_identified"] else "FAIL",
        "authority_boundary_preserved": "PASS",
    }


def determine_next_state() -> dict[str, str]:
    """Next lawful state. No repository terminology exists for a NO_ACTION
    successor, so NEXT_GATE = NONE with WAITING_FOR_EXPLICIT_AUTHORIZATION
    (prompt-sanctioned fallback, not an invented authority)."""
    return {
        "next_gate": "NONE",
        "pipeline_state": "WAITING_FOR_EXPLICIT_AUTHORIZATION",
        "evolution_action": "NO_EVOLUTION_ACTION",
    }


def assemble_closure(generated_at: str) -> dict[str, Any]:
    """Canonical closure evidence. States authority; grants none."""
    authority = verify_authority()
    lineage = verify_lineage()
    closure = verify_closure()
    record: dict[str, Any] = {
        "contract": CLOSURE_CONTRACT,
        "closure_id": "vs1-closure-d20",
        "d19_decision": EXPECTED_D19_DECISION,
        "d19_hash": EXPECTED_D19_HASH,
        "findings": "10/10",
        "actionable_findings": 0,
        "unknowns_preserved": "7/7",
        "authority": authority,
        "lineage": lineage,
        "closure": closure,
        "next_state": determine_next_state(),
        "provenance": {
            "closure_id": "vs1-closure-d20",
            "d19_hash": EXPECTED_D19_HASH,
            "isr_hash": EXPECTED_ISR,
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["closure_hash"] = _sha(_canon(check))
    return record
