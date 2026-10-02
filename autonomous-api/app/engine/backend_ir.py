"""CAP-003 technology-neutral backend compiler IR.

The backend IR is a compiler-owned representation. It is intentionally separate
from the ISR: selecting Python, Node, a framework, or a database is forbidden
at this layer.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BackendEndpoint:
    endpoint_id: str
    operation: str
    path: str
    method: str
    request_schema: str | None = None
    response_schema: str | None = None
    authorization_policy: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


@dataclass(frozen=True)
class BackendComponent:
    component_id: str
    kind: str
    responsibility: str
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | {"dependencies": list(self.dependencies)}


@dataclass(frozen=True)
class BackendProjectIR:
    schema_version: str
    architecture_id: str
    components: tuple[BackendComponent, ...]
    endpoints: tuple[BackendEndpoint, ...]
    configuration_keys: tuple[str, ...]
    error_contract: str
    lifecycle: tuple[str, ...]
    source_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "architecture_id": self.architecture_id,
            "components": [x.to_dict() for x in self.components],
            "endpoints": [x.to_dict() for x in self.endpoints],
            "configuration_keys": list(self.configuration_keys),
            "error_contract": self.error_contract,
            "lifecycle": list(self.lifecycle),
            "source_requirements": list(self.source_requirements),
        }


def validate_backend_ir(ir: BackendProjectIR) -> tuple[str, ...]:
    findings: list[str] = []
    ids = {c.component_id for c in ir.components}
    if not ir.components:
        findings.append("backend IR has no components")
    if not ir.error_contract.strip():
        findings.append("backend IR has no error contract")
    if not ir.lifecycle:
        findings.append("backend IR has no lifecycle contract")
    for endpoint in ir.endpoints:
        if not endpoint.path.startswith("/"):
            findings.append(f"endpoint path must be absolute: {endpoint.endpoint_id}")
        if endpoint.method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            findings.append(f"unsupported HTTP method: {endpoint.method}")
        if endpoint.authorization_policy and endpoint.authorization_policy not in ids:
            # Policy IDs are semantic references; this is a structural warning
            # only because policy ownership can be external to a backend component.
            findings.append(f"unresolved authorization reference: {endpoint.endpoint_id}")
    return tuple(findings)


def build_backend_ir(
    architecture_id: str,
    *,
    source_requirements: tuple[str, ...],
    endpoints: tuple[BackendEndpoint, ...] = (),
    components: tuple[BackendComponent, ...] = (
        BackendComponent("backend-domain", "domain", "execute domain behavior"),
        BackendComponent("backend-api", "interface", "expose application operations"),
    ),
    configuration_keys: tuple[str, ...] = (),
    error_contract: str = "stable machine-readable application errors",
    lifecycle: tuple[str, ...] = ("startup", "ready", "shutdown"),
) -> BackendProjectIR:
    return BackendProjectIR(
        "CAP-003-BackendIR.v1", architecture_id, components, endpoints,
        configuration_keys, error_contract, lifecycle, source_requirements,
    )
