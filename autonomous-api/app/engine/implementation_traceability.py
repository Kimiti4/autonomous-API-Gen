"""Trace architecture obligations into implementation components and tests."""
from __future__ import annotations
from dataclasses import dataclass

from .architecture_obligations import ArchitectureObligation, ObligationMapping
from .implementation_ir import BackendIR, FrontendIR


@dataclass(frozen=True)
class ImplementationTrace:
    obligation_id: str
    component_ids: tuple[str, ...]
    implementation_ids: tuple[str, ...]
    verification_ids: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class ImplementationTracePlan:
    traces: tuple[ImplementationTrace, ...]
    unresolved_obligations: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.unresolved_obligations and all(t.status == "planned" for t in self.traces)


def derive_implementation_trace(
    obligations: tuple[ArchitectureObligation, ...],
    mappings: tuple[ObligationMapping, ...],
    frontend: FrontendIR | None = None,
    backend: BackendIR | None = None,
) -> ImplementationTracePlan:
    components = set()
    for ir in (frontend, backend):
        if ir:
            components.update(m.module_id for m in ir.modules)
            components.update(ir.routes if isinstance(ir, FrontendIR) else ir.domain_modules)
    by_id = {m.obligation_id: m for m in mappings}
    traces=[]
    unresolved=[]
    for obligation in obligations:
        mapping=by_id.get(obligation.obligation_id)
        if mapping is None or not mapping.satisfied or not mapping.component_ids:
            unresolved.append(obligation.obligation_id)
            continue
        missing=tuple(sorted(set(mapping.component_ids)-components))
        if missing:
            unresolved.append(obligation.obligation_id)
            continue
        implementation_ids=tuple(f"impl:{c}" for c in sorted(mapping.component_ids))
        verification_ids=tuple(obligation.verification)
        traces.append(ImplementationTrace(
            obligation.obligation_id, tuple(sorted(mapping.component_ids)),
            implementation_ids, verification_ids, obligation.verification, "planned"))
    return ImplementationTracePlan(tuple(traces), tuple(sorted(set(unresolved))))
