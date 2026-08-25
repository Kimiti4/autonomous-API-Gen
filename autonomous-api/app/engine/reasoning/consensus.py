def compute_consensus(outputs: list[dict]):
    total_score = 0
    weighted = []

    for o in outputs:
        total_score += o["score"]

    for o in outputs:
        weight = o["score"] / total_score if total_score else 0
        weighted.append({
            "text": o["text"],
            "weight": weight
        })

    # pick highest weighted reasoning
    best = max(weighted, key=lambda x: x["weight"])

    return {
        "best": best,
        "distribution": weighted
    }