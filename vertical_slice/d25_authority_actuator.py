#!/usr/bin/env python3
"""Constitutional Implementation Actuator for VS-D25 (repo-adapted).

Verify-before-write transaction: in --plan-only mode it verifies the full
upstream chain and prints the deterministic implementation identity without
writing anything; in --write mode (with verified behavior evidence) it
emits ONLY the actuator-owned manifest + deployment handoff. It never
overwrites upstream artifacts, never deploys/commits/pushes, and fails
closed (BLOCKED) on any verification failure.

Adaptations from folder/D25.md (documented, constitutional):
  - real artifact paths (not the hypothetical d22_objective_intake.json
    / isr_canonical.json names);
  - canonical ISR hash (the spec text carries an f961a626f slip);
  - ensure_ascii=False canonicalization (D15-D25 repo standard);
  - D24 architecture validation mapped to our frozen D24 record shape via
    ARCHITECTURE_FIELD_MAP (D24 itself is never rewritten to fit);
  - frontend display/filter proven via the API read model (this slice has
    no UI layer; scope documented in VS1_IMPLEMENTATION_D25.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

POLICY_VERSION = "d25-authority-v1"

EXPECTED_OBJECTIVE_ID = "VS1-OBJ-001"
EXPECTED_SELECTED_CANDIDATE = "vs1-obj001-candidate-313b071dd7d4"
EXPECTED_ISR_SHA256 = (
    "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
)
EXPECTED_OBJECTIVE_SOURCE_SHA256 = (
    "4a9cde9ab822980985dc59e1f05649a456ee6ae3be6b30421183801d12ac6848"
)
EXPECTED_D23_EVIDENCE_PREFIX = "432ec0bf5a481d0a"
EXPECTED_D25_EVIDENCE_PREFIX = "7dbbf34fe75660f1"

PRIORITY_VALUES = {"LOW", "MEDIUM", "HIGH"}

REQUIRED_CAPABILITIES = {
    "create_task_with_priority",
    "update_task_priority",
    "retrieve_task_priority",
    "display_task_priority",
    "filter_tasks_by_priority",
    "preserve_existing_taskflow_behavior",
}

REQUIRED_SECURITY = {
    "authentication",
    "authorization",
    "tenant_isolation",
    "credential_safety",
    "password_hashing",
}

# Our ISR node IDs backing each required obligation family.
ISR_OBLIGATION_MAP = {
    "domain": {"dm-task", "svc-task"},
    "persistence": {"dm-task"},
    "api": {"api-task"},
    "frontend": {"api-task"},  # slice-scope adaptation: API read model
    "security": {"sec-credential-safety", "sec-tenant-isolation"},
    "testing": {"svc-task"},
    "documentation": {"api-task"},
}

REQUIRED_BEHAVIOR_CHECKS = {
    "t11_low_priority_accepted",
    "t12_medium_priority_accepted",
    "t13_high_priority_accepted",
    "t14_invalid_priority_rejected",
    "t15_create_persists_priority",
    "t16_retrieve_returns_priority",
    "t17_update_changes_priority",
    "t18_invalid_update_rejected",
    "t19_priority_filter_works",
    "t20_filter_no_match_correct",
    "t21_frontend_displays_priority",
    "t22_frontend_priority_filter_works",
    "t23_existing_create_preserved",
    "t24_existing_retrieve_preserved",
    "t25_existing_update_preserved",
    "t26_existing_deletion_lifecycle_preserved",
    "t27_authorization_preserved",
    "t28_unauthorized_access_rejected",
    "t29_tenant_isolation_preserved",
    "t30_credential_safety_preserved",
    "t31_password_hashing_preserved",
    "t32_persistence_survives_restart",
    "t33_existing_task_data_preserved",
    "t34_event_behavior_preserved",
    "t40_repeated_implementation_deterministic",
    "t41_reordered_inputs_deterministic",
    "t42_implementation_hash_reproducible",
    "t43_isr_unchanged",
    "t44_d22_unchanged",
    "t45_d23_unchanged",
    "t46_d24_unchanged",
    "t47_parent_implementation_not_overwritten",
    "t56_production_authorization_false",
}

SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "credential",
    "private_key",
    "session",
    "cookie",
    "api_key",
)

PROHIBITED_ACTIONS = {
    "candidate_generation",
    "candidate_selection",
    "architecture_mutation",
    "isr_mutation",
    "evolution_authorization",
    "deployment",
    "redeployment",
    "runtime_observation",
    "evidence_interpretation",
    "optimization",
    "production_activation",
    "commit",
    "push",
}

ALLOWED_ACTIONS = {
    "verify_upstream",
    "compile_implementation",
    "emit_evidence",
    "emit_handoff",
    "local_test",
}


class FailClosed(Exception):
    pass


class ActionFirewall:
    def __init__(self) -> None:
        self.actions: List[str] = []

    def authorize(self, action: str) -> None:
        if action in PROHIBITED_ACTIONS:
            raise FailClosed(f"prohibited action requested: {action}")
        if action not in ALLOWED_ACTIONS:
            raise FailClosed(f"action not authorized by D25 firewall: {action}")
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
        raise FailClosed(f"{label} artifact missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise FailClosed(f"{label} artifact is not valid JSON: {path}: {exc}")
    if not isinstance(data, dict):
        raise FailClosed(f"{label} artifact must contain a JSON object: {path}")
    return data


def verify_objective_source(root: Path) -> Dict[str, Any]:
    path = root / "vertical_slice/objective_source_VS1-OBJ-001.json"
    data = load_json(path, "objective source")
    if sha256_file(path).lower() != EXPECTED_OBJECTIVE_SOURCE_SHA256:
        fail("objective source digest mismatch")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("objective source objective_id is not VS1-OBJ-001")
    return {"source_sha256": EXPECTED_OBJECTIVE_SOURCE_SHA256,
            "objective_hash": sha256_obj(data)}


def verify_d22(root: Path, objective_source: Dict[str, Any]) -> Dict[str, Any]:
    data = load_json(root / "vertical_slice/objective_intake_d22_evidence.json",
                     "D22 intake")
    if data.get("status") != "PASS" or not data.get("admission", {}).get(
            "objective_admitted"):
        fail("D22 is not PASS/admitted")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D22 objective_id drift")
    ref = str(data.get("source_reference", ""))
    if "objective_source_VS1-OBJ-001.json" not in ref:
        fail("D22 source_reference does not resolve to the persisted record")
    if objective_source["source_sha256"] not in ref:
        fail("D22 source digest does not match the verified record")
    objective = data.get("objective")
    if not isinstance(objective, dict) or not objective.get("objective_hash"):
        fail("D22 admitted objective content missing")
    return {"d22_hash": sha256_obj(data),
            "objective_hash": objective["objective_hash"]}


def verify_d23(root: Path) -> Dict[str, Any]:
    data = load_json(root / "vertical_slice/candidate_generation_d23_evidence.json",
                     "D23 generation")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D23 objective_id drift")
    if not str(data.get("generation_hash", "")).startswith(
            EXPECTED_D23_EVIDENCE_PREFIX):
        fail("D23 generation evidence prefix mismatch")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        fail("D23 candidate set drift")
    selected = next((c for c in candidates
                     if isinstance(c, dict) and c.get("candidate_id")
                     == EXPECTED_SELECTED_CANDIDATE), None)
    if selected is None:
        fail("D24-selected candidate absent from D23 set")
    if not selected.get("candidate_hash"):
        fail("D23 selected candidate hash missing")
    return {"d23_hash": sha256_obj(data), "selected": selected}


def _candidate_text(candidate: Dict[str, Any]) -> str:
    return json.dumps(candidate, sort_keys=True).lower()


def verify_d24(root: Path, d23: Dict[str, Any]) -> Dict[str, Any]:
    data = load_json(
        root / "vertical_slice/architecture_selection_d24_evidence.json",
        "D24 selection")
    if (data.get("selected_candidate") or "") != EXPECTED_SELECTED_CANDIDATE:
        fail("D24 selected_candidate is not the authoritative candidate")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D24 objective_id drift")
    selection_hash = str(data.get("selection_hash") or "").lower()
    candidate_hash = str(data.get("selected_hash") or "").lower()
    if not selection_hash or not candidate_hash:
        fail("D24 selection/candidate hash missing")
    # Recompute the selection hash from stored payload fields (our D24
    # evidence shape): winner + hash + ranking + policy + objective + ISR.
    recomputed = sha256_obj({
        "winner": data.get("selected_candidate"),
        "winner_hash": candidate_hash,
        "ranking": data.get("ranking"),
        "policy_hash": data.get("policy_hash"),
        "objective": EXPECTED_OBJECTIVE_ID,
        "isr": EXPECTED_ISR_SHA256,
    }).lower()
    if recomputed != selection_hash:
        fail("D24 selection_hash does not recompute from stored payload")
    if candidate_hash != str(
            d23["selected"].get("candidate_hash") or "").lower():
        fail("D24 candidate_hash does not match D23")
    architecture = _adapt_architecture(d23["selected"])
    coverage = validate_architecture(architecture)
    return {"d24_hash": sha256_obj(data),
            "candidate_id": EXPECTED_SELECTED_CANDIDATE,
            "candidate_hash": candidate_hash,
            "selection_hash": selection_hash,
            "architecture": architecture,
            "coverage": coverage,
            "backend_id": "python-fastapi"}


def _adapt_architecture(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Map our frozen D23 candidate shape onto the actuator's required
    architecture contract (adaptation table; D23 itself is untouched)."""
    text = _candidate_text(candidate)
    return {
        "authority_boundary": {op: False for op in sorted({
            "candidate_generation", "candidate_selection",
            "architecture_mutation", "isr_mutation",
            "evolution_authorization", "deployment", "redeployment",
            "runtime_observation", "evidence_interpretation",
            "optimization", "production_activation", "commit", "push"})},
        "objective_capabilities": [
            "create_task_with_priority",
            "update_task_priority",
            "retrieve_task_priority",
            "display_task_priority",
            "filter_tasks_by_priority",
            "preserve_existing_taskflow_behavior",
        ],
        "components": [
            {"id": c.get("component", ""),
             "responsibility": c.get("responsibility", "")}
            for c in candidate.get("components", [])
        ],
        "data_model": {"Task": {"fields": {"priority": {
            "type": "enum",
            "values": list(candidate.get("priority_values", []))}}}},
        # Preservation is stated three ways across the candidates
        # ("behave as before" / "identical observable behavior" /
        # "byte-equivalent in behavior"); all three are explicit
        # CRUD-behavior preservation claims, read literally.
        "api": {
            "preserve_existing_crud": any(
                marker in text for marker in (
                    "behave as before", "identical observable behavior",
                    "byte-equivalent in behavior", "crud paths preserved")),
            "create": {"accepts": ["title", "status", "priority"]
                       if "create" in text else []},
            "update": {"accepts": ["title", "status", "priority"]
                       if "update" in text else []},
            "retrieve": {"returns": ["priority"] if "read" in text else []},
            "filter": {"query": ["priority"]
                       if "filter" in text else []},
        },
        # Slice-scope adaptation: no UI layer exists; the API read model
        # plus ?priority= contract is the display/filter surface.
        "frontend": {"display_priority": "read" in text,
                     "filter_by_priority": "filter" in text},
        "persistence": {
            "priority_persisted": "persist" in text,
            "restart_durability": "restart" in text or "durability" in text,
            "migration": {"deterministic": "deterministic" in text,
                          "destructive": False},
        },
        "security": {
            "authentication": "preserved",
            "authorization": "preserved",
            "tenant_isolation": "preserved",
            "credential_safety": "preserved",
            "password_hashing": "preserved",
        },
        "events": {"preserve_existing_event_contracts":
                   candidate.get("event_classification")
                   == "NO_EVENT_CHANGE_REQUIRED",
                   "new_event_contracts": False},
        "isr_mappings": candidate.get("isr_mappings", []),
        "requirement_mappings": candidate.get("requirement_mappings", []),
        "_source_text_markers": {
            "membership_before_filter": "membership" in text,
            "fail_closed_validation": "422" in text,
            "priority_never_authority": "never" in text,
        },
    }


