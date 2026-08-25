import asyncio

from app.engine.agents.heuristic import HeuristicAgent
from app.engine.agents.optimizer import OptimizerAgent
from app.engine.agents.explorer import ExplorerAgent

from app.engine.reasoning.scorer import score_output
from app.engine.reasoning.contradiction_graph import detect_contradictions
from app.engine.reasoning.consensus import compute_consensus


class ReasoningEngine:
    def __init__(self):
        self.agents = [
            HeuristicAgent(),
            OptimizerAgent(),
            ExplorerAgent()
        ]

    async def run(self, task: str):
        async def run_agent(agent):
            text = await agent.generate(task)
            return {
                "agent": agent.name,
                "text": text,
                "score": score_output(text)
            }

        outputs = await asyncio.gather(
            *[run_agent(agent) for agent in self.agents]
        )

        # contradictions
        contradictions = detect_contradictions(
            [o["text"] for o in outputs]
        )

        # penalize contradictions
        for o in outputs:
            for c in contradictions:
                if o["text"] in c:
                    o["score"] -= 1

        # consensus
        consensus = compute_consensus(outputs)

        return {
            "task": task,
            "outputs": outputs,
            "contradictions": contradictions,
            "consensus": consensus
        }