"""Evidence-bounded multi-objective architecture optimization."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from .pareto_architecture import ArchitectureScore, Objective, build_frontier

@dataclass(frozen=True)
class MultiObjectiveCandidate:
    candidate_id: str
    score: ArchitectureScore
    mandatory_gates_passed: bool
    evidence_current: bool
    findings: tuple[str,...]=()
    @property
    def eligible(self)->bool:
        return self.mandatory_gates_passed and self.evidence_current and not self.findings and bool(self.score.evidence)

@dataclass(frozen=True)
class MultiObjectiveResult:
    frontier: tuple[str,...]
    dominated: tuple[str,...]
    ineligible: tuple[str,...]
    status: str
    rationale: str

def require_comparable_objectives(scores: Sequence[ArchitectureScore], objectives: Sequence[Objective])->None:
    if not objectives: raise ValueError("optimization-requires-objectives")
    names=[o.name.strip() for o in objectives]
    if any(not n for n in names) or len(set(names))!=len(names): raise ValueError("invalid-objective-names")
    for o in objectives: o.validate()
    for s in scores:
        for o in objectives:
            v=s.values.get(o.name)
            if not isinstance(v,(int,float)) or isinstance(v,bool): raise ValueError("missing-or-nonnumeric-objective")

def evaluate_multi_objective(candidates: Sequence[MultiObjectiveCandidate], objectives: Sequence[Objective])->MultiObjectiveResult:
    if not candidates: raise ValueError("optimization-requires-candidates")
    if len({c.candidate_id for c in candidates})!=len(candidates): raise ValueError("duplicate-candidate-id")
    eligible=[c.score for c in candidates if c.eligible]
    ineligible=tuple(sorted(c.candidate_id for c in candidates if not c.eligible))
    if not eligible: return MultiObjectiveResult((),(),ineligible,"ineligible-all","no candidate has complete current evidence and mandatory gates")
    require_comparable_objectives(eligible,objectives)
    p=build_frontier(eligible,objectives)
    return MultiObjectiveResult(p.frontier,p.dominated,ineligible,"pareto-frontier","evidence-backed non-dominated trade-offs; no global optimum claimed")

def optimize_multi_objective(candidates, objectives): return evaluate_multi_objective(candidates,objectives)
