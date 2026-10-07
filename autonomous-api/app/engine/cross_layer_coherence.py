"""Cross-layer coherence checks for technology-neutral full-stack IR."""
from __future__ import annotations
from dataclasses import dataclass
from .api_ir import ApiContractIR
from .implementation_ir import BackendIR, FrontendIR


@dataclass(frozen=True)
class CoherenceFinding:
    code: str
    layer: str
    message: str


def verify_cross_layer_coherence(
    frontend: FrontendIR,
    api: ApiContractIR,
    backend: BackendIR,
) -> tuple[CoherenceFinding, ...]:
    findings: list[CoherenceFinding] = []
    if frontend.api_contract_id != api.contract_id:
        findings.append(CoherenceFinding("FS-CONTRACT-001","frontend","API contract identity mismatch"))
    if backend.api_contract_id != api.contract_id:
        findings.append(CoherenceFinding("FS-CONTRACT-002","backend","API contract identity mismatch"))

    api_paths = {o.path for o in api.operations}
    for route in frontend.routes:
        if route not in api_paths:
            findings.append(CoherenceFinding("FS-CONTRACT-003","frontend",f"route has no API operation: {route}"))

    frontend_boundaries = set(frontend.security_boundaries)
    backend_boundaries = set(backend.security_boundaries)
    if frontend_boundaries and not backend_boundaries:
        findings.append(CoherenceFinding("FS-SEC-001","backend","frontend declares security boundary but backend declares none"))

    backend_flow_ids = {f.flow_id for f in backend.data_flows}
    if backend.data_flows:
        for flow in frontend.data_flows:
            if flow.contract == api.contract_id and flow.flow_id not in backend_flow_ids:
                findings.append(CoherenceFinding("FS-FLOW-001","system",f"frontend flow lacks backend flow identity: {flow.flow_id}"))

    for op in api.operations:
        if op.idempotency_required and op.method.upper() in {"POST","PUT","PATCH"}:
            if not any("idempot" in x.lower() for x in backend.failure_modes + backend.observability_requirements):
                findings.append(CoherenceFinding("FS-EFFECT-001","backend",f"idempotent API operation lacks backend idempotency evidence: {op.operation_id}"))

    return tuple(findings)
