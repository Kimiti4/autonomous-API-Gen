"""Bounded counterexample -> repair -> re-verification feedback control.

The loop is deliberately orchestration-only: a repair operator must produce the
next verified result. ESAP never invents a repair, treats a retry as progress,
or runs indefinitely.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .cross_domain_evolution import CoEvolutionResult
from .repair_coevolution import Counterexample, extract_counterexamples

@dataclass(frozen=True)
class RepairFeedbackRound:
    iteration: int
    source_architecture_id: str
    result_architecture_id: str
    counterexamples: tuple[Counterexample, ...]
    passed: bool

@dataclass(frozen=True)
class RepairFeedbackResult:
    status: str
    rounds: tuple[RepairFeedbackRound, ...]
    final_result: CoEvolutionResult
    residuals: tuple[str, ...]

RepairRound = Callable[[CoEvolutionResult, tuple[Counterexample, ...], int], CoEvolutionResult]

def run_counterexample_repair_feedback(initial: CoEvolutionResult, repair_round: RepairRound, *, max_rounds: int = 3) -> RepairFeedbackResult:
    if max_rounds < 1:
        raise ValueError("repair-feedback-requires-positive-bound")
    if not callable(repair_round):
        raise ValueError("repair-feedback-requires-repair-operator")
    current = initial
    rounds = []
    seen = set()
    for iteration in range(1, max_rounds + 1):
        counterexamples = extract_counterexamples(current)
        rounds.append(RepairFeedbackRound(iteration, current.event.source_architecture_id, current.architecture_id, counterexamples, current.passed))
        if current.passed:
            return RepairFeedbackResult("closed", tuple(rounds), current, ())
        if not counterexamples:
            return RepairFeedbackResult("blocked", tuple(rounds), current, ("verification-failed-without-counterexample",))
        if iteration == max_rounds:
            return RepairFeedbackResult("bounded-exhausted", tuple(rounds), current, ("maximum-repair-rounds-reached",))
        signature = tuple(sorted((cx.domain, cx.mutation_id, cx.failed_properties) for cx in counterexamples))
        if signature in seen:
            return RepairFeedbackResult("blocked", tuple(rounds), current, ("repeated-counterexample-signature",))
        seen.add(signature)
        next_result = repair_round(current, counterexamples, iteration)
        if not isinstance(next_result, CoEvolutionResult):
            raise ValueError("repair-feedback-operator-must-return-coevolution-result")
        if next_result.event.event_id == current.event.event_id:
            raise ValueError("repair-feedback-requires-new-event")
        if next_result.architecture_id == current.architecture_id:
            raise ValueError("repair-feedback-requires-new-architecture")
        current = next_result
    raise AssertionError("unreachable")
