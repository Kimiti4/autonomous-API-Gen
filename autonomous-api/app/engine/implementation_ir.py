"""Richer technology-neutral frontend/backend implementation IR."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .api_ir import ApiContractIR


@dataclass(frozen=True)
class ModuleIR:
    module_id: str
    responsibility: str
    dependencies: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataFlowIR:
    flow_id: str
    source: str
    destination: str
    contract: str
    failure_policy: str


@dataclass(frozen=True)
class BackendIR:
    schema_version: str
    contract_id: str
    domain_modules: tuple[str, ...]
    api_contract_id: str
    quality_obligation_ids: tuple[str, ...] = ()
    persistence_targets: tuple[str, ...] = ()
    event_targets: tuple[str, ...] = ()
    observability_requirements: tuple[str, ...] = ()
    modules: tuple[ModuleIR, ...] = ()
    data_flows: tuple[DataFlowIR, ...] = ()
    security_boundaries: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["modules"] = [{**m.__dict__, "invariants": list(m.invariants)} for m in self.modules]
        d["data_flows"] = [f.__dict__ for f in self.data_flows]
        return d


@dataclass(frozen=True)
class FrontendIR:
    schema_version: str
    contract_id: str
    routes: tuple[str, ...]
    api_contract_id: str
    quality_obligation_ids: tuple[str, ...] = ()
    state_domains: tuple[str, ...] = ()
    interaction_flows: tuple[str, ...] = ()
    accessibility_requirements: tuple[str, ...] = ()
    observability_requirements: tuple[str, ...] = ()
    modules: tuple[ModuleIR, ...] = ()
    data_flows: tuple[DataFlowIR, ...] = ()
    security_boundaries: tuple[str, ...] = ()
    failure_states: tuple[str, ...] = ()
    design_constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["modules"] = [m.__dict__ for m in self.modules]
        d["data_flows"] = [f.__dict__ for f in self.data_flows]
        return d


def backend_from_api(api: ApiContractIR, quality_obligation_ids: tuple[str, ...] = ()) -> BackendIR:
    domains = tuple(sorted({o.operation_id.split("_", 1)[0] for o in api.operations}))
    return BackendIR(api.schema_version, f"backend:{api.contract_id}", domains, api.contract_id, quality_obligation_ids)


def frontend_from_api(api: ApiContractIR, quality_obligation_ids: tuple[str, ...] = ()) -> FrontendIR:
    routes = tuple(sorted({o.path for o in api.operations}))
    return FrontendIR(api.schema_version, f"frontend:{api.contract_id}", routes, api.contract_id, quality_obligation_ids)
