"""Frontend contract equivalence and certification."""
from __future__ import annotations
from dataclasses import dataclass
from .frontend_contracts import frontend_contract_manifest
from .frontend_ir import FrontendProjectIR
from .frontend_registry import FrontendCompilation


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


def certify_frontend_compiler(
    ir: FrontendProjectIR, compilation: FrontendCompilation
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
    )
    findings: list[str] = []
    if compilation.diagnostics:
        findings.extend(compilation.diagnostics)
    if compilation.source_schema_version != ir.schema_version:
        findings.append("compiler changed source schema identity")

    content = "\n".join(
        str(getattr(a, "content", "")) for a in compilation.artifacts
    )
    manifest = frontend_contract_manifest(ir)
    for screen in manifest["screens"]:
        if len(screen["actions"]) < 2:
            findings.append(f"missing screen action semantics: {screen['screen_id']}")
        if len(screen["accessibility_requirements"]) < 2:
            findings.append(
                f"missing screen accessibility semantics: {screen['screen_id']}"
            )
        for key in ("screen_id", "route", "title"):
            if screen[key] not in content:
                findings.append(f"missing screen contract field: {key}={screen[key]}")
        for key in ("data_contract", "authorization_policy"):
            value = screen[key]
            if value and value not in content:
                findings.append(f"missing screen semantic field: {key}={value}")
        for key in ("actions", "accessibility_requirements"):
            for value in screen[key]:
                if value not in content:
                    findings.append(f"missing {key} obligation: {value}")
    for value in manifest["configuration_keys"] + manifest["platform_requirements"]:
        if value not in content:
            findings.append(f"missing frontend requirement: {value}")

    return FrontendCertification(
        compilation.target, not findings, checks, tuple(findings)
    )


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
    for s in manifest["screens"]:
        values.extend([s["screen_id"], s["route"], s["title"]])
        values.extend(x for x in (s["data_contract"], s["authorization_policy"]) if x)
        values.extend(s["actions"])
        values.extend(s["accessibility_requirements"])
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
