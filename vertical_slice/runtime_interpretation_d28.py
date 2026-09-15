#!/usr/bin/env python3
"""VS-D28 Runtime Evidence Interpretation / Epistemic Synthesis compiler.

Compiles authoritative D27 runtime evidence into a deterministic,
provenance-bound interpretation with explicit epistemic typing
(OBSERVED / INFERRED / UNKNOWN / CONTRADICTION). Interpretation ONLY:
no runtime execution, deployment, mutation, selection, decision,
production authorization, commit, or push. Fail-closed on any integrity
violation.

D27 records use operation/observed_class/status vocabulary; this compiler
transliterates them into semantic atoms through the explicit ADAPTER_TAGS
table (policy-owned transliteration, documented per observation ID —
never inferred per-record content).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

POLICY_VERSION = "d28-epistemic-v1"
INTERPRETATION_VERSION = "d28-interpretation-v1"
CANONICALIZATION_VERSION = "d28-canonical-v1"

EXPECTED_OBJECTIVE_ID = "VS1-OBJ-001"
EXPECTED_D27_RUN_ID = "vs1-d27-run-001"
EXPECTED_DEPLOYMENT_ID = "vs1-deploy-obj001-4ca3d24c13561599"
EXPECTED_IMPLEMENTATION_ID = "vs1-impl-obj001-v1"
EXPECTED_CANDIDATE_ID = "vs1-obj001-candidate-313b071dd7d4"
EXPECTED_SELECTION_PREFIX = "9c8803764dd5f8f7"
EXPECTED_GENERATION_PREFIX = "432ec0bf5a481d0a"
EXPECTED_ISR_HASH = (
    "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
)
EXPECTED_D27_EVIDENCE_HASH_PREFIX = "731ee7a264906f44"

ALLOWED_ACTIONS = {
    "verify_evidence",
    "normalize_evidence",
    "interpret_evidence",
    "emit_artifacts",
}

PROHIBITED_ACTIONS = {
    "runtime_execution",
    "http_request",
    "database_mutation",
    "deployment",
    "implementation_mutation",
    "candidate_generation",
    "architecture_selection",
    "evolution_decision",
    "production_authorization",
    "optimization",
    "commit",
    "push",
}

SECRET_PATTERNS = [
    # JSON key form: "password": "<value>" (canonical evidence shape).
    ("json_secret_key", re.compile(
        r'"(password|passwd|secret|token|api_key|session_cookie|private_key'
        r'|credential|authorization)"\s*:\s*"[^"]{4,}"')),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    # NOTE: canonical JSON backslash-escapes quotes, so optional
    # backslashes are tolerated around the value delimiters.
    ("generic_password", re.compile(
        r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*\\?['\"][^'\"]{8,}")),
    ("generic_secret", re.compile(
        r"(?i)\b(secret|token|api_key|apikey|access_token|refresh_token)\b"
        r"\s*[:=]\s*\\?['\"][^'\"]{16,}")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("database_url_with_credentials", re.compile(
        r"(?i)\b(postgresql|postgres|mongodb|redis|mysql)\+?://[^:\s]+:[^@\s]+@")),
]

NON_SEMANTIC_OBSERVATION_FIELDS = {
    "timestamp",
    "latency_ms",
    "duration_ms",
    "wall_clock",
}

DEFAULT_LIMITATIONS = [
    "Evidence applies only to the exercised D27 loopback fixture.",
    "No production readiness claim is made.",
    "No universal correctness claim is made.",
    "No security certification claim is made.",
    "Latency measurements are mechanical and not judged against an SLO.",
]

# Adapter: D27 observation_id → semantic tags. Each entry encodes what the
# corresponding workload step mechanically verified (established by the
# D27 gate's own assertions); the compiler adds only the status tag.
ADAPTER_TAGS: Dict[str, List[str]] = {
    "lifecycle.readiness": ["readiness"],
    "auth.register": ["authentication", "register"],
    "auth.login": ["authentication", "login"],
    "auth.invalid-rejected": ["authentication", "rejection"],
    "authz.admin-grant": ["authorization", "grant"],
    "auth.authenticated-request": ["authentication", "authorized_read"],
    "priority.create-low": ["priority_create", "priority_low", "crud_lifecycle"],
    "priority.create-medium": ["priority_create", "priority_medium",
                               "crud_lifecycle"],
    "priority.create-high": ["priority_create", "priority_high",
                             "crud_lifecycle"],
    "authz.permitted-operation": ["authorization", "permitted"],
    "priority.filter-high": ["priority_filter", "per_item_verified"],
    "priority.filter-low": ["priority_filter", "per_item_verified"],
    "priority.invalid-rejected": ["invalid_priority", "rejected"],
    "priority.filter-invalid-rejected": ["invalid_filter", "rejected"],
    "priority.update": ["priority_update", "crud_lifecycle"],
    "crud.read-after-update": ["priority_read_after_update", "task_read",
                               "crud_lifecycle"],
    "authz.outsider-rejected": ["authorization", "isolation", "rejection"],
    "authz.role-rejected": ["authorization", "role", "rejection"],
    "crud.delete": ["crud_lifecycle", "delete"],
    "crud.read-after-delete": ["crud_lifecycle", "read_after_delete"],
    "events.lifecycle-emitted": ["events"],
    "persist.restart-state": ["persistence", "restart"],
    "lifecycle.shutdown-clean": ["shutdown", "run_completed"],
}

# Canonical overgeneralization probes: always evaluated, always rejected
# unless evidence genuinely establishes them (it cannot from a fixture).
OVERGENERALIZATION_PROBES = [
    "production-ready",
    "universally secure",
    "fully scalable",
    "all CRUD preserved",
    "architecture optimal",
]


class FailClosed(Exception):
    pass


class ActionFirewall:
    def __init__(self) -> None:
        self.actions: List[str] = []

    def authorize(self, action: str) -> None:
        if action in PROHIBITED_ACTIONS:
            raise FailClosed(f"prohibited action requested: {action}")
        if action not in ALLOWED_ACTIONS:
            raise FailClosed(f"action not authorized by D28 firewall: {action}")
        self.actions.append(action)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise FailClosed(message)


def load_json(path: Path, label: str) -> Dict[str, Any]:
    if not path.is_file():
        fail(f"{label} missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{label} is not valid JSON: {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{label} must contain a JSON object: {path}")
    return data


def scan_for_secrets(obj: Any) -> List[str]:
    text = canonical_json(obj)
    return sorted({name for name, pattern in SECRET_PATTERNS
                   if pattern.search(text)})


def verify_evidence_file(evidence_path: Path,
                         expected_hash: Optional[str]) -> Dict[str, Any]:
    if not evidence_path.is_file():
        fail(f"D27 evidence missing: {evidence_path}")
    evidence = load_json(evidence_path, "D27 evidence")
    # Recompute the normalized hash exactly as the D27 assembler defines it
    # (over content minus provenance and minus the hash field itself).
    check = {k: v for k, v in evidence.items()
             if k not in ("provenance", "normalized_hash")}
    provenance = dict(evidence.get("provenance", {}))
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    recomputed = sha256_obj(check).lower()
    embedded = str(evidence.get("normalized_hash") or "").lower()
    if recomputed != embedded:
        fail("D27 evidence normalized_hash does not recompute")
    if expected_hash:
        if recomputed != expected_hash.lower():
            fail("D27 evidence hash does not match expected authoritative hash")
    elif not embedded.startswith(EXPECTED_D27_EVIDENCE_HASH_PREFIX):
        fail("D27 evidence hash prefix mismatch")
    secret_findings = scan_for_secrets(evidence)
    if secret_findings:
        fail("secret-shaped material in D27 evidence: "
             + ", ".join(secret_findings))
    return evidence


def verify_provenance(evidence: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return _verify_provenance_inner(evidence)
    except KeyError as exc:
        fail(f"D27 provenance record missing: {exc}")
        raise  # unreachable; fail() raises


def _verify_provenance_inner(evidence: Dict[str, Any]) -> Dict[str, Any]:
    if evidence.get("execution_id") != EXPECTED_D27_RUN_ID:
        fail("D27 run identity mismatch")
    if evidence.get("deployment_id") != EXPECTED_DEPLOYMENT_ID:
        fail("D26 deployment identity mismatch")
    if evidence.get("implementation_id") != EXPECTED_IMPLEMENTATION_ID:
        fail("D25 implementation identity mismatch")
    if evidence.get("architecture_id") != EXPECTED_CANDIDATE_ID:
        fail("D24 candidate identity mismatch")
    if evidence.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D22 objective identity mismatch")
    if evidence.get("isr_hash") != EXPECTED_ISR_HASH:
        fail("ISR hash mismatch")
    summary = evidence.get("summary", {})
    if summary.get("status_counts", {}).get("FAIL", 1) != 0:
        fail("D27 evidence contains FAIL observations; "
             "interpretation requires an all-recorded-clean run")
    return {
        "d27_run_id": EXPECTED_D27_RUN_ID,
        "deployment_id": EXPECTED_DEPLOYMENT_ID,
        "implementation_id": EXPECTED_IMPLEMENTATION_ID,
        "candidate_id": EXPECTED_CANDIDATE_ID,
        "selection_id": EXPECTED_SELECTION_PREFIX,
        "candidate_generation_id": EXPECTED_GENERATION_PREFIX,
        "objective_id": EXPECTED_OBJECTIVE_ID,
        "isr_hash": EXPECTED_ISR_HASH,
    }


def normalize_observation(obs: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("observation_id", "operation", "status"):
        if field not in obs:
            fail(f"observation missing required field: {field}")
    obs_id = obs["observation_id"]
    if obs_id not in ADAPTER_TAGS:
        fail(f"observation outside adapter vocabulary: {obs_id}")
    # Internal consistency: a PASS record must show its expected class;
    # otherwise the record is self-contradictory (forgery indicator).
    if str(obs.get("status") or "").strip().upper() == "PASS" and \
            obs.get("observed_class") != obs.get("expected_class"):
        fail(f"PASS record with unexpected observed class: {obs_id}")
    status = str(obs.get("status") or "").strip().upper()
    if status == "PASS":
        result, tags = "success", ["success"]
    elif status == "FAIL":
        result, tags = "failure", ["failure"]
    else:
        result, tags = "unknown", ["unknown"]
    measurement = obs.get("measurement", {})
    semantic: Dict[str, Any] = {
        "observation_id": obs_id,
        "semantic_key": obs.get("operation", ""),
        "category": obs.get("operation", "").split(".")[0],
        "result": result,
        "tags": sorted(set(ADAPTER_TAGS[obs_id]) | set(tags)),
        "scope": ["loopback-fixture", "exercised-workload", "non-production"],
    }
    http_status = measurement.get("http_status") if isinstance(
        measurement, dict) else None
    if http_status is not None:
        semantic["http_status"] = http_status
    return semantic


def normalize_observations(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = evidence.get("observations", [])
    if not isinstance(raw, list) or not raw:
        fail("D27 observations missing")
    normalized = [normalize_observation(obs) for obs in raw]
    by_id: Dict[str, Dict[str, Any]] = {}
    for obs in normalized:
        obs_id = obs["observation_id"]
        if obs_id in by_id and canonical_json(by_id[obs_id]) != canonical_json(obs):
            fail(f"duplicate observation with conflicting values: {obs_id}")
        by_id[obs_id] = obs
    return sorted(normalized, key=lambda item: item["observation_id"])


def detect_contradictions(
        observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for obs in observations:
        by_key.setdefault(obs["semantic_key"], []).append(obs)
    # A contradiction is the SAME logical operation reporting DIFFERENT
    # outcomes (success vs failure/unknown) — not mere parameter variation
    # (e.g. create-LOW vs create-HIGH both succeeding corroborates).
    contradictions = []
    index = 0
    for semantic_key in sorted(by_key):
        items = by_key[semantic_key]
        results = {item["result"] for item in items}
        if len(results) < 2:
            continue
        index += 1
        by_result: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            by_result.setdefault(item["result"], []).append(item)
        ordered = sorted(results)
        contradictions.append({
            "contradiction_id": f"CONTRA-{index:03d}",
            "semantic_key": semantic_key,
            "left_evidence_id": by_result[ordered[0]][0]["observation_id"],
            "right_evidence_id": by_result[ordered[1]][0]["observation_id"],
            "field": "result",
            "left_value": ordered[0],
            "right_value": ordered[1],
            "identity_context": semantic_key,
            "classification": "factual",
            "impact": "affected claims downgraded; positive conclusions blocked",
            "resolution_status": "UNRESOLVED",
        })
    return contradictions


def observation_has_tags(obs: Dict[str, Any], tags: List[str]) -> bool:
    obs_tags = set(obs.get("tags", []))
    return all(tag in obs_tags for tag in tags)


def evidence_strength_for_observations(
        observations: List[Dict[str, Any]]) -> str:
    if not observations:
        return "INSUFFICIENT"
    if len({obs["observation_id"] for obs in observations}) > 1:
        return "CORROBORATED"
    return "DIRECT"


def evaluate_criteria(policy: Dict[str, Any],
                      observations: List[Dict[str, Any]],
                      contradictions: List[Dict[str, Any]]
                      ) -> tuple:
    criteria = policy.get("criteria", [])
    if not isinstance(criteria, list) or not criteria:
        fail("D28 policy must define criteria")
    contradiction_keys = {c["semantic_key"] for c in contradictions}
    coverage, claims, unknowns = [], [], []
    unknown_index = 0
    for criterion in criteria:
        criterion_id = criterion.get("id")
        criterion_text = criterion.get("text", "")
        required_tag_sets = criterion.get("required_tag_sets", [])
        if not criterion_id or not isinstance(required_tag_sets, list):
            fail("criterion malformed")
        if criterion.get("special") == "provenance_verified":
            coverage.append({
                "criterion_id": criterion_id, "criterion_text": criterion_text,
                "status": "OBSERVED", "supporting_observations": [],
                "evidence_strength": "DIRECT",
                "scope": ["loopback-fixture", "exercised-workload",
                          "non-production"], "limitations": []})
            claims.append({
                "claim_id": f"CLAIM-{criterion_id}",
                "statement": f"{criterion_text} verified against the "
                             f"complete provenance chain.",
                "epistemic_class": "OBSERVED", "evidence_strength": "DIRECT",
                "supporting_observations": [],
                "scope": ["loopback-fixture", "exercised-workload",
                          "non-production"], "limitations": []})
            continue
        supporting, satisfied = [], True
        for tag_set in required_tag_sets:
            if not isinstance(tag_set, list):
                fail(f"criterion {criterion_id} contains malformed tag set")
            matches = [obs for obs in observations
                       if observation_has_tags(obs, tag_set)]
            if matches:
                supporting.extend(matches)
            else:
                satisfied = False
        supporting_sorted = sorted(
            supporting, key=lambda item: item["observation_id"])
        supporting_ids = [obs["observation_id"] for obs in supporting_sorted]
        has_contradiction = any(
            obs["semantic_key"] in contradiction_keys for obs in supporting_sorted)
        scope = ["loopback-fixture", "exercised-workload", "non-production"]
        limitations: List[str] = []
        if has_contradiction:
            status, strength = "CONTRADICTION", "CONTRADICTED"
            limitations.append("Authoritative observations conflict.")
        elif satisfied and supporting_sorted:
            status = "OBSERVED"
            strength = evidence_strength_for_observations(supporting_sorted)
        elif supporting_sorted:
            status, strength = "UNKNOWN", "LIMITED"
            limitations.append("Evidence is insufficient for this criterion.")
        else:
            status, strength = "UNKNOWN", "INSUFFICIENT"
            limitations.append("Evidence is insufficient for this criterion.")
            marker = criterion.get("unobservable_in_d27", {})
            if isinstance(marker, dict) and marker.get("reason"):
                limitations.append(str(marker["reason"]))
            unknown_index += 1
            unknowns.append({
                "unknown_id": f"UNKNOWN-{unknown_index:03d}",
                "question": f"Can {criterion_id} be established from "
                            f"authoritative D27 evidence?",
                "why_unknown": "Required observations are missing, "
                               "incomplete, or not semantically sufficient.",
                "missing_evidence": required_tag_sets,
                "affected_requirement_or_obligation": [criterion_id],
                "risk_if_assumed": "Assuming success would convert missing "
                                   "evidence into an unsupported claim.",
                "possible_future_evidence": [
                    "A future authorized run with observations satisfying "
                    "the required semantic tags."],
            })
        coverage.append({
            "criterion_id": criterion_id, "criterion_text": criterion_text,
            "status": status, "supporting_observations": supporting_ids,
            "evidence_strength": strength, "scope": scope,
            "limitations": limitations})
        if status in {"OBSERVED", "CONTRADICTION"}:
            claims.append({
                "claim_id": f"CLAIM-{criterion_id}",
                "statement": (
                    f"{criterion_text} was directly observed within the "
                    f"exercised D27 loopback workload."
                    if status == "OBSERVED" else
                    f"{criterion_text} is affected by contradictory D27 "
                    f"evidence."),
                "epistemic_class": status, "evidence_strength": strength,
                "supporting_observations": supporting_ids, "scope": scope,
                "limitations": limitations})
    return coverage, claims, unknowns


def evaluate_inferences(policy: Dict[str, Any],
                        observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    inferences = policy.get("inferences", [])
    if not isinstance(inferences, list):
        fail("D28 policy inferences must be a list")
    claims = []
    for inference in inferences:
        claim_id = inference.get("claim_id")
        statement = inference.get("statement")
        required_tag_sets = inference.get("required_tag_sets", [])
        reasoning = inference.get("reasoning")
        confidence = inference.get("confidence", "LIMITED")
        scope = inference.get("scope", ["loopback-fixture", "exercised-workload"])
        if not claim_id or not statement or not reasoning:
            fail("inference rule missing required fields")
        if not isinstance(required_tag_sets, list) or not required_tag_sets:
            fail(f"inference {claim_id} must define required_tag_sets")
        supporting, satisfied = [], True
        for tag_set in required_tag_sets:
            matches = [obs for obs in observations
                       if observation_has_tags(obs, tag_set)]
            if matches:
                supporting.extend(matches)
            else:
                satisfied = False
        if not satisfied:
            continue
        supporting_ids = sorted({obs["observation_id"] for obs in supporting})
        if not supporting_ids:
            fail(f"inference {claim_id} has no supporting observations")
        claims.append({
            "claim_id": claim_id, "statement": statement,
            "epistemic_class": "INFERRED", "evidence_strength": confidence,
            "supporting_observations": supporting_ids, "scope": scope,
            "limitations": ["This is an inference, not a direct runtime "
                            "observation.",
                            "It applies only within the declared scope."],
            "reasoning": reasoning})
    return claims


def evaluate_overgeneralizations() -> List[Dict[str, Any]]:
    """Canonical probes that must always be rejected from fixture evidence."""
    rejected = []
    for index, probe in enumerate(OVERGENERALIZATION_PROBES, start=1):
        rejected.append({
            "claim_id": f"REJECTED-{index:03d}",
            "claim": probe,
            "requested_classification": "INFERRED",
            "actual_classification": "REJECTED AS UNSUPPORTED",
            "supporting_evidence": [],
            "reason": "Fixture evidence cannot establish universal scope.",
            "scope_limitation": "loopback-fixture, exercised workload only",
        })
    return rejected


OVERGENERALIZATION_PROBES = [
    "production-ready",
    "universally secure",
    "fully scalable",
    "all CRUD preserved",
    "architecture optimal",
]


def validate_claim_scope(claim: Dict[str, Any], policy: Dict[str, Any]) -> None:
    forbidden = set(policy.get("forbidden_scopes", []))
    invalid = forbidden.intersection(set(claim.get("scope", [])))
    if invalid:
        fail(f"claim {claim.get('claim_id')} attempts unsupported scope: "
             + ", ".join(sorted(invalid)))


def build_provenance(provenance: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {"layer": "D28", "identity": "interpretation", "depends_on": "D27"},
        {"layer": "D27", "identity": provenance["d27_run_id"],
         "depends_on": "D26"},
        {"layer": "D26", "identity": provenance["deployment_id"],
         "depends_on": "D25"},
        {"layer": "D25", "identity": provenance["implementation_id"],
         "depends_on": "D24"},
        {"layer": "D24", "identity": provenance["candidate_id"],
         "depends_on": "D23"},
        {"layer": "D23", "identity": provenance["candidate_generation_id"],
         "depends_on": "D22"},
        {"layer": "D22", "identity": provenance["objective_id"],
         "depends_on": "ISR"},
        {"layer": "ISR", "identity": provenance["isr_hash"],
         "depends_on": "NONE"},
    ]


def canonical_payload(evidence: Dict[str, Any], policy: Dict[str, Any],
                      provenance: Dict[str, Any],
                      coverage: List[Dict[str, Any]],
                      claims: List[Dict[str, Any]],
                      contradictions: List[Dict[str, Any]],
                      unknowns: List[Dict[str, Any]],
                      rejected: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "interpretation_version": INTERPRETATION_VERSION,
        "policy_version": policy.get("policy_version", POLICY_VERSION),
        "objective_id": provenance["objective_id"],
        "source_evidence_id": provenance["d27_run_id"],
        "source_evidence_hash": evidence.get("normalized_hash", ""),
        "d27_run_id": provenance["d27_run_id"],
        "deployment_id": provenance["deployment_id"],
        "implementation_id": provenance["implementation_id"],
        "candidate_id": provenance["candidate_id"],
        "selection_id": provenance["selection_id"],
        "candidate_generation_id": provenance["candidate_generation_id"],
        "isr_hash": provenance["isr_hash"],
        "claims": sorted(claims, key=lambda item: item["claim_id"]),
        "requirement_coverage": sorted(
            coverage, key=lambda item: item["criterion_id"]),
        "contradictions": sorted(
            contradictions, key=lambda item: item["contradiction_id"]),
        "unknowns": sorted(unknowns, key=lambda item: item["unknown_id"]),
        "unsupported_claims": sorted(
            rejected, key=lambda item: item["claim_id"]),
        "provenance": build_provenance(provenance),
        "canonicalization": {
            "version": "d28-canonical-v1",
            "excluded_nonsemantic_fields": ["timestamp", "latency_ms"],
            "observation_ordering": "observation_id",
        },
        "scope": sorted(evidence.get("scope", ["loopback-fixture",
                                               "exercised-workload",
                                               "non-production"])),
        "limitations": [
            "Evidence applies only to the exercised D27 loopback fixture.",
            "No production readiness claim is made.",
            "No universal correctness claim is made.",
            "Latency measurements are mechanical and not judged against an SLO.",
        ],
    }


def render_fail_report(reason: str) -> str:
    return "\n".join([
        "VS-D28 STOP REPORT", "STATUS: FAIL", "",
        f"REASON: {reason}", "",
        "NEXT GATE:", "  D29 NOT AUTHORIZED.",
    ])


def run_d28(args) -> int:
    firewall = ActionFirewall()
    try:
        firewall.authorize("verify_evidence")
        evidence = verify_evidence_file(Path(args.d27_evidence),
                                        args.expected_d27_hash or None)
        provenance = verify_provenance(evidence)
        policy = load_json(Path(args.policy), "D28 policy")
        firewall.authorize("normalize_evidence")
        observations = normalize_observations(evidence)
        contradictions = detect_contradictions(observations)
        firewall.authorize("interpret_evidence")
        coverage, criterion_claims, unknowns = evaluate_criteria(
            policy, observations, contradictions)
        inference_claims = evaluate_inferences(policy, observations)
        claims = criterion_claims + inference_claims
        for claim in claims:
            validate_claim_scope(claim, policy)
        rejected = evaluate_overgeneralizations()
        payload = canonical_payload(evidence, policy, provenance, coverage,
                                    claims, contradictions, unknowns, rejected)
        interpretation_hash = sha256_obj(payload).lower()
        interpretation_id = f"vs1-d28-interp-{interpretation_hash[:16]}"
        interpretation = dict(payload)
        interpretation["interpretation_id"] = interpretation_id
        interpretation["interpretation_hash"] = interpretation_hash
        firewall.authorize("emit_artifacts")
        out_dir = Path(args.out_dir)
        docs_dir = Path(args.docs_dir)
        if args.write:
            out_dir.mkdir(parents=True, exist_ok=True)
            docs_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "runtime_interpretation_d28_evidence.json").write_text(
                canonical_json(interpretation), encoding="utf-8")
            handoff = {
                "d28_status": "PASS",
                "interpretation_id": interpretation_id,
                "interpretation_hash": interpretation_hash,
                "source_d27_run": provenance["d27_run_id"],
                "source_d27_evidence_hash": interpretation["source_evidence_hash"],
                "deployment_id": provenance["deployment_id"],
                "implementation_id": provenance["implementation_id"],
                "candidate_id": provenance["candidate_id"],
                "objective_id": provenance["objective_id"],
                "isr_hash": provenance["isr_hash"],
                "claim_count": len(claims),
                "unknown_count": len(unknowns),
                "contradiction_count": len(contradictions),
                "unsupported_claim_count": len(rejected),
                "requirement_coverage_summary": {
                    item["criterion_id"]: item["status"] for item in coverage},
                "security_summary": "bounded_to_exercised_workload",
                "operational_summary": "mechanical_observations_only",
                "scope": interpretation["scope"],
                "limitations": interpretation["limitations"],
                "next_gate": "D29",
                "authorization_state": "D29_AUTHORIZATION=NOT GRANTED",
            }
            (out_dir / "runtime_interpretation_d28_handoff.json").write_text(
                canonical_json(handoff), encoding="utf-8")
            manifest = {
                "interpretation_id": interpretation_id,
                "interpretation_hash": interpretation_hash,
                "contract": INTERPRETATION_VERSION,
                "policy_version": policy.get("policy_version", POLICY_VERSION),
                "source_evidence_hash": interpretation["source_evidence_hash"],
                "claim_count": len(claims),
                "unknown_count": len(unknowns),
                "contradiction_count": len(contradictions),
                "firewall_actions": sorted(firewall.actions),
            }
            (out_dir / "runtime_interpretation_d28_manifest.json").write_text(
                canonical_json(manifest), encoding="utf-8")
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "VS-D28 interpretation artifact",
                "type": "object",
                "required": ["interpretation_id", "interpretation_hash",
                             "objective_id", "source_evidence_hash",
                             "claims", "requirement_coverage",
                             "contradictions", "unknowns",
                             "unsupported_claims", "provenance"],
                "properties": {
                    key: {"type": ["array", "object", "string"]}
                    for key in ("claims", "requirement_coverage",
                                "contradictions", "unknowns",
                                "unsupported_claims", "provenance",
                                "interpretation_id", "interpretation_hash")},
            }
            (out_dir / "runtime_interpretation_d28_schema.json").write_text(
                canonical_json(schema), encoding="utf-8")
            (docs_dir / "VS1_RUNTIME_INTERPRETATION_D28.md").write_text(
                "# VS1 Runtime Interpretation D28\n\nEpistemic interpretation "
                "of the D27 loopback run. See "
                "runtime_interpretation_d28_evidence.json for the canonical "
                "record. No evolution decision is made here.\n",
                encoding="utf-8")
        counts = {
            "observed": len([c for c in claims
                             if c["epistemic_class"] == "OBSERVED"]),
            "inferred": len([c for c in claims
                             if c["epistemic_class"] == "INFERRED"]),
            "unknown": len(unknowns),
            "contradictions": len(contradictions),
            "unsupported_claims": len(rejected),
        }
        print(canonical_json({
            "status": "PASS",
            "interpretation_id": interpretation_id,
            "interpretation_hash": interpretation_hash,
            "counts": counts,
            "coverage": {item["criterion_id"]: item["status"]
                         for item in coverage},
            "emitted": args.write,
        }))
        return 0
    except FailClosed as exc:
        print(render_fail_report(str(exc)))
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="VS-D28 Runtime Evidence Interpretation compiler")
    parser.add_argument("--d27-evidence", default="",
                        help="Path to authoritative D27 evidence JSON.")
    parser.add_argument("--policy", default="",
                        help="Path to D28 policy JSON.")
    parser.add_argument("--expected-d27-hash", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out-dir", default="vertical_slice")
    parser.add_argument("--docs-dir", default="folder")
    args = parser.parse_args(argv)
    if not args.d27_evidence or not args.policy:
        print(render_fail_report(
            "D28 requires explicit --d27-evidence and --policy paths"))
        return 1
    return run_d28(args)


if __name__ == "__main__":
    sys.exit(main())