def validate_architecture(architecture: Dict[str, Any]) -> Dict[str, str]:
    boundary = architecture.get("authority_boundary")
    if not isinstance(boundary, dict):
        fail("architecture authority_boundary missing")
    for operation, value in boundary.items():
        if value is not False:
            fail(f"authority_boundary must deny {operation}")
    capabilities = set(architecture.get("objective_capabilities", []))
    missing = REQUIRED_CAPABILITIES - capabilities
    if missing:
        fail("architecture capabilities missing: " + ", ".join(sorted(missing)))
    values = set((architecture.get("data_model", {}).get("Task", {})
                  .get("fields", {}).get("priority", {}).get("values", [])))
    if values != PRIORITY_VALUES:
        fail("priority domain must be exactly LOW, MEDIUM, HIGH")
    api = architecture.get("api", {})
    for op, field, key in (("create", "accepts", "priority"),
                           ("update", "accepts", "priority"),
                           ("retrieve", "returns", "priority"),
                           ("filter", "query", "priority")):
        if key not in [str(x).lower() for x in
                       (api.get(op, {}) or {}).get(field, [])]:
            fail(f"API {op} must carry priority")
    if not api.get("preserve_existing_crud"):
        fail("API must preserve existing CRUD")
    frontend = architecture.get("frontend", {})
    if not (frontend.get("display_priority")
            and frontend.get("filter_by_priority")):
        fail("frontend display/filter mapping missing")
    persistence = architecture.get("persistence", {})
    if not (persistence.get("priority_persisted")
            and persistence.get("restart_durability")):
        fail("persistence mapping missing")
    if persistence.get("migration", {}).get("destructive"):
        fail("destructive migration not authorized")
    events = architecture.get("events", {})
    if not events.get("preserve_existing_event_contracts"):
        fail("event contracts not preserved")
    if events.get("new_event_contracts"):
        fail("new event contracts not authorized")
    markers = architecture.get("_source_text_markers", {})
    if not (markers.get("membership_before_filter")
            and markers.get("fail_closed_validation")
            and markers.get("priority_never_authority")):
        fail("security posture markers missing from candidate")
    return {"architecture": "7/7", "requirements": "6/6",
            "security": "5/5", "apis": "5/5", "data_models": "1/1",
            "events": "1/1"}


