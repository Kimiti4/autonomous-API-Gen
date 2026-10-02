"""CAP-003 contract-aware backend target contract lowering.

This module defines the shared semantic lowering contract used by concrete
language/framework compilers. Technology-specific compilers remain separate.
"""
from __future__ import annotations
from dataclasses import dataclass
from .backend_ir import BackendProjectIR


@dataclass(frozen=True)
class LoweredEndpointContract:
    operation: str
    method: str
    path: str
    request_schema: str | None
    response_schema: str | None
    authorization_policy: str | None


def endpoint_contracts(ir: BackendProjectIR) -> tuple[LoweredEndpointContract, ...]:
    return tuple(
        LoweredEndpointContract(
            e.operation,
            e.method.upper(),
            e.path,
            e.request_schema,
            e.response_schema,
            e.authorization_policy,
        )
        for e in ir.endpoints
    )


def contract_manifest(ir: BackendProjectIR) -> dict:
    return {
        "schema_version": ir.schema_version,
        "operations": [
            {
                "operation": x.operation,
                "method": x.method,
                "path": x.path,
                "request_schema": x.request_schema,
                "response_schema": x.response_schema,
                "authorization_policy": x.authorization_policy,
            }
            for x in endpoint_contracts(ir)
        ],
        "configuration_keys": sorted(ir.configuration_keys),
        "lifecycle": list(ir.lifecycle),
        "error_contract": ir.error_contract,
    }
