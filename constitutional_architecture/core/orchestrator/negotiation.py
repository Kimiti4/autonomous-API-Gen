"""
Phase 19 — Multi-Agent Negotiation Protocol.

The Evolution Coordinator mediates the bounded debate between specialized
agents: critiques are gathered, FATAL objections block compilation,
directives are synthesized into the draft, and consensus (no objections)
locks the Intent for Pass 3 (Topology Resolution).

Constitutional Alignment:
- "Architectural decisions should emerge through collaboration rather than
  isolated reasoning."
- The MAX_ROUNDS bound guarantees termination (bounded debate).
"""

from __future__ import annotations

from typing import Any, Dict, List

from constitutional_architecture.core.agents.base import (
    Agent, ArchitecturalDirective, Critique, ObjectionSeverity,
)


class NegotiationFailure(Exception):
    """Agents could not reach consensus within the round budget."""


class MultiAgentCoordinator:
    """Mediates the multi-agent debate over a raw requirement draft."""

    MAX_ROUNDS = 3

    def __init__(self, agents: List[Agent]) -> None:
        self.agents = agents
        self.round_log: List[Dict[str, Any]] = []

    def negotiate_intent(self, raw_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Run the negotiation loop to produce a consensus Intent draft."""
        current_draft = {k: self._deep_copy(v) for k, v in raw_requirements.items()}
        applied_directives: List[ArchitecturalDirective] = []

        for round_num in range(self.MAX_ROUNDS):
            round_critiques: List[Critique] = []
            for agent in self.agents:
                critiques = agent.analyze(
                    current_draft, context={"round": round_num})
                round_critiques.extend(critiques)

            self.round_log.append({
                "round": round_num + 1,
                "critiques": [
                    {"agent_role": c.agent_role,
                     "severity": c.severity.value,
                     "message": c.message}
                    for c in round_critiques
                ],
            })

            fatals = [c for c in round_critiques
                      if c.severity == ObjectionSeverity.FATAL]
            if not fatals and not any(
                    c.severity == ObjectionSeverity.WARNING
                    for c in round_critiques):
                break

            for critique in round_critiques:
                for directive in critique.proposed_directives:
                    if directive not in applied_directives:
                        self._apply_directive(current_draft, directive)
                        applied_directives.append(directive)

            if round_num == self.MAX_ROUNDS - 1 and fatals:
                raise NegotiationFailure(
                    "Agents could not reach consensus. Fatal flaws remain: "
                    + "; ".join(f.message for f in fatals)
                )

        return current_draft

    def _apply_directive(self, draft: Dict[str, Any],
                         directive: ArchitecturalDirective) -> None:
        """Mutate the draft based on the agent's directive."""
        if directive.target_node == "GLOBAL":
            draft[directive.attribute] = directive.value
            return

        target_type, target_name = directive.target_node.split(":", 1)

        if target_type == "CAPABILITY":
            for cap in draft.get("capabilities", []):
                if cap.get("name") == target_name:
                    cap[directive.attribute] = directive.value
        elif target_type == "DOMAIN":
            for domain in draft.get("data_domains", []):
                if domain.get("name") == target_name:
                    domain[directive.attribute] = directive.value

    @staticmethod
    def _deep_copy(value: Any) -> Any:
        import copy
        return copy.deepcopy(value)
