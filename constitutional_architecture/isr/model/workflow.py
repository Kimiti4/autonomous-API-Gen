"""
ISR Workflow Model — state machines with states, transitions, and actions.
Technology-neutral: no state machine libraries, no workflow engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional


@unique
class StateType(str, Enum):
    INITIAL = "initial"
    INTERMEDIATE = "intermediate"
    FINAL = "final"
    ERROR = "error"


@dataclass(frozen=True)
class WorkflowState:
    id: str
    name: str
    state_type: StateType = StateType.INTERMEDIATE
    description: str = ""
    entry_actions: tuple[str, ...] = ()
    exit_actions: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowTransition:
    id: str
    name: str
    from_state_id: str
    to_state_id: str
    trigger: str = ""
    guard_condition: str = ""
    actions: tuple[str, ...] = ()
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Workflow:
    id: str
    name: str
    description: str = ""
    states: tuple[WorkflowState, ...] = ()
    transitions: tuple[WorkflowTransition, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def initial_states(self) -> tuple[WorkflowState, ...]:
        return tuple(s for s in self.states if s.state_type == StateType.INITIAL)

    @property
    def final_states(self) -> tuple[WorkflowState, ...]:
        return tuple(s for s in self.states if s.state_type == StateType.FINAL)

    def get_state(self, state_id: str) -> Optional[WorkflowState]:
        for s in self.states:
            if s.id == state_id:
                return s
        return None

    def get_transitions_from(self, state_id: str) -> tuple[WorkflowTransition, ...]:
        return tuple(t for t in self.transitions if t.from_state_id == state_id)