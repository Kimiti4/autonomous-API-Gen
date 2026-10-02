"""CAP-003 backend compiler certification.

A compiler is certified only when compilation succeeds and its generated
artifacts preserve the complete semantic contract manifest. This is a bounded
compiler certification, not a claim that generated code is production-safe.
"""
from __future__ import annotations
from dataclasses import dataclass
from .backend_contracts import contract_manifest
from .backend_deep_equivalence import verify_deep_backend_equivalence
from .backend_ir import BackendProjectIR
from .backend_compiler import BackendCompilation


@dataclass(frozen=True)
class CompilerCertification:
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


def certify_compiler(ir: BackendProjectIR, compilation: BackendCompilation) -> CompilerCertification:
    checks = (
        "compilation-success",
        "source-schema-preserved",
        "operation-contracts-preserved",
        "configuration-contract-preserved",
        "lifecycle-contract-preserved",
        "error-contract-preserved",
    )
    findings: list[str] = []
    if compilation.diagnostics:
        findings.extend(compilation.diagnostics)
    if compilation.source_schema_version != ir.schema_version:
        findings.append("compiler changed source schema identity")

    content = "\n".join(a.content for a in compilation.artifacts)
    manifest = contract_manifest(ir)
    for operation in manifest["operations"]:
        for key in ("operation", "path", "method"):
            value = operation[key]
            if value and str(value).lower() not in content.lower():
                findings.append(f"missing operation contract field: {key}={value}")
        for key in ("request_schema", "response_schema", "authorization_policy"):
            value = operation[key]
            if value and value not in content:
                findings.append(f"missing endpoint semantic field: {key}={value}")
    for key in manifest["configuration_keys"]:
        if key not in content:
            findings.append(f"missing configuration key: {key}")
    if manifest["error_contract"] and "contract" not in content.lower():
        findings.append("missing error contract")
    for lifecycle in manifest["lifecycle"]:
        if lifecycle not in content:
            findings.append(f"missing lifecycle obligation: {lifecycle}")

    return CompilerCertification(
        compilation.target,
        not findings,
        checks,
        tuple(findings),
    )


def certify_cross_target_equivalence(
    ir: BackendProjectIR,
    left: BackendCompilation,
    right: BackendCompilation,
) -> CompilerCertification:
    result = verify_deep_backend_equivalence(ir, left, right)
    checks = ("cross-target-deep-equivalence",)
    return CompilerCertification(
        f"{left.target}↔{right.target}",
        result.equivalent,
        checks,
        result.findings,
    )
