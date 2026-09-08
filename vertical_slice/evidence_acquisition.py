"""VS-D09 — evidence acquisition / evolution trigger gate (planning only).

Determines what additional evidence, if any, is necessary to reduce the
uncertainty of D08-deferred hypotheses. Emits evidence plans, never evolution
authorizations. No system modification of any kind. See
folder/VS1_EVIDENCE_ACQUISITION.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

ACQUISITION_CONTRACT_VERSION = "vs1-evidence-acquisition-v1"
ACQUISITION_CONTRACT_ID = "vs1-evidence-acquisition-v1"
ACQUISITION_POLICY_VERSION = "vs1-evidence-acquisition-v1"

_OUTCOMES = (
    "NO_ADDITIONAL_EVIDENCE_REQUIRED",
    "EVIDENCE_PLAN_REQUIRED",
    "EVIDENCE_PLAN_BLOCKED",
)

# Secret-value shapes (key=value assignments), not discussion words: plans
# must be able to *require* redaction/credential-handling in prose without
# tripping the retention guard.
_SECRET_VALUE_RE = (
    r"(password|passwd|secret|api_key|apikey|session_cookie|private_key"
    r"|credential)\s*[:=]\s*\S+"
)


class AcquisitionError(Exception):
    """Fail-closed acquisition failure (never guess a plan)."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_decision(
    path: str = "vertical_slice/evolution_decision_evidence.json",
) -> dict[str, Any]:
    """Load + validate the frozen D08 decision record (fail-closed)."""
    try:
        with open(path, encoding="utf-8") as f:
            decision = json.load(f)
    except (OSError, ValueError) as exc:
        raise AcquisitionError(f"D08 decision unavailable: {exc}")
    if not isinstance(decision, dict):
        raise AcquisitionError("D08 decision malformed")
    for field in ("decision", "evaluations", "content_hash", "policy_id",
                  "provenance"):
        if field not in decision:
            raise AcquisitionError(f"D08 record missing field: {field}")
    if decision.get("policy_id") != "vs1-evolution-decision-v1":
        raise AcquisitionError("D08 policy mismatch")
    if decision.get("decision") != "NO_CHANGE":
        raise AcquisitionError(
            f"D09 requires D08=NO_CHANGE, found {decision.get('decision')}")
    return decision


def validate_hypothesis(hypothesis: dict[str, Any]) -> None:
    """Fail-closed structural check for one D07 hypothesis."""
    for field in ("hypothesis_id", "statement", "falsifiers",
                  "evolution_eligibility", "supporting_findings"):
        if field not in hypothesis:
            raise AcquisitionError(
                f"hypothesis missing field: {field}")
    if not hypothesis["falsifiers"]:
        raise AcquisitionError(
            f"hypothesis {hypothesis.get('hypothesis_id')} lacks a falsifier")
    if hypothesis.get("evolution_eligibility") not in (
            "eligible_for_evolution_review", "requires_more_evidence",
            "insufficient_evidence", "contradicted", "out_of_scope"):
        raise AcquisitionError("hypothesis has unknown eligibility")


def load_hypotheses(
    path: str = "vertical_slice/interpretation_evidence.json",
) -> list[dict[str, Any]]:
    """Load the frozen D07 hypotheses (fail-closed)."""
    try:
        with open(path, encoding="utf-8") as f:
            evidence = json.load(f)
    except (OSError, ValueError) as exc:
        raise AcquisitionError(f"D07 hypotheses unavailable: {exc}")
    if not isinstance(evidence, dict):
        raise AcquisitionError("D07 evidence malformed")
    hypotheses = evidence.get("hypotheses", [])
    if not hypotheses:
        raise AcquisitionError("D07 evidence has no hypotheses")
    for hypothesis in hypotheses:
        validate_hypothesis(hypothesis)
    return hypotheses


def upstream_identities(decision: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities; cross-check D08 provenance."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    expected = {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": "vs1-candidate-a",
        "vs-d03-policy": C.SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
        "vs-d07-interpretation": "vs1-interpret-v1",
        "vs-d08-decision": "vs1-decision-v1",
    }
    record_prov = decision.get("provenance", {})
    for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash", "vs-d03-selected"):
        if record_prov.get(key) != expected[key]:
            raise AcquisitionError(f"upstream drift in D08 provenance: {key}")
    return expected


