"""VS-D19 — runtime interpretation → evolution decision gate.

Consumes the authoritative D18 interpretation and records a bounded,
deterministic evolution decision. Governance stage ONLY: no authorization,
no production change, no mutation of any upstream artifact, no candidate
generation/selection, no implementation, no deployment, no observation.

Decision policy (policy_id vs1-evolution-decision-v1): constitutional
preconditions first (any failure → BLOCKED), then per-finding materiality
(M1∧…∧M8), then deterministic aggregation (PROPOSED > INVESTIGATE >
MONITOR > NO_ACTION). A decision is never authorization: this module has
no path that emits authorization.

Artifact paths are D19-versioned (*_d19_*) because the unversioned
evolution_decision paths belong to frozen D08/D12 history.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

DECISION_POLICY_ID = "vs1-evolution-decision-v1"
DECISION_CONTRACT = "vs1-evolution-decision-d19"
D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"

DECISIONS: tuple[str, ...] = (
    "NO_ACTION", "MONITOR", "INVESTIGATE", "EVOLUTION_PROPOSED", "BLOCKED",
)

# Precedence for aggregation (BLOCKED handled separately, never aggregated).
PRECEDENCE: tuple[str, ...] = (
    "EVOLUTION_PROPOSED", "INVESTIGATE", "MONITOR", "NO_ACTION",
)

# M4 vocabulary: claim states a failure/weakness against an obligation.
FAILURE_TOKENS: tuple[str, ...] = (
    "fail", "violation", "weakness", "deficiency", "conflict",
    "vulnerability", "breach", "non-compliance", "regression",
    "unauthorized access", "bypass",
)

# M7 vocabulary: claim is only a measurement without judgment.
MEASUREMENT_TOKENS: tuple[str, ...] = (
    "latency", "measured mechanically", "no performance conclusion",
)

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_D12_DECISION = "NO_CHANGE"


class DecisionError(Exception):
    """Fail-closed decision failure (including firewall trips)."""


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


def verify_inputs(d18_path: str = D18_PATH, d17_path: str = D17_PATH,
                    d12_path: str = D12_PATH) -> dict[str, Any]:
    """Constitutional preconditions. Any failure → BLOCKED (raised)."""
    d18 = _load_json(d18_path)
    d17 = _load_json(d17_path)
    d12 = _load_json(d12_path)
    if d18.get("contract") != "vs1-runtime-interpret-v1":
        raise DecisionError("D18 contract drift")
    check = {k: v for k, v in d18.items()
             if k not in ("provenance", "content_hash")}
    provenance = dict(d18["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    d18_hash = _sha(_canon(check))
    if d18_hash != d18.get("content_hash"):
        raise DecisionError("D18 hash mismatch")
    if d18.get("evidence_hash") != d17.get("normalized_hash"):
        raise DecisionError("D17 lineage break")
    if d17.get("isr_hash") != EXPECTED_ISR:
        raise DecisionError("ISR drift")
    if d12.get("decision") != EXPECTED_D12_DECISION:
        raise DecisionError("D12 drift")
    findings = d18.get("findings")
    if not isinstance(findings, list) or not findings:
        raise DecisionError("D18 findings missing")
    known_obs = {r["observation_id"] for r in d17.get("observations", [])}
    for finding in findings:
        refs = finding.get("observation_ids", [])
        if not refs or any(r not in known_obs for r in refs):
            raise DecisionError(
                f"finding untraceable: {finding.get('finding_id')}")
        if not finding.get("scope"):
            raise DecisionError(
                f"scope missing: {finding.get('finding_id')}")
    if not d18.get("unknowns"):
        raise DecisionError("unknowns not preserved")
    from vertical_slice import regeneration as REG
    from vertical_slice import deployment_v2 as DEP
    if REG.build_evidence()["implementation_hash"] != \
            "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c":
        raise DecisionError("D15 drift")
    if DEP.contract_hash() != \
            "279fd4da7a47672cac211faf4da934208b9d2f66d8ed5d695fd7f4f7aa8f1dee":
        raise DecisionError("D16 drift")
    return {"d18": d18, "d17": d17, "d12": d12, "d18_hash": d18_hash}


def materiality(finding: dict[str, Any]) -> dict[str, bool]:
    """M1∧…∧M8 material-deficiency test for one D18 finding."""
    claim = str(finding.get("claim", "")).lower()
    scope = str(finding.get("scope", ""))
    refs = finding.get("observation_ids", [])
    # M4 helper: whole-word failure match; an explicit absence count
    # ("0 FAIL", "no violation") is an all-clear, never a failure.
    # Without this, the all-clear finding F9 would manufacture its own
    # deficiency out of the words "0 FAIL".
    words = set(re.findall(r"[a-z0-9]+", claim))
    _stated = any(t in words or t in claim for t in FAILURE_TOKENS)
    _negated = re.search(
        r"\b(0|no|without|zero|never|absence of)\b[^.]{0,24}"
        r"\b(fail\w*|violation\w*|weakness\w*|deficienc\w*|conflict\w*|"
        r"vulnerabilit\w*|breach\w*|shapes?|leak\w*)\b", claim) is not None
    _m4 = _stated and not _negated
    return {
        # M1: finding is SUPPORTED.
        "M1_supported": finding.get("support") == "SUPPORTED",
        # M2: concrete D17 observation references.
        "M2_concrete_refs": isinstance(refs, list) and len(refs) > 0,
        # M3: scope explicitly known.
        "M3_scope_explicit": len(scope.strip()) > 0,
        # M4: identifies a failure/weakness against an obligation
        # (computed above with all-clear negation handling).
        "M4_failure_identified": _m4,
        # M5: obligation already exists upstream. D18 findings state
        # observed behavior, never an upstream obligation breach; without
        # an explicit obligation reference the criterion is unmet. Only a
        # finding that names its upstream obligation can satisfy M5.
        "M5_existing_obligation": "obligation" in claim and any(
            t in claim for t in FAILURE_TOKENS),
        # M6: not merely an unresolved UNKNOWN.
        "M6_not_unknown": finding.get("support") != "UNKNOWN",
        # M7: not merely a performance measurement.
        "M7_not_measurement_only": not any(t in claim for t in MEASUREMENT_TOKENS),
        # M8: remediation plausibly requires architectural evolution.
        # Unknowable from observation alone; satisfied only together with
        # M4+M5 (a demonstrated architectural limitation).
        "M8_architectural": any(t in claim for t in FAILURE_TOKENS)
        and "architectur" in claim,
    }


def classify(finding: dict[str, Any]) -> str:
    """Deterministic per-finding classification."""
    material = materiality(finding)
    if all(material.values()):
        return "EVOLUTION_PROPOSED"
    claim = str(finding.get("claim", "")).lower()
    if finding.get("support") == "SUPPORTED" and (
            "unknown" in claim or "suspected" in claim
            or material["M4_failure_identified"]):
        return "INVESTIGATE"
    if finding.get("support") in ("SUPPORTED", "HYPOTHESIZED"):
        # A tracked scope limitation is a bounded signal worth monitoring
        # only if it names a concrete residual risk; plain passing scope
        # notes carry no signal.
        if any(t in claim for t in ("risk", "residual", "watch", "track")):
            return "MONITOR"
        return "NO_ACTION"
    return "INVESTIGATE"


def decide(d18_path: str = D18_PATH, d17_path: str = D17_PATH,
           d12_path: str = D12_PATH) -> dict[str, Any]:
    """Run the full policy: preconditions → classify → aggregate."""
    inputs = verify_inputs(d18_path, d17_path, d12_path)
    d18 = inputs["d18"]
    classes = {f["finding_id"]: classify(f) for f in d18["findings"]}
    decision = "NO_ACTION"
    for candidate in PRECEDENCE:
        if candidate in classes.values():
            decision = candidate
            break
    material = {fid: materiality(f) for fid, f in
                ((f["finding_id"], f) for f in d18["findings"])}
    return {
        "decision": decision,
        "per_finding": classes,
        "materiality": material,
        "d18_hash": inputs["d18_hash"],
    }


def assemble_evidence(generated_at: str, d18_path: str = D18_PATH,
                        d17_path: str = D17_PATH,
                        d12_path: str = D12_PATH) -> dict[str, Any]:
    """Canonical decision evidence. Contains NO authorization: the
    authorization fields restate the inherited D12 NONE/FALSE state."""
    inputs = verify_inputs(d18_path, d17_path, d12_path)
    d18, d17, d12 = inputs["d18"], inputs["d17"], inputs["d12"]
    outcome = decide()
    record: dict[str, Any] = {
        "contract": DECISION_CONTRACT,
        "policy_id": DECISION_POLICY_ID,
        "decision_id": "vs1-decision-d19",
        "decision": outcome["decision"],
        "decision_rationale": (
            "Mechanical application of vs1-evolution-decision-v1 to the "
            "authoritative D18 interpretation: no finding satisfies "
            "M1∧…∧M8 (no SUPPORTED failure against an existing "
            "obligation), no supported deficiency needs more evidence, "
            "no bounded risk signal exists; unknowns and scope limits "
            "preserved, latency non-finding preserved."
            if outcome["decision"] == "NO_ACTION" else
            "See per_finding classifications and materiality matrix."
        ),
        "per_finding": outcome["per_finding"],
        "materiality": outcome["materiality"],
        "d18_interpretation_id": d18["execution_id"],
        "d18_interpretation_hash": inputs["d18_hash"],
        "d17_observation_id": d17["execution_id"],
        "d17_observation_hash": d17["normalized_hash"],
        "d12_decision": d12.get("decision"),
        "d12_authorization": 0,
        "isr_hash": EXPECTED_ISR,
        "findings_considered": f"{len(d18['findings'])}/{len(d18['findings'])}",
        "unknowns_considered": f"{len(d18['unknowns'])}/{len(d18['unknowns'])}",
        "scope_constraints": "all D18 scope notes preserved verbatim by reference",
        "authorization": "NONE",
        "evolution_authorization": "NONE",
        "production_authorization": False,
        "provenance": {
            "decision_id": "vs1-decision-d19",
            "policy_id": DECISION_POLICY_ID,
            "d18_hash": inputs["d18_hash"],
            "d17_hash": d17["normalized_hash"],
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
