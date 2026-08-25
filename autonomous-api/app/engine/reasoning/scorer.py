def score_solution(solution: str):
    score = 0

    if "optimized" in solution.lower():
        score += 2
    if "experimental" in solution.lower():
        score += 1
# app/engine/scorer.py

def score_output(text: str):
    score = 0

    if "def " in text:
        score += 3
    if "return" in text:
        score += 2
    if "security" in text.lower():
        score += 2
    if len(text) > 300:
        score += 1

    return score