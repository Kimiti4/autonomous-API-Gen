"""R2 -- TransitionRestoration mutation operator (R2.3).

Seed defect class (ISR-expressible, technology-neutral): a Service/Workflow
declares an async operation it must resolve before returning -- encoded as a
`WorkflowState` with `metadata["awaits"] = <op>` -- but the resolving
`WorkflowTransition` (whose `trigger == <op>`) was dropped, so the generated
handler fires the coroutine without awaiting it.

The operator's trigger is the *specific signature*
`coroutine '<name>' was never awaited` (read from the FailureObservation's
stderr), NOT the coarse `TEST_FAILURE` class -- so ordinary failing tests never
select it.

Constitutional contract:
  - Read the ISR graph via accessors; never mutate -- write a NEW versioned ISR
    via `ISR.with_system(...)` (provenance + content_hash preserved).
  - Deterministically map `coroutine_name` -> exactly one resolving transition,
    or decline (return None). Never speculate.

Naming contract (R2.4 precondition for real codegen): the coroutine name
emitted by the backend corresponds to the `WorkflowState.metadata["awaits"]`
value / `WorkflowTransition.trigger`. The FSM harness defines this by
construction; real backends must establish it before grounding.
"""
from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.model import (
    ISR,
    System,
    Workflow,
    WorkflowTransition,
)

_COROUTINE_RE = re.compile(r"coroutine '([^'{}]+)' was never awaited")


@dataclass(frozen=True)
class _ResolvedTarget:
    workflow_id: str
    from_state_id: str
    to_state_id: str
    coroutine_name: str


def _resolve_target(isr: ISR, coroutine_name: str) -> Optional[_ResolvedTarget]:
    candidates: list[_ResolvedTarget] = []
    for module in isr.system.modules:
        for wf in module.workflows:
            awaiting = [s for s in wf.states if s.metadata.get("awaits") == coroutine_name]
            has_resolving = any(t.trigger == coroutine_name for t in wf.transitions)
            if not awaiting or has_resolving:
                continue
            finals = wf.final_states
            if not finals or len(awaiting) != 1:
                continue
            candidates.append(_ResolvedTarget(
                workflow_id=wf.id,
                from_state_id=awaiting[0].id,
                to_state_id=finals[0].id,
                coroutine_name=coroutine_name,
            ))
    if len(candidates) == 1:
        return candidates[0]
    return None


def _build_transition(target: _ResolvedTarget) -> WorkflowTransition:
    return WorkflowTransition(
        id=f"resolve-{target.coroutine_name}",
        name=f"resolve {target.coroutine_name}",
        from_state_id=target.from_state_id,
        to_state_id=target.to_state_id,
        trigger=target.coroutine_name,
    )


def _restore_edge(isr: ISR, target: _ResolvedTarget) -> ISR:
    transition = _build_transition(target)
    new_modules = []
    for module in isr.system.modules:
        new_wfs = []
        for wf in module.workflows:
            if wf.id == target.workflow_id:
                new_wfs.append(dataclasses.replace(wf, transitions=(*wf.transitions, transition)))
            else:
                new_wfs.append(wf)
        new_modules.append(dataclasses.replace(module, workflows=tuple(new_wfs)))
    new_system: System = dataclasses.replace(isr.system, modules=tuple(new_modules))
    return isr.with_system(new_system)


def _diff_json(target: _ResolvedTarget) -> str:
    return json.dumps(
        {
            "workflow_id": target.workflow_id,
            "from_state_id": target.from_state_id,
            "to_state_id": target.to_state_id,
            "trigger": target.coroutine_name,
        },
        sort_keys=True,
    )


def _relax_guard(isr: ISR, desc: dict) -> ISR:
    """R2.9.2 -- clear a blocking ``guard_condition`` on one transition."""
    workflow_id = desc["workflow_id"]
    transition_id = desc["transition_id"]
    new_modules = []
    for module in isr.system.modules:
        new_wfs = []
        for wf in module.workflows:
            if wf.id != workflow_id:
                new_wfs.append(wf)
                continue
            new_transitions = tuple(
                dataclasses.replace(t, guard_condition="")
                if t.id == transition_id
                else t
                for t in wf.transitions
            )
            new_wfs.append(dataclasses.replace(wf, transitions=new_transitions))
        new_modules.append(dataclasses.replace(module, workflows=tuple(new_wfs)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(new_modules)))


def _inject_action(isr: ISR, desc: dict) -> ISR:
    """R2.9.2 -- attach a side-effect action to one transition."""
    workflow_id = desc["workflow_id"]
    transition_id = desc["transition_id"]
    action = desc["action"]
    new_modules = []
    for module in isr.system.modules:
        new_wfs = []
        for wf in module.workflows:
            if wf.id != workflow_id:
                new_wfs.append(wf)
                continue
            new_transitions = tuple(
                dataclasses.replace(t, actions=(*t.actions, action))
                if t.id == transition_id
                else t
                for t in wf.transitions
            )
            new_wfs.append(dataclasses.replace(wf, transitions=new_transitions))
        new_modules.append(dataclasses.replace(module, workflows=tuple(new_wfs)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(new_modules)))