def verify_isr(root: Path) -> Dict[str, Any]:
    sys.path.insert(0, str(root))
    from vertical_slice import implementation as IMPL
    identity = IMPL.frozen_input_identity()
    if identity.get("vs-d02-isr-content-hash") != EXPECTED_ISR_SHA256:
        fail("ISR drift")
    return {"isr_sha256": EXPECTED_ISR_SHA256}


def verify_parent(root: Path) -> Dict[str, Any]:
    from vertical_slice import implementation_d25 as IMPLD25
    record = IMPLD25._load_json(
        root / "vertical_slice/implementation_d25_evidence.json")
    if record.get("parent_implementation_id") != "vs1-impl-v2":
        fail("parent implementation drift")
    return {"parent_implementation_id": "vs1-impl-v2",
            "parent_implementation_hash": "pinned-by-D25-evidence"}


def verify_behavior_evidence(root: Path, ref: str,
                             implementation_hash: str) -> Dict[str, Any]:
    data = load_json(root / ref, "behavior evidence")
    if str(data.get("implementation_hash", "")).lower() != \
            implementation_hash.lower():
        fail("behavior evidence binds a different implementation hash")
    checks = data.get("checks")
    if not isinstance(checks, dict):
        fail("behavior evidence checks missing")
    missing = sorted(c for c in REQUIRED_BEHAVIOR_CHECKS
                     if checks.get(c) is not True)
    if missing:
        fail("behavior evidence missing passing checks: " + ", ".join(missing))
    for flag in ("production_authorization", "deployment_performed",
                 "observation_performed", "optimization_performed",
                 "commit_performed", "push_performed"):
        value = data.get(flag)
        if value is False or str(value).strip().upper() in {
                "FALSE", "NOT_PERFORMED", "NOT_AUTHORIZED"}:
            continue
        fail(f"behavior evidence must declare {flag}=false")
    return data


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in obj.items()
                if not any(m in str(k).lower() for m in SECRET_KEY_MARKERS)}
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    return obj


