"""Complete requirement -> architecture -> implementation -> verification certification."""
from dataclasses import dataclass
from typing import Sequence
from .requirement_ir import RequirementGraph
from .requirement_architecture_bridge import ArchitecturePlan
from .architecture_obligations import ArchitectureObligation, ObligationMapping
from .implementation_traceability import ImplementationTracePlan
from .verification_obligations import VerificationObligation

@dataclass(frozen=True)
class RequirementChainFinding:
    requirement_id: str
    stage: str
    reason: str

@dataclass(frozen=True)
class RequirementImplementationVerificationChain:
    requirement_ids: tuple[str,...]
    architecture_ids: tuple[str,...]
    implementation_ids: tuple[str,...]
    verification_ids: tuple[str,...]
    findings: tuple[RequirementChainFinding,...]
    @property
    def complete(self): return not self.findings

def certify_requirement_to_verification_chain(graph: RequirementGraph, architecture_plan: ArchitecturePlan, obligations: Sequence[ArchitectureObligation], mappings: Sequence[ObligationMapping], implementation_plan: ImplementationTracePlan, verification_obligations: Sequence[VerificationObligation]) -> RequirementImplementationVerificationChain:
    required=tuple(sorted(graph.requirements)); findings=[]
    links={r:[] for r in required}
    for x in architecture_plan.links:
        if x.requirement_id in links: links[x.requirement_id].append(x.obligation_id)
    obs={x.obligation_id:x for x in obligations}; maps={x.obligation_id:x for x in mappings}; traces={x.obligation_id:x for x in implementation_plan.traces}
    arch=[]; impl=[]; vids=[]
    if graph.issues:
        findings += [RequirementChainFinding(r,"requirements","requirement-graph-has-issues") for r in required]
    for rid in required:
        oids=tuple(sorted(set(links[rid])))
        if not oids:
            findings.append(RequirementChainFinding(rid,"architecture","missing-architecture-obligation")); continue
        for oid in oids:
            if oid not in obs:
                findings.append(RequirementChainFinding(rid,"architecture","unknown-architecture-obligation:"+oid)); continue
            arch.append(oid); m=maps.get(oid); t=traces.get(oid)
            if m is None or not m.satisfied:
                findings.append(RequirementChainFinding(rid,"architecture","unsatisfied-architecture-mapping:"+oid)); continue
            if not m.component_ids:
                findings.append(RequirementChainFinding(rid,"implementation","missing-component-mapping:"+oid)); continue
            if t is None:
                findings.append(RequirementChainFinding(rid,"implementation","missing-implementation-trace:"+oid)); continue
            if t.status!="planned" or not t.implementation_ids:
                findings.append(RequirementChainFinding(rid,"implementation","incomplete-implementation-trace:"+oid)); continue
            impl.extend(t.implementation_ids)
            if not t.verification_ids:
                findings.append(RequirementChainFinding(rid,"verification","missing-verification-anchor:"+oid)); continue
            for vid in t.verification_ids:
                matches=[v for v in verification_obligations if v.obligation_id==vid]
                if not matches: matches=[v for v in verification_obligations if v.scenario==vid or v.expected==vid]
                if not matches: findings.append(RequirementChainFinding(rid,"verification","unresolved-verification:"+vid))
                else: vids.extend(v.obligation_id for v in matches)
    for rid in required:
        for oid in links[rid]:
            if oid in implementation_plan.unresolved_obligations:
                findings.append(RequirementChainFinding(rid,"implementation","implementation-plan-unresolved:"+oid))
    return RequirementImplementationVerificationChain(required,tuple(sorted(set(arch))),tuple(sorted(set(impl))),tuple(sorted(set(vids))),tuple(sorted(set(findings),key=lambda x:(x.requirement_id,x.stage,x.reason))))
def require_complete_chain(chain):
    if not chain.complete: raise ValueError("requirement-to-verification-chain-not-certified")
