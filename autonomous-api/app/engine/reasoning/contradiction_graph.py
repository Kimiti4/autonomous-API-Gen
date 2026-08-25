from itertools import combinations

def detect_contradictions(outputs: list[str]):
    contradictions = []

    for a, b in combinations(outputs, 2):
        if is_contradiction(a, b):
            contradictions.append((a, b))

    return contradictions


def is_contradiction(a: str, b: str):
    # lightweight heuristic (upgrade later with LLM)
    opposites = [
        ("fast", "slow"),
        ("increase", "decrease"),
        ("true", "false")
    ]

    for x, y in opposites:
        if x in a.lower() and y in b.lower():
            return True
        if y in a.lower() and x in b.lower():
            return True

    return False