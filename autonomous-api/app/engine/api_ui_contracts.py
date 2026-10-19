"""End-to-end API/UI contract verification (CAP-004 foundation).

The verifier compares semantic contracts, not generated source syntax. It is
intentionally independent of React, FastAPI, Express, or any future target.
"""
from __future__ import annotations
from dataclasses import dataclass
from .backend_contracts import contract_manifest
from .backend_ir import BackendProjectIR
from .frontend_contracts import frontend_contract_manifest
from .frontend_ir import FrontendProjectIR


@dataclass(frozen=True)
class FullStackContractVerification:
    compatible: bool
    checks: tuple[str, ...]
    findings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"compatible": self.compatible, "checks": list(self.checks), "findings": list(self.findings)}


def verify_api_ui_contract(
    backend: BackendProjectIR,
    frontend: FrontendProjectIR,
) -> FullStackContractVerification:
    checks = (
        "route-operation-alignment",
        "http-method-alignment",
        "request-schema-alignment",
        "response-schema-alignment",
        "authorization-alignment",
        "api-contract-version-alignment",
        "explicit-action-operation-binding",
    )
    findings: list[str] = []
    bm = contract_manifest(backend)
    fm = frontend_contract_manifest(frontend)

    if not frontend.api_contract_version:
        findings.append("frontend API contract version is missing")

    operations = {(x["method"], x["path"]): x for x in bm["operations"]}
    for screen in fm["screens"]:
        # A screen route is only required to map to a backend operation when
        # its data contract/actions declare an API dependency. Navigation-only
        # screens remain valid without an endpoint.
        if not screen["data_contract"] and not screen["actions"]:
            continue
        matches = [x for x in bm["operations"] if x["path"] == screen["route"]]
        if not matches:
            findings.append(
                f"no backend operation for data/action screen: {screen['screen_id']} {screen['route']}"
            )
            continue
        if screen["authorization_policy"] and not any(
            x["authorization_policy"] == screen["authorization_policy"] for x in matches
        ):
            findings.append(
                f"authorization mismatch for screen: {screen['screen_id']}"
            )

    for screen in fm["screens"]:
        for binding in screen.get("action_bindings", []):
            operation = next(
                (item for item in bm["operations"] if item["operation"] == binding["api_operation_id"]),
                None,
            )
            if operation is None:
                findings.append(
                    f"action {binding['action_id']} references unknown API operation: {binding['api_operation_id']}"
                )
                continue
            if operation["method"].upper() != binding["method"].upper():
                findings.append(f"HTTP method mismatch for action: {binding['action_id']}")
            if operation["path"] != binding["path"]:
                findings.append(f"API path mismatch for action: {binding['action_id']}")
            if binding["authorization_policy"] and operation["authorization_policy"] != binding["authorization_policy"]:
                findings.append(f"authorization mismatch for action: {binding['action_id']}")

    # API version is a semantic compatibility declaration, not an assumption.
    if frontend.api_contract_version not in {
        bm["schema_version"],
        f"api-{bm['schema_version']}",
        "api-v1",
    }:
        findings.append(
            f"frontend API contract version {frontend.api_contract_version!r} "
            f"has no declared backend compatibility mapping"
        )

    return FullStackContractVerification(not findings, checks, tuple(findings))
