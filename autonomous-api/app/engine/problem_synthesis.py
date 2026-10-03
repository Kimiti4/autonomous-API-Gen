"""Problem-aware strategy synthesis from requirements and constraints."""
from __future__ import annotations
from dataclasses import dataclass
from .exploration_engine import SolutionStrategy, ExplorationRequest


@dataclass(frozen=True)
class ProblemModel:
    domain: str
    actors: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    opportunities: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SynthesizedStrategy(SolutionStrategy):
    derivation: tuple[str, ...] = ()


def synthesize_strategies(
    request: ExplorationRequest,
    problem: ProblemModel,
) -> tuple[SynthesizedStrategy, ...]:
    signals = []
    if problem.workflows:
        signals.append("workflow-structure")
    if problem.failure_modes:
        signals.append("explicit-failure-model")
    if problem.opportunities:
        signals.append("opportunity-driven-design")
    if "offline" in " ".join(problem.constraints).lower():
        signals.append("offline-capability")
    if "high throughput" in " ".join(problem.constraints).lower():
        signals.append("throughput-first")

    families = ["domain_composed", "workflow_composed", "data_composed"]
    if "offline-capability" in signals:
        families.append("offline_resilient")
    if "throughput-first" in signals:
        families.append("throughput_optimized")

    out = []
    for family in families:
        out.append(SynthesizedStrategy(
            strategy_id=f"{request.request_id}:synth:{family}",
            family=family,
            principles=("requirements-first", "evidence-driven", "problem-derived"),
            components=problem.entities,
            assumptions=problem.constraints,
            intended_strengths=request.required_properties,
            known_risks=problem.failure_modes,
            derivation=tuple(signals) + (f"domain:{problem.domain}",),
        ))
    return tuple(out)
