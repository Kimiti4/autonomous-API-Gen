from app.engine.llm import call_llm


class OptimizerAgent:
    name = "optimizer"

    async def generate(self, task: str):
        prompt = f"""
Provide an optimized, production-quality solution for:

{task}

Requirements:
- clear structure
- best practices
- working code if applicable
- concise explanation
"""
        return await call_llm(prompt)