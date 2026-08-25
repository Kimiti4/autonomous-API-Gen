def evaluate(result):
    score = 0

    if result["success"]:
        score += 5
        if result["output"]:
            score += 2
    if result["error"]:
        score -= 3
    return score