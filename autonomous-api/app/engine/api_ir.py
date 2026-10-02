"""CAP-004 API contract IR with structural schema bindings."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .schema_ir import SchemaIR, validate_schema

@dataclass(frozen=True)
class ApiError:
    code: str
    status: int
    retryable: bool = False

@dataclass(frozen=True)
class ApiOperation:
    operation_id: str
    method: str
    path: str
    request_schema: str | None = None
    response_schema: str | None = None
    authorization_policy: str | None = None
    errors: tuple[ApiError, ...] = ()
    idempotency_required: bool = False
    paginated: bool = False
    version: str = "v1"
    def to_dict(self) -> dict[str, Any]:
        return {"operation_id": self.operation_id, "method": self.method.upper(), "path": self.path,
                "request_schema": self.request_schema, "response_schema": self.response_schema,
                "authorization_policy": self.authorization_policy, "errors": [e.__dict__ for e in self.errors],
                "idempotency_required": self.idempotency_required, "paginated": self.paginated, "version": self.version}

@dataclass(frozen=True)
class ApiContractIR:
    schema_version: str
    contract_id: str
    operations: tuple[ApiOperation, ...]
    global_error_contract: str
    auth_scheme: str | None = None
    schemas: tuple[SchemaIR, ...] = ()
    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "contract_id": self.contract_id,
                "operations": [o.to_dict() for o in self.operations],
                "global_error_contract": self.global_error_contract, "auth_scheme": self.auth_scheme,
                "schemas": [s.to_dict() for s in self.schemas]}

def validate_api_contract(ir: ApiContractIR) -> tuple[str, ...]:
    findings: list[str] = []
    if not ir.contract_id: findings.append("API contract_id is required")
    if not ir.global_error_contract: findings.append("global error contract is required")
    names = {s.name for s in ir.schemas}
    for schema in ir.schemas: findings.extend(validate_schema(schema))
    seen: set[tuple[str, str]] = set()
    for op in ir.operations:
        method = op.method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}: findings.append(f"unsupported HTTP method: {op.operation_id}")
        if not op.path.startswith("/"): findings.append(f"API path must be absolute: {op.operation_id}")
        key = (method, op.path)
        if key in seen: findings.append(f"duplicate API route: {method} {op.path}")
        seen.add(key)
        for ref in (op.request_schema, op.response_schema):
            if ref and ref not in names: findings.append(f"unknown schema reference {ref}: {op.operation_id}")
        for error in op.errors:
            if not 400 <= error.status <= 599: findings.append(f"invalid error status: {op.operation_id}")
            if not error.code: findings.append(f"error code is required: {op.operation_id}")
        if op.idempotency_required and method in {"GET", "DELETE"}: findings.append(f"idempotency requirement is invalid for {method}: {op.operation_id}")
        if op.paginated and method != "GET": findings.append(f"pagination is currently restricted to GET: {op.operation_id}")
    return tuple(findings)