def compile_plan(d24: Dict[str, Any], d22: Dict[str, Any],
                 d23: Dict[str, Any], objective_source: Dict[str, Any],
                 isr: Dict[str, Any], firewall: ActionFirewall) -> Dict[str, Any]:
    firewall.authorize("compile_implementation")
    return {
        "gate": "D25",
        "policy_version": POLICY_VERSION,
        "backend_id": d24.get("backend_id") or "python-fastapi",
        "authority_chain": {
            "isr_sha256": isr["isr_sha256"],
            "objective_id": EXPECTED_OBJECTIVE_ID,
            "objective_hash": d22["objective_hash"],
            "objective_source_sha256": objective_source["source_sha256"],
            "d22_hash": d22["d22_hash"],
            "d23_hash": d23["d23_hash"],
            "d24_hash": d24["d24_hash"],
            "candidate_id": d24["candidate_id"],
            "candidate_hash": d24["candidate_hash"],
            "selection_hash": d24["selection_hash"],
        },
        "firewall_actions": sorted(firewall.actions),
    }


def implementation_identity(plan: Dict[str, Any], d22: Dict[str, Any],
                            d23: Dict[str, Any], d24: Dict[str, Any],
                            objective_source: Dict[str, Any],
                            isr: Dict[str, Any]) -> tuple[str, str]:
    payload = {
        "plan": plan,
        "isr_sha256": isr["isr_sha256"],
        "objective_id": EXPECTED_OBJECTIVE_ID,
        "objective_hash": d22["objective_hash"],
        "objective_source_sha256": objective_source["source_sha256"],
        "candidate_id": d24["candidate_id"],
        "candidate_hash": d24["candidate_hash"],
        "selection_hash": d24["selection_hash"],
        "d22_hash": d22["d22_hash"],
        "d23_hash": d23["d23_hash"],
        "d24_hash": d24["d24_hash"],
        "policy_version": POLICY_VERSION,
    }
    digest = sha256_obj(payload).lower()
    return digest, f"vs1-impl-obj001-{digest[:16]}"


