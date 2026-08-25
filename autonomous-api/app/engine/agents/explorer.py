from app.engine.llm import call_llm


class ExplorerAgent:
    name = "explorer"

    async def generate(self, task: str):
        prompt = f"""
Give a creative or unconventional solution for:

{task}

Think outside the box.
"""
        return await call_llm(prompt)