class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def generate(self, task: str) -> str:
        raise NotImplementedError