from ...domain.ports import IntentCompiler
from ...domain.models.isr import (
    IntermediateSoftwareRepresentation,
    IntentSpecification,
    ServiceSpec,
    DataModelSpec,
)


class StructuredIntentCompiler(IntentCompiler):
    """Deterministic intent compiler: maps a natural-language intent + hints
    into an ISR (services/data models derived from constraints). Replaces the
    LLM-driven RequirementGraph in production behind the same port."""

    def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation:
        domain = hints.get("domain", "general")
        complexity = hints.get("complexity_tier", "medium")
        services = [ServiceSpec(name="primary", responsibilities=["serve " + domain])]
        models = []
        persistence = hints.get("constraints", {}).get("persistence") if isinstance(hints.get("constraints"), dict) else None
        if persistence:
            models.append(DataModelSpec(name=persistence + "_model", fields={"id": "str"}))
        return IntermediateSoftwareRepresentation(
            system_id="stub-system",
            system_name=(" ".join(statement.split()[:6]) or "stub-system"),
            intent=IntentSpecification(statement=statement, domain=domain, complexity_tier=complexity),
            services=services,
            data_models=models,
        )
