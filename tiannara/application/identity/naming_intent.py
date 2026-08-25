"""44.2 Naming Intent -- domain, concept, actors."""
def compile_naming_intent(intent: str) -> dict:
    # Extract semantics from intent
    lower=intent.lower()
    domain="maritime mobility" if "boat" in lower else "general"
    concept="marketplace" if "uber" in lower else "service"
    return {"domain": domain, "concept": concept, "interaction": "booking", "actors": ("passengers","boat operators"), "value": "on-demand transport", "source": intent}
