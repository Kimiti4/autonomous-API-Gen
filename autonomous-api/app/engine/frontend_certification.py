"""Frontend contract equivalence and evidence-bound certification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .frontend_contracts import frontend_contract_manifest
from .frontend_ir import FrontendProjectIR
from .frontend_registry import FrontendCompilation


@dataclass(frozen=True)
class FrontendExecutionEvidence:
    artifact_sha256: str
    build_passed: bool
    unit_tests_passed: bool
    e2e_passed: bool
    build_log_sha256: str
    unit_test_log_sha256: str
    e2e_log_sha256: str
    workflow_run_id: str
    source_commit: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_sha256": self.artifact_sha256,
            "build_passed": self.build_passed,
            "unit_tests_passed": self.unit_tests_passed,
            "e2e_passed": self.e2e_passed,
            "build_log_sha256": self.build_log_sha256,
            "unit_test_log_sha256": self.unit_test_log_sha256,
            "e2e_log_sha256": self.e2e_log_sha256,
            "workflow_run_id": self.workflow_run_id,
            "source_commit": self.source_commit,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "FrontendExecutionEvidence":
        return cls(
            artifact_sha256=str(value.get("artifact_sha256", "")),
            build_passed=value.get("build_passed") is True,
            unit_tests_passed=value.get("unit_tests_passed") is True,
            e2e_passed=value.get("e2e_passed") is True,
            build_log_sha256=str(value.get("build_log_sha256", "")),
            unit_test_log_sha256=str(value.get("unit_test_log_sha256", "")),
            e2e_log_sha256=str(value.get("e2e_log_sha256", "")),
            workflow_run_id=str(value.get("workflow_run_id", "")),
            source_commit=str(value.get("source_commit", "")),
        )


@dataclass(frozen=True)
class FrontendCertification:
    target: str
    certified: bool
    checks: tuple[str, ...]
    findings: tuple[str, ...]

    def to_dict(self):
        return {
            "target": self.target,
            "certified": self.certified,
            "checks": list(self.checks),
            "findings": list(self.findings),
        }


def frontend_artifact_hash(compilation: FrontendCompilation) -> str:
    """Hash the exact compiler-emitted file set and contents, order-independently."""
    manifest = [
        {
            "path": str(getattr(artifact, "path", "")),
            "kind": str(getattr(artifact, "kind", "")),
            "content": str(getattr(artifact, "content", "")),
        }
        for artifact in compilation.artifacts
    ]
    payload = json.dumps(sorted(manifest, key=lambda item: item["path"]), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def certify_frontend_compiler(
    ir: FrontendProjectIR,
    compilation: FrontendCompilation,
    execution_evidence: FrontendExecutionEvidence | None = None,
) -> FrontendCertification:
    checks = (
        "compilation-success",
        "source-schema-preserved",
        "screen-contracts-preserved",
        "navigation-preserved",
        "authorization-preserved",
        "data-contracts-preserved",
        "actions-preserved",
        "accessibility-preserved",
        "configuration-preserved",
        "platform-requirements-preserved",
        "real-build-passed",
        "generated-unit-tests-passed",
        "browser-e2e-passed",
        "evidence-bound-to-exact-artifacts",
    )
    findings: list[str] = []
    if compilation.diagnostics:
        findings.extend(compilation.diagnostics)
    if compilation.source_schema_version != ir.schema_version:
        findings.append("compiler changed source schema identity")

    content = "\n".join(
        str(getattr(artifact, "content", "")) for artifact in compilation.artifacts
    )
    manifest = frontend_contract_manifest(ir)
    for screen in manifest["screens"]:
        if len(screen["actions"]) < 2:
            findings.append(f"missing screen action semantics: {screen['screen_id']}")
        if len(screen["accessibility_requirements"]) < 2:
            findings.append(f"missing screen accessibility semantics: {screen['screen_id']}")
        for key in ("screen_id", "route", "title"):
            if str(screen[key]) not in content:
                findings.append(f"missing screen contract field: {key}={screen[key]}")
        for key in ("data_contract", "authorization_policy"):
            value = screen[key]
            if value and value not in content:
                findings.append(f"missing screen semantic field: {key}={value}")
        for key in ("actions", "accessibility_requirements"):
            for value in screen[key]:
                if value not in content:
                    findings.append(f"missing {key} obligation: {value}")
        for binding in screen.get("action_bindings", []):
            for key in ("action_id", "api_operation_id", "method", "path"):
                if binding[key] not in content:
                    findings.append(f"missing action binding {key}: {binding[key]}")
            for field in binding["request_fields"]:
                if field not in content:
                    findings.append(f"missing bound request field: {field}")
            policy = binding["authorization_policy"]
            if policy and policy not in content:
                findings.append(f"missing action authorization policy: {policy}")
    for value in manifest["configuration_keys"] + manifest["platform_requirements"]:
        if value not in content:
            findings.append(f"missing frontend requirement: {value}")

    if execution_evidence is None:
        findings.append("missing real build, unit-test, and browser E2E execution evidence")
    else:
        expected_hash = frontend_artifact_hash(compilation)
        if execution_evidence.artifact_sha256 != expected_hash:
            findings.append("execution evidence is not bound to this exact frontend artifact set")
        for label, passed in (
            ("build", execution_evidence.build_passed),
            ("unit tests", execution_evidence.unit_tests_passed),
            ("browser E2E", execution_evidence.e2e_passed),
        ):
            if passed is not True:
                findings.append(f"{label} evidence did not pass")
        for label, digest in (
            ("build log", execution_evidence.build_log_sha256),
            ("unit-test log", execution_evidence.unit_test_log_sha256),
            ("E2E log", execution_evidence.e2e_log_sha256),
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                findings.append(f"missing or invalid {label} SHA-256")
        if not execution_evidence.workflow_run_id:
            findings.append("missing workflow run identity")
        if not execution_evidence.source_commit:
            findings.append("missing source commit identity")

    return FrontendCertification(compilation.target, not findings, checks, tuple(findings))


def compare_frontend_contracts(
    ir: FrontendProjectIR,
    left: FrontendCompilation,
    right: FrontendCompilation,
) -> FrontendCertification:
    findings: list[str] = []
    if left.source_schema_version != right.source_schema_version:
        findings.append("target schema versions differ")
    left_content = "\n".join(str(getattr(a, "content", "")) for a in left.artifacts)
    right_content = "\n".join(str(getattr(a, "content", "")) for a in right.artifacts)
    manifest = frontend_contract_manifest(ir)
    values = []
    for screen in manifest["screens"]:
        values.extend([screen["screen_id"], screen["route"], screen["title"]])
        values.extend(value for value in (screen["data_contract"], screen["authorization_policy"]) if value)
        values.extend(screen["actions"])
        values.extend(screen["accessibility_requirements"])
        for binding in screen.get("action_bindings", []):
            values.extend([binding["action_id"], binding["api_operation_id"], binding["method"], binding["path"]])
            values.extend(binding["request_fields"])
            if binding["authorization_policy"]:
                values.append(binding["authorization_policy"])
    values.extend(manifest["configuration_keys"])
    values.extend(manifest["platform_requirements"])
    for value in values:
        if value not in left_content:
            findings.append(f"left target missing contract value: {value}")
        if value not in right_content:
            findings.append(f"right target missing contract value: {value}")
    return FrontendCertification(
        f"{left.target}↔{right.target}",
        not findings,
        ("cross-target-contract-equivalence",),
        tuple(findings),
    )
