from app.engine.llm import call_llm


class HeuristicAgent:
    name = "heuristic"

    async def generate(self, task: str):
        prompt = f"""
Give a simple and quick solution for:

{task}

Keep it minimal and practical.
"""
        return await call_llm(prompt)