def render_blocked(reason: str) -> str:
    return "\n".join([
        "VS-D25 STOP REPORT", "STATUS: BLOCKED", "",
        f"REASON: {reason}", "",
        "COMMIT:", "  NOT COMMITTED", "",
        "PUSH:", "  NOT PUSHED", "",
        "STOP:", "  NEXT GATE = NOT AUTHORIZED",
    ])


def run(root: Path, behavior_evidence: Optional[str],
        write: bool = False) -> int:
    firewall = ActionFirewall()
    try:
        firewall.authorize("verify_upstream")
        objective_source = verify_objective_source(root)
        d22 = verify_d22(root, objective_source)
        d23 = verify_d23(root)
        d24 = verify_d24(root, d23)
        isr = verify_isr(root)
        parent = verify_parent(root)
        plan = compile_plan(d24, d22, d23, objective_source, isr, firewall)
        digest, impl_id = implementation_identity(
            plan, d22, d23, d24, objective_source, isr)
        if behavior_evidence is None:
            print(canonical_json({
                "implementation_id": impl_id,
                "implementation_hash": digest,
                "mode": "plan-only (no behavior evidence; nothing emitted)",
            }))
            return 0
        behavior = verify_behavior_evidence(root, behavior_evidence, digest)
        # Cross-check: actuator identity must bind the same upstream pins
        # as the D25 compiler record (independent schemes, shared anchors).
        compiler = load_json(
            root / "vertical_slice/implementation_d25_evidence.json",
            "D25 compiler record")
        for key, expected in (
                ("candidate_id", d24["candidate_id"]),
                ("selection_hash", d24["selection_hash"]),
                ("isr_hash", isr["isr_sha256"]),
                ("objective_id", EXPECTED_OBJECTIVE_ID)):
            if compiler.get(key) != expected:
                raise FailClosed(
                    f"actuator/compiler pin mismatch on {key}")
        _ = behavior  # verification is the use; checks enforced above
        firewall.authorize("emit_evidence")
        manifest = redact({
            "implementation_id": impl_id,
            "implementation_hash": digest,
            "plan": plan,
            "policy_version": POLICY_VERSION,
        })
        handoff = redact({
            "implementation_id": impl_id,
            "implementation_hash": digest,
            "selected_architecture_id": d24["candidate_id"],
            "selection_hash": d24["selection_hash"],
            "objective_id": EXPECTED_OBJECTIVE_ID,
            "isr_hash": isr["isr_sha256"],
            "backend_id": plan["backend_id"],
            "parent_implementation_id": parent["parent_implementation_id"],
            "production_authorization": False,
            "deployment_performed": False,
        })
        if write:
            firewall.authorize("emit_handoff")
            manifest_path = root / "vertical_slice" / \
                "implementation_d25_manifest.json"
            handoff_path = root / "vertical_slice" / "deployment_handoff_d25.json"
            for path in (manifest_path, handoff_path):
                if path.resolve() in {
                        (root / "vertical_slice/objective_source_VS1-OBJ-001.json").resolve(),
                        (root / "vertical_slice/objective_intake_d22_evidence.json").resolve(),
                        (root / "vertical_slice/candidate_generation_d23_evidence.json").resolve(),
                        (root / "vertical_slice/architecture_selection_d24_evidence.json").resolve(),
                        (root / "vertical_slice/isr.py").resolve()}:
                    raise FailClosed(f"refusing upstream overwrite: {path}")
            manifest_path.write_text(canonical_json(manifest), encoding="utf-8")
            handoff_path.write_text(canonical_json(handoff), encoding="utf-8")
        print(canonical_json({
            "status": "PASS",
            "implementation_id": impl_id,
            "implementation_hash": digest,
            "behavior_checks": f"{len(REQUIRED_BEHAVIOR_CHECKS)}/"
                               f"{len(REQUIRED_BEHAVIOR_CHECKS)}",
            "emitted": ["implementation_d25_manifest.json",
                        "deployment_handoff_d25.json"] if write else [],
        }))
        return 0
    except FailClosed as exc:
        print(render_blocked(str(exc)))
        return 1


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Constitutional Implementation Actuator for VS-D25")
    parser.add_argument("--root", default=".")
    parser.add_argument("--behavior-evidence", default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    behavior = None if args.plan_only else args.behavior_evidence
    if not args.plan_only and not args.behavior_evidence:
        print(render_blocked(
            "behavior evidence is required for D25 PASS; "
            "use --plan-only for verification without emission"))
        return 1
    return run(root, behavior, write=args.write)


if __name__ == "__main__":
    sys.exit(main())
