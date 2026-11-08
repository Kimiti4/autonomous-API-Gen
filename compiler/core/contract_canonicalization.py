"""F-05 CanonicalApiContract canonical bytes (ADR-R1-02 Tier B)."""

from __future__ import annotations

import json

from compiler.core.canonical_api_contract import CanonicalApiContract


def canonical_bytes_f05(contract: CanonicalApiContract) -> bytes:
    """Same payload shape as contract_digest input (independent path)."""
    payload = {
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "auth_scheme": contract.auth_scheme,
        "operations": [
            {
                "operation_id": op.operation_id,
                "method": op.method,
                "path": op.path,
                "authorization_policy_ids": list(op.authorization_policy_ids),
                "idempotency_required": op.idempotency_required,
            }
            for op in contract.operations
        ],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
