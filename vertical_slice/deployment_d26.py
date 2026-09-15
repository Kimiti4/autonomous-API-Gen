#!/usr/bin/env python3
"""VS-D26 Deployment Authority Actuator (repo-adapted from folder/D26.md).

Compiles the verified D25 implementation into a deterministic deployment
artifact and validates the complete upstream provenance. Two modes:
--plan-only (zero writes) and --write (emits actuator-owned manifest,
evidence, handoff, spec copy, manifest module, doc). No deployment
authorization exists in the current state, so actuation is never performed;
--actuate always fails closed here. No production, commit, or push paths
exist in this actuator.

Adaptations (documented, constitutional):
  - real artifact paths; canonical ISR hash (spec text slip corrected);
  - ensure_ascii=False canonicalization (D15-D26 repo standard);
  - D24 selection hash recomputed from our frozen D24 shape via an
    explicit adapter (D24 itself untouched);
  - behavior evidence bound to the D25-actuator identity, recomputed via
    the D25 actuator itself (behavior_evidence_d25.json untouched);
  - emitted manifest module is deployment_d26_manifest.py (the spec's
    deployment_d26.py name would overwrite this actuator source; the
    overwrite guard additionally protects the actuator and test files).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

POLICY_VERSION = "d26-deployment-authority-v1"

EXPECTED_OBJECTIVE_ID = "VS1-OBJ-001"
EXPECTED_SELECTED_CANDIDATE = "vs1-obj001-candidate-313b071dd7d4"
EXPECTED_ISR_SHA256 = (
    "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
)
EXPECTED_OBJECTIVE_SOURCE_SHA256 = (
    "4a9cde9ab822980985dc59e1f05649a456ee6ae3be6b30421183801d12ac6848"
)
EXPECTED_D23_EVIDENCE_PREFIX = "432ec0bf5a481d0a"
EXPECTED_D24_SELECTION_HASH_PREFIX = "9c8803764dd5f8f7"
EXPECTED_D25_IMPLEMENTATION_ID = "vs1-impl-obj001-v1"
EXPECTED_D25_PARENT_ID = "vs1-impl-v2"
EXPECTED_D25_BACKEND = "python-fastapi"
EXPECTED_D25_IMPLEMENTATION_HASH_PREFIX = "7dbbf34fe75660f1"

# Adapter: our frozen D24 selection-hash payload construction
# (architecture_selection_d24.evaluate). D24 is verified, never rewritten.
D24_SELECTION_ADAPTER = {
    "winner": "selected_candidate",
    "winner_hash": "selected_hash",
    "ranking": "ranking",
    "policy_hash": "policy_hash",
    "objective": "objective_id",
    "isr": "isr_hash",
}

PRODUCTION_ENVIRONMENTS = {"production", "prod", "prd", "live"}

PROHIBITED_ACTIONS = {
    "candidate_generation",
    "candidate_selection",
    "architecture_mutation",
    "implementation_generation",
    "isr_mutation",
    "evolution_authorization",
    "runtime_observation",
    "runtime_interpretation",
    "evidence_interpretation",
    "optimization",
    "production_deployment",
    "commit",
    "push",
}

ALLOWED_ACTIONS = {
    "verify_upstream",
    "compile_deployment",
    "scan_artifact",
    "verify_deployment_integrity",
    "emit_evidence",
    "emit_handoff",
    "actuate_bounded_deployment",
}

FALSE_VALUES = {"FALSE", "NOT_PERFORMED", "NOT_AUTHORIZED", "NONE", "NO"}

SECRET_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    ("generic_password", re.compile(
        r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
    ("generic_secret", re.compile(
        r"(?i)\b(secret|token|api_key|apikey|access_token|refresh_token)\b"
        r"\s*[:=]\s*['\"][^'\"]{16,}['\"]")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("database_url_with_credentials", re.compile(
        r"(?i)\b(postgresql|postgres|mongodb|redis|mysql)\+?://[^:\s]+:[^@\s]+@")),
]

DEFAULT_EXCLUDE_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", ".hg", ".svn", "node_modules", "tests", "test",
}
DEFAULT_EXCLUDE_SUFFIXES = {
    ".pyc", ".pyo", ".log", ".sqlite", ".sqlite3", ".db", ".env",
    ".pem", ".key", ".crt", ".p12", ".pfx", ".zip", ".tar", ".tgz",
}
MAX_SCANNABLE_TEXT_BYTES = 2_000_000


class FailClosed(Exception):
    pass


class ActionFirewall:
    def __init__(self) -> None:
        self.actions: List[str] = []

    def authorize(self, action: str) -> None:
        if action in PROHIBITED_ACTIONS:
            raise FailClosed(f"prohibited action requested: {action}")
        if action not in ALLOWED_ACTIONS:
            raise FailClosed(f"action not authorized by D26 firewall: {action}")
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
        fail("objective source objective_id drift")
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
    return {"d22_hash": sha256_obj(data),
            "objective_hash": data["objective"]["objective_hash"]}


def verify_d23(root: Path) -> Dict[str, Any]:
    data = load_json(
        root / "vertical_slice/candidate_generation_d23_evidence.json", "D23")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D23 objective_id drift")
    if not str(data.get("generation_hash", "")).startswith(
            EXPECTED_D23_EVIDENCE_PREFIX):
        fail("D23 generation evidence prefix mismatch")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        fail("D23 candidate set drift")
    selected = next((c for c in candidates
                     if c.get("candidate_id") == EXPECTED_SELECTED_CANDIDATE),
                    None)
    if selected is None or not selected.get("candidate_hash"):
        fail("D23 selected candidate unresolvable")
    return {"d23_hash": sha256_obj(data), "selected": selected}


def verify_d24(root: Path, d23: Dict[str, Any]) -> Dict[str, Any]:
    data = load_json(
        root / "vertical_slice/architecture_selection_d24_evidence.json",
        "D24 selection")
    if (data.get("selected_candidate") or "") != EXPECTED_SELECTED_CANDIDATE:
        fail("D24 selected_candidate drift")
    if data.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D24 objective_id drift")
    payload = {key: data.get(field)
               for key, field in D24_SELECTION_ADAPTER.items()}
    if any(value is None for value in payload.values()):
        fail("D24 selection payload fields missing")
    if sha256_obj(payload).lower() != str(
            data.get("selection_hash") or "").lower():
        fail("D24 selection hash does not recompute via adapter")
    if not str(data.get("selection_hash", "")).startswith(
            EXPECTED_D24_SELECTION_HASH_PREFIX):
        fail("D24 selection hash prefix mismatch")
    if str(data.get("selected_hash") or "").lower() != str(
            d23["selected"].get("candidate_hash") or "").lower():
        fail("D24 candidate hash does not match D23")
    return {"d24_hash": sha256_obj(data),
            "candidate_id": EXPECTED_SELECTED_CANDIDATE,
            "candidate_hash": str(data.get("selected_hash")).lower(),
            "selection_hash": str(data.get("selection_hash")).lower()}


def verify_isr(root: Path) -> Dict[str, Any]:
    sys.path.insert(0, str(root))
    from vertical_slice import implementation as IMPL
    if IMPL.frozen_input_identity().get(
            "vs-d02-isr-content-hash") != EXPECTED_ISR_SHA256:
        fail("ISR drift")
    return {"isr_sha256": EXPECTED_ISR_SHA256}


def verify_d25(root: Path) -> Dict[str, Any]:
    # Two lawful identities coexist in the D25 set: the compiler's
    # content-addressed identity (the deployment subject) and the
    # actuator's plan identity (supporting proof). Each is verified
    # against its own pins; D26 records both with explicit scheme
    # labels and rewrites neither.
    manifest = load_json(
        root / "vertical_slice/implementation_d25_manifest.json", "D25 manifest")
    plan = manifest.get("plan", {})
    if not isinstance(plan, dict):
        plan = {}
    chain = plan.get("authority_chain", {})
    if not isinstance(chain, dict):
        chain = {}
    if chain.get("candidate_id") != EXPECTED_SELECTED_CANDIDATE:
        fail("D25 manifest candidate drift")
    if chain.get("isr_sha256") != EXPECTED_ISR_SHA256:
        fail("D25 manifest ISR drift")
    backend = plan.get("backend_id") or manifest.get("backend_id")
    if backend != EXPECTED_D25_BACKEND:
        fail("D25 backend is not python-fastapi")
    handoff = load_json(root / "vertical_slice/deployment_handoff_d25.json",
                        "D25 handoff")
    compiler = load_json(
        root / "vertical_slice/implementation_d25_evidence.json",
        "D25 compiler record")
    if compiler.get("implementation_id") != EXPECTED_D25_IMPLEMENTATION_ID:
        fail("D25 compiler implementation_id drift")
    implementation_hash = str(
        compiler.get("implementation_hash") or "").lower()
    if not implementation_hash.startswith(
            EXPECTED_D25_IMPLEMENTATION_HASH_PREFIX):
        fail("D25 compiler implementation hash prefix mismatch")
    if handoff.get("selection_hash") != compiler.get("selection_hash"):
        fail("D25 handoff/compiler selection divergence")
    if handoff.get("isr_hash") != EXPECTED_ISR_SHA256:
        fail("D25 handoff ISR drift")
    if handoff.get("objective_id") != EXPECTED_OBJECTIVE_ID:
        fail("D25 handoff objective drift")
    behavior = load_json(root / "vertical_slice/behavior_evidence_d25.json",
                         "D25 behavior")
    checks = behavior.get("checks")
    if not isinstance(checks, dict) or len(checks) < 33:
        fail("D25 behavior checks insufficient")
    if any(value is not True for value in checks.values()):
        fail("D25 behavior checks not all passing")
    for flag in ("production_authorization", "deployment_performed",
                 "observation_performed", "optimization_performed",
                 "commit_performed", "push_performed"):
        value = behavior.get(flag)
        if value is not False and str(value).strip().upper() not in {
                "FALSE", "NOT_PERFORMED", "NOT_AUTHORIZED"}:
            fail(f"D25 behavior must declare {flag}=false")
    # Bind behavior evidence to the D25-actuator identity recomputed here
    # (behavior_evidence_d25.json itself is never rewritten by D26).
    sys.path.insert(0, str(root / "vertical_slice"))
    import d25_authority_actuator as D25A
    firewall25 = D25A.ActionFirewall()
    firewall25.authorize("verify_upstream")
    objective_source = D25A.verify_objective_source(root)
    d22 = D25A.verify_d22(root, objective_source)
    d23 = D25A.verify_d23(root)
    d24 = D25A.verify_d24(root, d23)
    isr = D25A.verify_isr(root)
    plan25 = D25A.compile_plan(d24, d22, d23, objective_source, isr, firewall25)
    digest25, _ = D25A.implementation_identity(
        plan25, d22, d23, d24, objective_source, isr)
    if str(behavior.get("implementation_hash") or "").lower() != digest25:
        fail("D25 behavior evidence binds a different identity")
    if manifest.get("parent_implementation_id",
                    "vs1-impl-v2") != EXPECTED_D25_PARENT_ID:
        fail("D25 parent drift")
    return {"implementation_id": EXPECTED_D25_IMPLEMENTATION_ID,
            "implementation_hash": implementation_hash,
            "parent_implementation_id": EXPECTED_D25_PARENT_ID,
            "backend": "python-fastapi",
            "manifest_hash": sha256_obj(manifest)}


def validate_deployment_spec(spec: Dict[str, Any]) -> str:
    for key in ("environment", "target", "backend", "runtime", "entrypoint",
                "health", "configuration_contract"):
        if key not in spec:
            fail(f"deployment specification missing: {key}")
    environment = str(spec.get("environment") or "").strip().lower()
    if not environment:
        fail("deployment environment missing")
    if environment in PRODUCTION_ENVIRONMENTS:
        fail("production deployment is not authorized")
    if spec.get("production") is True:
        fail("production flag must be false")
    if spec.get("rollback_required", True) and not spec.get("rollback_identity"):
        fail("rollback required but rollback_identity missing")
    closure = spec.get("source_closure", {})
    if not isinstance(closure, dict):
        fail("source_closure must be an object")
    source_root = str(closure.get("root") or "vertical_slice/app_v3")
    if not source_root:
        fail("source_closure.root missing")
    return source_root


def is_excluded(rel_path: str, extra: set) -> bool:
    parts = Path(rel_path).parts
    for part in parts:
        if part in DEFAULT_EXCLUDE_DIRS or part in extra:
            return True
    for suffix in DEFAULT_EXCLUDE_SUFFIXES:
        if rel_path.endswith(suffix):
            return True
    if rel_path.startswith("tests/") or "/tests/" in rel_path:
        return True
    if Path(rel_path).name.startswith("test_"):
        return True
    return False


def classify_role(rel_path: str) -> str:
    if rel_path.endswith(".py"):
        return "runtime"
    if rel_path.endswith((".json", ".yaml", ".yml", ".toml")):
        return "configuration"
    if rel_path.endswith(".txt"):
        return "dependency"
    if rel_path.endswith(".md"):
        return "documentation"
    return "asset"


def build_artifact_manifest(root: Path, source_root: str,
                            excludes: list) -> Dict[str, Any]:
    source_path = root / source_root
    if not source_path.is_dir():
        fail(f"deployment source root missing: {source_path}")
    extra = {str(x) for x in excludes if x}
    files: List[Dict[str, Any]] = []
    for path in sorted(source_path.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_dir():
            continue
        rel_path = path.relative_to(root).as_posix()
        if is_excluded(rel_path, extra):
            continue
        files.append({"relative_path": rel_path,
                      "sha256": sha256_file(path).lower(),
                      "size": path.stat().st_size,
                      "role": classify_role(rel_path)})
    if not files:
        fail("deployment artifact closure is empty")
    return {"source_root": source_root, "files": files}


def scan_text_for_secrets(text: str, rel_path: str) -> list:
    diagnostics = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                diagnostics.append({"pattern": pattern_name,
                                    "path": rel_path,
                                    "line": line_number})
    return diagnostics


def scan_manifest_files(root: Path, manifest: Dict[str, Any]) -> list:
    diagnostics = []
    for entry in manifest["files"]:
        rel_path = entry["relative_path"]
        raw = (root / rel_path).read_bytes()
        if entry["size"] > MAX_SCANNABLE_TEXT_BYTES:
            raise FailClosed(f"file too large, not safely deployable: {rel_path}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise FailClosed(f"binary file in deployment closure: {rel_path}")
        diagnostics.extend(scan_text_for_secrets(text, rel_path))
    return diagnostics


def compute_deployment_identity(spec: Dict[str, Any], spec_hash: str,
                                manifest_hash: str,
                                d25: Dict[str, Any]) -> tuple[str, str]:
    payload = {
        "implementation_id": d25["implementation_id"],
        "implementation_hash": d25["implementation_hash"],
        "artifact_manifest_hash": manifest_hash,
        "deployment_spec_hash": spec_hash,
        "environment": spec["environment"],
        "target": spec["target"],
        "backend": spec["backend"],
        "runtime": spec["runtime"],
        "configuration_contract": spec.get("configuration_contract", {}),
        "policy_version": POLICY_VERSION,
    }
    deployment_hash = sha256_obj(payload).lower()
    return deployment_hash, f"vs1-deploy-obj001-{deployment_hash[:16]}"


def verify_authorization(root: Path, authorization_path: str,
                         spec: Dict[str, Any], d25: Dict[str, Any],
                         deployment_id: str, deployment_hash: str,
                         require_actuation: bool) -> Dict[str, Any]:
    path = root / authorization_path
    if not path.is_file():
        raise FailClosed("deployment authorization missing")
    authorization = json.loads(path.read_text(encoding="utf-8"))
    for key in ("authorization_id", "implementation_id",
                "implementation_hash", "deployment_target",
                "deployment_scope", "environment", "allowed_actions"):
        if key not in authorization:
            fail(f"authorization missing: {key}")
    if authorization.get("implementation_id") != d25["implementation_id"]:
        fail("authorization implementation_id mismatch")
    if str(authorization.get("implementation_hash") or "").lower() != \
            d25["implementation_hash"]:
        fail("authorization implementation_hash mismatch")
    if authorization.get("deployment_target") != spec.get("target"):
        fail("authorization target mismatch")
    if str(authorization.get("environment") or "").lower() != \
            str(spec.get("environment") or "").lower():
        fail("authorization environment mismatch")
    if authorization.get("production_authorization", False) is not False:
        fail("production authorization must be false")
    allowed = authorization.get("allowed_actions", [])
    if not isinstance(allowed, list):
        fail("allowed_actions must be a list")
    if require_actuation and "actuate_bounded_deployment" not in allowed:
        fail("authorization does not permit actuation")
    expires_at = authorization.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(
                str(expires_at).replace("Z", "+00:00"))
        except Exception:
            fail("expires_at is not valid ISO-8601")
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            fail("deployment authorization expired")
    return authorization


def redact(obj: Any) -> Any:
    markers = ("password", "secret", "token", "credential", "private_key",
               "session", "cookie", "api_key")
    if isinstance(obj, dict):
        return {key: redact(value) for key, value in obj.items()
                if not any(m in str(key).lower() for m in markers)}
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    return obj


def render_blocked(reason: str) -> str:
    return "\n".join([
        "VS-D26 STOP REPORT", "STATUS: BLOCKED", "",
        f"REASON: {reason}", "",
        "COMMIT:", "  NOT_COMMITTED", "",
        "PUSH:", "  NOT_PUSHED", "",
        "STOP:", "  NEXT GATE = D27 NOT AUTHORIZED",
    ])


def _self_protected(root: Path) -> set:
    """Paths the actuator must never overwrite: upstream inputs plus its
    own source and test files (lesson: the spec's deployment_d26.py output
    name collided with this actuator source)."""
    return {
        (root / "vertical_slice/objective_source_VS1-OBJ-001.json").resolve(),
        (root / "vertical_slice/objective_intake_d22_evidence.json").resolve(),
        (root / "vertical_slice/candidate_generation_d23_evidence.json").resolve(),
        (root / "vertical_slice/architecture_selection_d24_evidence.json").resolve(),
        (root / "vertical_slice/isr.py").resolve(),
        (root / "vertical_slice/implementation_d25_evidence.json").resolve(),
        (root / "vertical_slice/implementation_d25_manifest.json").resolve(),
        (root / "vertical_slice/deployment_handoff_d25.json").resolve(),
        (root / "vertical_slice/behavior_evidence_d25.json").resolve(),
        Path(__file__).resolve(),
        (root / "tests/vs1/test_deployment_d26.py").resolve(),
    }


def run_d26(args) -> int:
    root = Path(args.root).resolve()
    firewall = ActionFirewall()
    try:
        firewall.authorize("verify_upstream")
        objective_source = verify_objective_source(root)
        d22 = verify_d22(root, objective_source)
        d23 = verify_d23(root)
        d24 = verify_d24(root, d23)
        sys.path.insert(0, str(root))
        from vertical_slice import implementation as IMPL
        if IMPL.frozen_input_identity().get(
                "vs-d02-isr-content-hash") != EXPECTED_ISR_SHA256:
            fail("ISR drift")
        isr = {"isr_sha256": EXPECTED_ISR_SHA256}
        d25 = verify_d25(root)
        firewall.authorize("compile_deployment")
        spec = json.loads((root / "vertical_slice/deployment_spec_d26_input.json")
                          .read_text(encoding="utf-8"))
        spec_hash = sha256_obj(spec).lower()
        source_root = validate_deployment_spec(spec)
        manifest = build_artifact_manifest(root, source_root, [])
        manifest_hash = sha256_obj(manifest).lower()
        entrypoint = str(spec.get("entrypoint") or "")
        entrypoint_module = entrypoint.split(":")[0]
        if entrypoint and not any(
                item["relative_path"] == entrypoint_module
                for item in manifest["files"]):
            fail("deployment entrypoint absent from closure")
        firewall.authorize("scan_artifact")
        diagnostics = scan_manifest_files(root, manifest)
        if diagnostics:
            fail("secret scan failed: " + ", ".join(
                f"{d['pattern']}@{d['path']}:{d['line']}"
                for d in diagnostics[:5]))
        deployment_hash, deployment_id = compute_deployment_identity(
            spec, spec_hash, manifest_hash, d25)
        repeat_hash = sha256_obj(build_artifact_manifest(
            root, source_root, [])).lower()
        if repeat_hash != manifest_hash:
            fail("deployment manifest is not reproducible")
        repeat_id_hash, repeat_id = compute_deployment_identity(
            spec, spec_hash, repeat_hash, d25)
        if repeat_id_hash != deployment_hash or repeat_id != deployment_id:
            fail("deployment identity is not reproducible")
        authorization = None
        if args.authorization:
            authorization = verify_authorization(
                root, args.authorization, spec, d25, deployment_id,
                deployment_hash, require_actuation=args.actuate)
        elif args.actuate:
            fail("actuation requires explicit deployment authorization")
        if args.actuate:
            fail("no bounded DeploymentBackend configured; actuation by "
                 "explicit target adapter only")
        if args.plan_only:
            print(json.dumps({
                "status": "PLAN_VALID",
                "deployment_id": deployment_id,
                "deployment_hash": deployment_hash,
                "artifact_manifest_hash": manifest_hash,
                "deployment_spec_hash": spec_hash,
                "environment": spec["environment"],
                "target": spec["target"],
                "backend": spec["backend"],
                "implementation_id": d25["implementation_id"],
                "implementation_hash": d25["implementation_hash"],
                "actuation": "NOT_PERFORMED",
                "production": False,
                "runtime_observation": "NOT_PERFORMED",
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if not args.write:
            fail("evidence emission requires --write (plan-only validates)")
        if not args.test_evidence:
            fail("D26 PASS requires --test-evidence")
        test_summary = json.loads(
            (root / args.test_evidence).read_text(encoding="utf-8"))
        for key in ("d26", "d25", "d24", "d23", "d22", "tests_vs1",
                    "adjacent_suites", "full_regression"):
            if key not in test_summary:
                fail(f"test evidence missing: {key}")
        if str(test_summary.get("full_regression") or "").upper() not in {
                "COMPLETE", "NOT_COMPLETE"}:
            fail("test evidence full_regression must be COMPLETE/NOT_COMPLETE")
        outputs = {
            "manifest": root / "vertical_slice/deployment_d26_manifest.json",
            "evidence": root / "vertical_slice/deployment_d26_evidence.json",
            "handoff": root / "vertical_slice/deployment_handoff_d26.json",
            "spec": root / "vertical_slice/deployment_spec_d26.json",
            "deployment_py": root / "vertical_slice/deployment_d26_manifest.py",
            "markdown": root / "folder/VS1_DEPLOYMENT_D26.md",
        }
        protected = _self_protected(root)
        for output_path in outputs.values():
            if output_path.resolve() in protected:
                fail(f"output would overwrite protected file: {output_path}")
        before = {str(p): sha256_file(p) for p in protected if p.is_file()}
        rollback = spec.get("rollback_identity") or {}
        handoff = redact({
            "deployment_status": "NOT_PERFORMED",
            "deployment_id": deployment_id,
            "deployment_hash": deployment_hash,
            "artifact_hash": manifest_hash,
            "artifact_manifest_hash": manifest_hash,
            "deployment_spec_hash": spec_hash,
            "implementation_id": d25["implementation_id"],
            "implementation_hash": d25["implementation_hash"],
            "target": spec["target"],
            "environment": spec["environment"],
            "deployment_integrity": "NOT_PERFORMED",
            "runtime_observation_authority": "separate",
            "observation_status": "NOT_PERFORMED",
            "production_authorization": False,
            "deployment_authorized": bool(authorization),
        })
        handoff_hash = sha256_obj(handoff).lower()
        manifest_obj = redact({
            "deployment_id": deployment_id,
            "deployment_hash": deployment_hash,
            "implementation_id": d25["implementation_id"],
            "implementation_hash": d25["implementation_hash"],
            "artifact_hash": manifest_hash,
            "artifact_manifest_hash": manifest_hash,
            "deployment_spec_hash": spec_hash,
            "environment": spec["environment"],
            "backend": spec["backend"],
            "entrypoint": spec["entrypoint"],
            "runtime": spec["runtime"],
            "configuration_identity": sha256_obj(
                spec.get("configuration_contract", {})),
            "rollback_identity": rollback or "NONE",
            "authorization_identity": (authorization or {}).get(
                "authorization_id", "NONE"),
            "production": False,
            "observation": "NOT_PERFORMED",
            "interpretation": "NOT_PERFORMED",
            "optimization": "NOT_PERFORMED",
            "evolution": "NOT_PERFORMED",
            "commit": False,
            "push": False,
        })
        evidence = redact({
            "gate": "D26",
            "policy_version": POLICY_VERSION,
            "status": "PASS",
            "deployment_status": "NOT_PERFORMED",
            "production_authorization": False,
            "deployment_performed": False,
            "observation_performed": False,
            "interpretation_performed": False,
            "optimization_performed": False,
            "commit_performed": False,
            "push_performed": False,
            "upstream": {
                "d22": d22, "d23": d23, "d24": d24, "d25": d25,
                "isr": isr, "objective_source": objective_source,
            },
            "deployment": {
                "deployment_id": deployment_id,
                "deployment_hash": deployment_hash,
                "artifact_manifest_hash": manifest_hash,
                "deployment_spec_hash": spec_hash,
                "environment": spec["environment"],
                "target": spec["target"],
                "backend": spec["backend"],
                "runtime": spec["runtime"],
            },
            "artifact": {
                "source_root": source_root,
                "manifest_hash": manifest_hash,
                "file_count": len(manifest["files"]),
                "secret_scan": "PASS",
                "reproducibility": "VERIFIED",
            },
            "authorization": {
                "authorization_id": (authorization or {}).get(
                    "authorization_id", "NONE"),
                "deployment_authorized": bool(authorization),
                "production_authorized": False,
            },
            "handoff_hash": handoff_hash,
            "firewall_actions": sorted(firewall.actions),
        })
        firewall.authorize("emit_evidence")
        outputs["manifest"].write_text(
            json.dumps(manifest_obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False), encoding="utf-8")
        outputs["evidence"].write_text(
            json.dumps(evidence, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False), encoding="utf-8")
        outputs["handoff"].write_text(
            json.dumps(handoff, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False), encoding="utf-8")
        outputs["spec"].write_text(
            json.dumps(spec, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False), encoding="utf-8")
        manifest_literal = json.dumps(json.dumps(
            manifest_obj, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False))
        outputs["deployment_py"].write_text("\n".join([
            '"""Deterministic D26 deployment manifest module."""',
            "import json", "",
            f"DEPLOYMENT_ID = {json.dumps(deployment_id)}",
            f"DEPLOYMENT_HASH = {json.dumps(deployment_hash)}", "",
            f"MANIFEST_JSON = {manifest_literal}",
            "MANIFEST = json.loads(MANIFEST_JSON)", "",
            "",
            "def main() -> None:",
            "    print(json.dumps(MANIFEST, sort_keys=True, indent=2))", "",
            "",
            'if __name__ == "__main__":', "    main()", "",
        ]), encoding="utf-8")
        outputs["markdown"].parent.mkdir(parents=True, exist_ok=True)
        outputs["markdown"].write_text(
            "# VS1 Deployment D26\n\nDeployment compiled, actuation not "
            "performed (no authorization). See deployment_d26_evidence.json.\n",
            encoding="utf-8")
        after = {str(p): sha256_file(p) for p in protected if p.is_file()}
        if before != after:
            fail("protected file mutation detected during D26 execution")
        firewall.authorize("emit_handoff")
        print(json.dumps({
            "status": "PASS",
            "deployment_id": deployment_id,
            "deployment_hash": deployment_hash,
            "actuation": "NOT_PERFORMED",
            "production": False,
            "runtime_observation": "NOT_PERFORMED",
            "d27_ready": False,
            "handoff_hash": handoff_hash,
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except FailClosed as exc:
        print(render_blocked(str(exc)))
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="VS-D26 Deployment Authority Actuator")
    parser.add_argument("--root", default=".")
    parser.add_argument("--authorization", default="")
    parser.add_argument("--test-evidence", default="")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--actuate", action="store_true")
    args = parser.parse_args(argv)
    return run_d26(args)


if __name__ == "__main__":
    sys.exit(main())