def _add_exploratory_edge(isr: ISR, desc: dict) -> ISR:
    """R2.9.2 -- add a structurally valid exploratory transition.

    Deterministic identity: the new transition id is derived from its
    endpoints + trigger, so replaying the same (ISR, seed) reproduces the
    same candidate. A duplicate (from, to, trigger) triple is declined.
    """
    workflow_id = desc["workflow_id"]
    from_state_id = desc["from_state_id"]
    to_state_id = desc["to_state_id"]
    trigger = desc["trigger"]
    transition = WorkflowTransition(
        id=f"explore-{from_state_id}-{to_state_id}-{trigger}",
        name=f"explore {from_state_id} -> {to_state_id}",
        from_state_id=from_state_id,
        to_state_id=to_state_id,
        trigger=trigger,
    )
    new_modules = []
    for module in isr.system.modules:
        new_wfs = []
        for wf in module.workflows:
            if wf.id != workflow_id:
                new_wfs.append(wf)
                continue
            if any(
                (t.from_state_id, t.to_state_id, t.trigger)
                == (from_state_id, to_state_id, trigger)
                for t in wf.transitions
            ):
                new_wfs.append(wf)
                continue
            new_wfs.append(dataclasses.replace(wf, transitions=(*wf.transitions, transition)))
        new_modules.append(dataclasses.replace(module, workflows=tuple(new_wfs)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(new_modules)))


def _strip_awaits(isr: ISR, desc: dict) -> ISR:
    """R2.9.2 deceptive primitive -- remove the awaiting surface from a state.

    This is the ISR-level analog of "delete the test that checks the
    transition": the generated async surface no longer fires the coroutine, so
    the failing signature disappears while the awaiting contract is silently
    dropped. The R2.8 boundary (``AwaitingSurfaceIntactInvariant``) must
    reject it.
    """
    workflow_id = desc["workflow_id"]
    state_id = desc["state_id"]
    new_modules = []
    for module in isr.system.modules:
        new_wfs = []
        for wf in module.workflows:
            if wf.id != workflow_id:
                new_wfs.append(wf)
                continue
            new_states = tuple(
                dataclasses.replace(
                    s,
                    metadata={k: v for k, v in s.metadata.items() if k != "awaits"},
                )
                if s.id == state_id
                else s
                for s in wf.states
            )
            new_wfs.append(dataclasses.replace(wf, states=new_states))
        new_modules.append(dataclasses.replace(module, workflows=tuple(new_wfs)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(new_modules)))


def apply_restoration(isr: ISR, diff: tuple[str, ...]) -> ISR:
    """Apply an ISR delta. Entries are R2.3 JSON descriptors; an optional
    ``op`` key dispatches to the R2.9.2 constructive variation primitives
    (``relax_guard``, ``inject_action``, ``explore``, ``strip_awaits``). The
    default (no ``op``) is the R2.4.0b transition restoration. Closure is
    verified by the CausalGate against this exact function, so every new op
    keeps the same tamper-evident causality guarantee."""
    current = isr
    for entry in diff:
        desc = json.loads(entry)
        op = desc.get("op", "restore")
        if op == "restore":
            target = _ResolvedTarget(
                workflow_id=desc["workflow_id"],
                from_state_id=desc["from_state_id"],
                to_state_id=desc["to_state_id"],
                coroutine_name=desc["trigger"],
            )
            current = _restore_edge(current, target)
        elif op == "relax_guard":
            current = _relax_guard(current, desc)
        elif op == "inject_action":
            current = _inject_action(current, desc)
        elif op == "explore":
            current = _add_exploratory_edge(current, desc)
        elif op == "strip_awaits":
            current = _strip_awaits(current, desc)
        else:
            raise ValueError(f"unknown variation op {op!r}")
    return current


@dataclass(frozen=True)
class RepairedCandidate:
    origin: str
    repaired_isr: ISR
    hypothesis: str
    repaired_diff: tuple[str, ...] = field(default_factory=tuple)


class TransitionRestoration:
    """First Evolution Engine mutation operator: restores a dropped async-resolution transition."""

    name = "transition_restoration"

    @staticmethod
    def extract_coroutine_name(observation) -> Optional[str]:
        haystack = " ".join(observation.diagnostics) + "\n" + observation.stderr_excerpt
        match = _COROUTINE_RE.search(haystack)
        return match.group(1) if match else None

    def hypothesis(self, observation, broken_isr: ISR) -> Optional[RepairedCandidate]:
        coroutine_name = self.extract_coroutine_name(observation)
        if coroutine_name is None:
            return None
        return self.try_repair(broken_isr, coroutine_name)

    def try_repair(self, isr: ISR, coroutine_name: str) -> Optional[RepairedCandidate]:
        """R2.4.0b Step 1 entry point: restore the resolving transition for a
        known coroutine name (read from the FailureObservation's stderr).

        Returns ``None`` when no *unique* resolving target exists -- i.e. the
        coroutine is unmatched, ambiguous across workflows, or the transition is
        already present. Never speculates: the closed loop only acts on a
        one-to-one edge-to-name mapping.
        """
        target = _resolve_target(isr, coroutine_name)
        if target is None:
            return None
        repaired = _restore_edge(isr, target)
        diff = (_diff_json(target),)
        return RepairedCandidate(
            origin=self.name,
            repaired_isr=repaired,
            hypothesis=(
                f"restore required async resolution of '{coroutine_name}' "
                f"(transition {target.from_state_id} -> {target.to_state_id})"
            ),
            repaired_diff=diff,
        )