_KNOWN_GAPS: dict[str, dict[str, Any]] = {
    "vs1-hypothesis-auth-model-adequate": {
        "unknown_to_resolve": (
            "Whether session-token authorization holds across the full role "
            "boundary (admin-allowed administration, member-attempted admin "
            "action rejection, repeated credential rejection) rather than "
            "only the outsider-rejection shape observed in P04."),
        "required_observation": (
            "Bounded authorization probe set against the frozen deployment: "
            "admin-allowed member administration observed; member-attempted "
            "admin action rejected; repeated wrong-password logins rejected; "
            "all without persisting credentials."),
        "observation_count": 4,
        "success_criteria": [
            "admin-allowed administration returns 201",
            "member-attempted admin action returns 403",
            "repeated wrong-password logins return 401 with identical errors",
            "no credential material appears in any record",
        ],
        "falsification_criteria": [
            "any authorization probe returns an unexpected status",
            "credential material appears in any record",
        ],
        "scope": "frozen vs1-impl-v1 on vs1-deploy-v1; read-only probes plus "
                 "reversible membership changes on an isolated store",
        "out_of_scope": ["production traffic", "load testing", "new roles",
                         "implementation changes"],
    },
    "vs1-hypothesis-deploy-repeatable": {
        "unknown_to_resolve": (
            "Whether deployment reproduces from the version-controlled "
            "descriptor across independently initiated cycles, rather than "
            "the single observed instance."),
        "required_observation": (
            "Three independently initiated deployment cycles using the same "
            "frozen deployment contract and implementation identity, each "
            "followed by readiness + one CRUD probe; fresh isolated store "
            "per cycle."),
        "observation_count": 3,
        "success_criteria": [
            "all 3 cycles reach readiness within the bounded window",
            "all 3 cycles complete the CRUD probe with identical outcomes",
        ],
        "falsification_criteria": [
            "any cycle fails readiness",
            "any cycle diverges behaviorally from the others",
        ],
        "scope": "frozen vs1-impl-v1 with vs1-deploy-v1; isolated stores; "
                 "no shared mutable state between cycles",
        "out_of_scope": ["fresh-host provisioning", "cloud deployment",
                         "implementation changes"],
    },
}


def analyze_hypothesis(hypothesis: dict[str, Any]) -> dict[str, Any]:
    """Produce the §5 analysis for one deferred hypothesis (fail-closed)."""
    hid = hypothesis.get("hypothesis_id", "?")
    if hypothesis.get("evolution_eligibility") != "requires_more_evidence":
        raise AcquisitionError(
            f"hypothesis {hid} is not deferred-requiring-evidence")
    gap = _KNOWN_GAPS.get(hid)
    if gap is None:
        raise AcquisitionError(
            f"no bounded evidence gap defined for hypothesis: {hid}")
    return {"hypothesis_id": hid, **gap,
            "current_status": "deferred",
            "reason_deferred": "requires_more_evidence per D08",
            "uncertainty": ("single-observation basis" if "deploy" in hid
                            else "role-boundary coverage"),
            "falsifier": list(hypothesis.get("falsifiers", [])),
            "decision_after_evidence": "REVIEW_AGAIN"}


_PLAN_FIELDS = (
    "plan_id", "hypothesis_id", "objective", "unknown_to_resolve",
    "required_observation", "observation_count", "independence_requirement",
    "success_criteria", "falsification_criteria", "termination_condition",
    "scope", "out_of_scope", "risk_constraints", "provenance_requirements",
    "privacy_requirements", "security_requirements",
    "reproducibility_requirements",
)


def check_plan_integrity(plan: dict[str, Any]) -> None:
    """Fail-closed structural check for one D09 plan (§4 field list)."""
    for field in _PLAN_FIELDS:
        if field not in plan:
            raise AcquisitionError(f"plan missing field: {field}")
    _check_plan_safety(plan)


def _check_plan_safety(plan: dict[str, Any]) -> None:
    blob = json.dumps(plan).lower()
    for marker in ("source-code modification", "architecture modification",
                   "schema change", "api redesign", "new dependenc",
                   "new service", "new framework", "database migration"):
        if marker in blob:
            raise AcquisitionError(
                f"plan requires implementation modification: {marker}")
    for marker in ("mutate isr", "rewrite requirement", "new requirement"):
        if marker in blob:
            raise AcquisitionError("plan requires ISR/requirement mutation")
    import re as _re
    if _re.search(_SECRET_VALUE_RE, blob, _re.IGNORECASE):
        raise AcquisitionError("plan retains secret material (key=value shape)")
    privacy = " ".join(plan.get("privacy_requirements", [])).lower()
    if "redact" not in privacy:
        raise AcquisitionError("plan lacks explicit redaction requirement")


