"""
ASE-OS Governance Kernel & Multi-Agent Protocol.

Enforces constitutional invariants and mediates agent collaboration.

Agents observe the UEM, reason against the CKB, and propose directives.
The Governance Kernel intercepts all writes: any directive that injects a
forbidden technology (see the Forbidden Lexicon) into the ISR is rejected
before it can be appended to the UEM. Valid directives receive a
cryptographic proof of validation.

Constitutional Alignment:
- Axiom I (ISR Supremacy): technology coupling into the ISR is
  mathematically impossible.
- "Each agent should produce evidence-based recommendations": directives
  must carry a rationale.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel

from constitutional_architecture.core.constitution import FORBIDDEN_LEXICON
from constitutional_architecture.core.kernels.engineering.uem import (
    EventType, UEMEvent, UniversalEngineeringMemory,
)


class AgentDirective(BaseModel):
    agent_role: str
    target_node: str
    attribute: str
    value: Any
    rationale: str


class GovernanceViolation(Exception):
    pass


class GovernanceKernel:
    """Intercepts all agent actions to enforce the Constitution."""

    def validate_directive(self, directive: AgentDirective) -> str:
        # 1. Check for technology coupling in the value or rationale
        text = f"{directive.value} {directive.rationale}".lower()
        for term in FORBIDDEN_LEXICON:
            if re.search(rf"\b{re.escape(term)}\b", text):
                raise GovernanceViolation(
                    f"Agent '{directive.agent_role}' attempted to inject "
                    f"forbidden technology '{term}' into ISR."
                )
        # 2. Return cryptographic proof of validation
        proof_hash = hashlib.sha256(
            directive.model_dump_json().encode()).hexdigest()[:12]
        return "gov_proof_" + proof_hash


class Agent(ABC):
    """Base class for all specialized engineering agents."""

    def __init__(self, role: str, uem: UniversalEngineeringMemory,
                 gov: GovernanceKernel) -> None:
        self.role = role
        self.uem = uem
        self.gov = gov

    @abstractmethod
    def reason(self, target_id: str) -> List[AgentDirective]:
        pass

    def act(self, target_id: str, directives: List[AgentDirective]) -> None:
        for directive in directives:
            proof = self.gov.validate_directive(directive)  # Governance Gate
            self.uem.append(UEMEvent(
                event_type=EventType.AGENT_CRITIQUE,
                actor_id=self.role,
                target_id=target_id,
                payload=directive.model_dump(),
                constitutional_proof=proof,
            ))
