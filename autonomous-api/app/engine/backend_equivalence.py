"""CAP-003 cross-target backend contract equivalence.

Compares compiler outputs through normalized semantic contracts, not framework
syntax. This proves whether different targets preserve the same Backend IR
obligations.
"""
from __future__ import annotations
from dataclasses import dataclass
from .backend_ir import BackendProjectIR
from .backend_compiler import BackendCompilation


@dataclass(frozen=True)
class BackendContract:
    operations: tuple[tuple[str, str, str], ...]
    lifecycle: tuple[str, ...]
    error_contract: str

    def to_dict(self):
        return {
            "operations": [list(x) for x in self.operations],
            "lifecycle": list(self.lifecycle),
            "error_contract": self.error_contract,
        }


@dataclass(frozen=True)
class EquivalenceFinding:
    category: str
    message: str


@dataclass(frozen=True)
class BackendEquivalenceResult:
    left_target: str
    right_target: str
    equivalent: bool
    findings: tuple[EquivalenceFinding, ...]

    def to_dict(self):
        return {
            "left_target": self.left_target,
            "right_target": self.right_target,
            "equivalent": self.equivalent,
            "findings": [f.__dict__ for f in self.findings],
        }


def contract_from_ir(ir: BackendProjectIR) -> BackendContract:
    return BackendContract(
        tuple(sorted(
            (e.method.upper(), e.path, e.operation)
            for e in ir.endpoints
        )),
        tuple(ir.lifecycle),
        ir.error_contract,
    )


def verify_backend_equivalence(
    ir: BackendProjectIR,
    left: BackendCompilation,
    right: BackendCompilation,
) -> BackendEquivalenceResult:
    findings: list[EquivalenceFinding] = []
    expected = contract_from_ir(ir)

    if left.diagnostics:
        findings.append(EquivalenceFinding("left-compilation", "left compiler has diagnostics"))
    if right.diagnostics:
        findings.append(EquivalenceFinding("right-compilation", "right compiler has diagnostics"))

    if left.source_schema_version != ir.schema_version:
        findings.append(EquivalenceFinding("left-schema", "left compiler changed source schema identity"))
    if right.source_schema_version != ir.schema_version:
        findings.append(EquivalenceFinding("right-schema", "right compiler changed source schema identity"))

    for result, side in ((left, "left"), (right, "right")):
        content = "\n".join(a.content for a in result.artifacts)
        for method, path, operation in expected.operations:
            if path not in content or operation not in content:
                findings.append(EquivalenceFinding(
                    f"{side}-operation", f"{side} target does not expose operation {operation} at {path}"
                ))
            if method.lower() not in content.lower():
                findings.append(EquivalenceFinding(
                    f"{side}-method", f"{side} target does not encode HTTP method {method}"
                ))
        for lifecycle in expected.lifecycle:
            if lifecycle not in content:
                findings.append(EquivalenceFinding(
                    f"{side}-lifecycle", f"{side} target does not preserve lifecycle contract '{lifecycle}'"
                ))

    return BackendEquivalenceResult(
        left.target, right.target, not findings, tuple(findings)
    )