def build_plan(analysis: dict[str, Any],
               provenance: dict[str, str]) -> dict[str, Any]:
    """Build one deterministic Evidence Acquisition Plan (fail-closed)."""
    hid = analysis["hypothesis_id"]
    plan_id = _stable_id("vs1-evidence-plan", hid,
                         str(analysis["observation_count"]))
    plan = {
        "plan_id": plan_id,
        "hypothesis_id": hid,
        "objective": analysis["unknown_to_resolve"],
        "unknown_to_resolve": analysis["unknown_to_resolve"],
        "required_observation": analysis["required_observation"],
        "observation_count": analysis["observation_count"],
        "independence_requirement": (
            "separate processes; isolated stores; no shared mutable state"),
        "success_criteria": list(analysis["success_criteria"]),
        "falsification_criteria": list(analysis["falsification_criteria"]),
        "termination_condition": (
            "stop after the specified observation count or on first "
            "falsification, whichever comes first"),
        "scope": analysis["scope"],
        "out_of_scope": list(analysis["out_of_scope"]),
        "risk_constraints": ["loopback only", "synthetic credentials",
                             "isolated stores", "no production contact"],
        "provenance_requirements": ["contract", "deployment", "implementation",
                                    "upstream hashes", "run identity"],
        "privacy_requirements": ["no credential persistence",
                                 "token redaction", "marker scan"],
        "security_requirements": ["least privilege", "explicit admin seeding",
                                  "no secret logs"],
        "reproducibility_requirements": ["frozen contract", "fixed probe order",
                                         "deterministic normalization"],
        "provenance": dict(provenance),
    }
    if not isinstance(plan["observation_count"], int) or plan["observation_count"] < 1:
        raise AcquisitionError("unbounded experiment: observation_count invalid")
    _check_plan_safety(plan)
    return plan


def determine_outcome(plans: list[dict[str, Any]], blocked: list[str]) -> str:
    """Pure outcome rule (testable in isolation)."""
    if blocked:
        return "EVIDENCE_PLAN_BLOCKED"
    if plans:
        return "EVIDENCE_PLAN_REQUIRED"
    return "NO_ADDITIONAL_EVIDENCE_REQUIRED"


def run_gate() -> dict[str, Any]:
    """Execute the D09 gate: verify → analyze → plan → outcome (no acquisition)."""
    decision = load_decision()
    hypotheses = load_hypotheses()
    identities = upstream_identities(decision)

    deferred = [h for h in hypotheses
                if h.get("evolution_eligibility") == "requires_more_evidence"]
    plans, blocked = [], []
    for hypothesis in sorted(deferred, key=lambda h: h["hypothesis_id"]):
        try:
            analysis = analyze_hypothesis(hypothesis)
            plans.append(build_plan(
                analysis, {**identities,
                           "vs-d08-decision": decision["decision"],
                           "vs-d08-policy": decision["policy_id"]}))
        except AcquisitionError as exc:
            blocked.append(f"{hypothesis['hypothesis_id']}: {exc}")
    # Eligible NO_ACTION hypotheses are never planned: only deferred ones
    # reach build_plan above. Enforced structurally; pinned by test.
    for plan in plans:
        check_plan_integrity(plan)
    outcome = determine_outcome(plans, blocked)
    record = {
        "contract": ACQUISITION_CONTRACT_ID,
        "contract_version": ACQUISITION_CONTRACT_VERSION,
        "policy": ACQUISITION_POLICY_VERSION,
        "upstream_identities": identities,
        "d08_decision": decision["decision"],
        "outcome": outcome,
        "hypotheses_reviewed": sorted(h["hypothesis_id"] for h in deferred),
        "plans": sorted(plans, key=lambda p: p["plan_id"]),
        "remain_deferred": sorted(
            h["hypothesis_id"] for h in deferred
            if h["hypothesis_id"] not in {p["hypothesis_id"] for p in plans}),
        "blocked": sorted(blocked),
        "evolution_authorized": False,
        "provenance": dict(decision.get("provenance", {})),
    }
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if outcome not in ("NO_ADDITIONAL_EVIDENCE_REQUIRED",
                       "EVIDENCE_PLAN_REQUIRED", "EVIDENCE_PLAN_BLOCKED"):
        raise AcquisitionError(f"ambiguous outcome: {outcome}")
    return record
