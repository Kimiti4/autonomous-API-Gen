"""Close verification/evidence back to requirement certification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from .implementation_traceability import ImplementationTracePlan
from .requirement_ir import RequirementGraph


@dataclass(frozen=True)
class RequirementEvidenceTrace:
    requirement_id: str
    obligation_ids: tuple[str, ...]
    implementation_ids: tuple[str, ...]
    verification_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class RequirementEvidenceCertification:
    traces: tuple[RequirementEvidenceTrace, ...]
    unresolved_requirement_ids: tuple[str, ...]

    @property
    def certified(self) -> bool:
        return not self.unresolved_requirement_ids and all(t.status == "verified" for t in self.traces)


def certify_requirement_evidence(
    graph: RequirementGraph,
    obligation_source: Mapping[str, str],
    implementation_plan: ImplementationTracePlan,
    verification_results: Mapping[str, Mapping[str, object]],
) -> RequirementEvidenceCertification:
    by_obligation={t.obligation_id:t for t in implementation_plan.traces}
    grouped: dict[str,list[RequirementEvidenceTrace]]={}
    unresolved=set()
    for req in graph.requirements:
        obligations=tuple(sorted(o for o,s in obligation_source.items() if s == req.requirement_id))
        if not obligations:
            unresolved.add(req.requirement_id); continue
        impl=[]; ver=[]; evidence=[]; failed=False
        for oid in obligations:
            trace=by_obligation.get(oid)
            if trace is None:
                failed=True; continue
            impl.extend(trace.implementation_ids); ver.extend(trace.verification_ids)
            for vid in trace.verification_ids:
                result=verification_results.get(vid)
                if not result or result.get("passed") is not True:
                    failed=True; continue
                ev=result.get("evidence_ids", ())
                if not ev: failed=True
                evidence.extend(str(x) for x in ev)
        if failed or not evidence:
            unresolved.add(req.requirement_id)
            continue
        grouped.setdefault(req.requirement_id,[]).append(RequirementEvidenceTrace(
            req.requirement_id, obligations, tuple(sorted(set(impl))),
            tuple(sorted(set(ver))), tuple(sorted(set(evidence))), "verified"))
    traces=tuple(x for xs in grouped.values() for x in xs)
    return RequirementEvidenceCertification(traces,tuple(sorted(unresolved)))
