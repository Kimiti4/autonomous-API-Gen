"""37.2 Failure Attribution -- separate compiler/architecture/mutation/fitness/knowledge/environment."""
def attribute_failure(observation: dict) -> str:
    if observation.get("compiler_error"): return "compiler failure"
    if observation.get("arch_mismatch"): return "architecture failure"
    if observation.get("mutation_error"): return "mutation failure"
    if observation.get("fitness_error"): return "fitness failure"
    return "environment failure"
