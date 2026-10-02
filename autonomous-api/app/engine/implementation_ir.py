"""Technology-neutral implementation IRs derived from canonical API contracts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .api_ir import ApiContractIR


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

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


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

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def backend_from_api(
    api: ApiContractIR,
    quality_obligation_ids: tuple[str, ...] = (),
) -> BackendIR:
    return BackendIR(
        schema_version=api.schema_version,
        contract_id=f"backend:{api.contract_id}",
        domain_modules=tuple(sorted({o.operation_id.split("_", 1)[0] for o in api.operations})),
        api_contract_id=api.contract_id,
        quality_obligation_ids=quality_obligation_ids,
    )


def frontend_from_api(
    api: ApiContractIR,
    quality_obligation_ids: tuple[str, ...] = (),
) -> FrontendIR:
    return FrontendIR(
        schema_version=api.schema_version,
        contract_id=f"frontend:{api.contract_id}",
        routes=tuple(sorted({o.path for o in api.operations})),
        api_contract_id=api.contract_id,
        quality_obligation_ids=quality_obligation_ids,
    )
