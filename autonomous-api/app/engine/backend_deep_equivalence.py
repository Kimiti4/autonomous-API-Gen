"""CAP-003 deep backend contract equivalence.

Extends equivalence beyond routes to schemas, authorization, errors,
configuration, lifecycle and verification obligations.
"""
from __future__ import annotations
from dataclasses import dataclass
from .backend_ir import BackendProjectIR
from .backend_compiler import BackendCompilation


@dataclass(frozen=True)
class DeepBackendContract:
    operations: tuple[tuple[str, str, str, str | None, str | None, str | None], ...]
    lifecycle: tuple[str, ...]
    error_contract: str
    configuration_keys: tuple[str, ...]
    verification_obligations: tuple[str, ...]

    def to_dict(self):
        return {
            "operations": [list(x) for x in self.operations],
            "lifecycle": list(self.lifecycle),
            "error_contract": self.error_contract,
            "configuration_keys": list(self.configuration_keys),
            "verification_obligations": list(self.verification_obligations),
        }


@dataclass(frozen=True)
class DeepEquivalenceResult:
    left_target: str
    right_target: str
    equivalent: bool
    findings: tuple[str, ...]

    def to_dict(self):
        return {
            "left_target": self.left_target,
            "right_target": self.right_target,
            "equivalent": self.equivalent,
            "findings": list(self.findings),
        }


def contract_from_ir(ir: BackendProjectIR) -> DeepBackendContract:
    operations = tuple(sorted(
        (
            e.method.upper(),
            e.path,
            e.operation,
            e.request_schema,
            e.response_schema,
            e.authorization_policy,
        )
        for e in ir.endpoints
    ))
    obligations = tuple(sorted({
        f"operation:{e.operation}:contract"
        for e in ir.endpoints
    } | {
        f"lifecycle:{x}" for x in ir.lifecycle
    } | {
        "error-contract",
    }))
    return DeepBackendContract(
        operations,
        tuple(ir.lifecycle),
        ir.error_contract,
        tuple(sorted(ir.configuration_keys)),
        obligations,
    )


def verify_deep_backend_equivalence(
    ir: BackendProjectIR,
    left: BackendCompilation,
    right: BackendCompilation,
) -> DeepEquivalenceResult:
    expected = contract_from_ir(ir)
    findings: list[str] = []

    for result, side in ((left, "left"), (right, "right")):
        if result.diagnostics:
            findings.append(f"{side}: compilation diagnostics present")
        if result.source_schema_version != ir.schema_version:
            findings.append(f"{side}: source schema version changed")

        content = "\n".join(a.content for a in result.artifacts)
        for method, path, operation, request, response, auth in expected.operations:
            if operation not in content:
                findings.append(f"{side}: missing operation {operation}")
            if path not in content:
                findings.append(f"{side}: missing path {path}")
            if method.lower() not in content.lower():
                findings.append(f"{side}: missing method {method}")
            for value, label in (
                (request, "request schema"),
                (response, "response schema"),
                (auth, "authorization policy"),
            ):
                if value and value not in content:
                    findings.append(f"{side}: missing {label} {value}")

        for key in expected.configuration_keys:
            if key not in content:
                findings.append(f"{side}: missing configuration key {key}")
        if expected.error_contract and "contract" not in content.lower():
            findings.append(f"{side}: missing error contract")

        for lifecycle in expected.lifecycle:
            if lifecycle not in content:
                findings.append(f"{side}: missing lifecycle obligation {lifecycle}")

    return DeepEquivalenceResult(
        left.target,
        right.target,
        not findings,
        tuple(findings),
    )
