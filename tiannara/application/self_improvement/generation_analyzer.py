"""37.1 Generation Performance Analyzer."""
def analyze_generation(generation: dict) -> dict:
    return {"failed_where": generation.get("failed_stage","unknown"), "compiler": generation.get("compiler","unknown")}
