"""LLM-guided mutation with an explicit, fail-closed genome boundary."""

import json
import random
from typing import Any, Dict, List

from app.core.logger import logger
from app.engine.llm import get_llm_client


ALLOWED_MUTATION_FIELDS = {
    "services", "auth", "database", "cache_enabled", "rate_limiting",
    "cors_enabled", "logging_level", "api_version", "openapi_version",
    "health_endpoints", "metrics_endpoints", "tracing_enabled", "circuit_breaker",
    "retry_policy", "timeout_config", "deployment_target",
}

ENUM_FIELDS = {
    "auth": {"jwt", "oauth2", "api_key", "basic"},
    "database": {"postgres", "sqlite", "mysql"},
    "logging_level": {"DEBUG", "INFO", "WARNING", "ERROR"},
    "api_version": {"v1", "v2", "v3"},
    "openapi_version": {"3.0.0", "3.1.0"},
}
BOOL_FIELDS = {
    "cache_enabled", "rate_limiting", "cors_enabled", "health_endpoints",
    "metrics_endpoints", "tracing_enabled", "circuit_breaker",
}


class LLMGuidedMutator:
    """Use an LLM to propose mutations; never allow it to bypass genome rules."""

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.client = get_llm_client()
        self.mutation_cache: Dict[str, Dict[str, Any]] = {}

    async def suggest_mutations(
        self,
        genome: Dict[str, Any],
        fitness_score: float,
        generation: int,
        run_history: List[Dict] | None = None,
        context: str = "",
    ) -> Dict[str, Any]:
        try:
            cache_key = f"{json.dumps(genome, sort_keys=True)}_{fitness_score:.6f}"
            if cache_key in self.mutation_cache:
                return self.mutation_cache[cache_key]
            prompt = self._build_mutation_prompt(genome, fitness_score, generation, run_history, context)
            response = await self.client.generate(prompt)
            parsed = self._parse_llm_response(response)
            self.mutation_cache[cache_key] = parsed
            if len(self.mutation_cache) > 100:
                del self.mutation_cache[next(iter(self.mutation_cache))]
            return parsed
        except Exception as exc:
            logger.error("LLM-guided mutation failed", exc_info=True)
            return self._fallback_mutation(genome)

    def _build_mutation_prompt(self, genome, fitness, generation, history=None, context="") -> str:
        return f'''You are an API architecture optimizer.

CURRENT GENOME:
{json.dumps(genome, indent=2)}

FITNESS: {fitness:.3f}
GENERATION: {generation}
CONTEXT: {context or "General optimization"}

Suggest at most 3 mutations. Only use these fields:
{sorted(ALLOWED_MUTATION_FIELDS)}

Return JSON only:
{{
  "mutations": [
    {{"field": "database", "current_value": "sqlite", "suggested_value": "postgres", "reason": "..."}}
  ],
  "confidence": 0.0,
  "explanation": "..."
}}
'''

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start < 0 or end <= start:
                return self._empty_result("Parsing failed")
            parsed = json.loads(response[start:end + 1])
            mutations = parsed.get("mutations", [])
            if not isinstance(mutations, list):
                return self._empty_result("Invalid mutations list")

            validated = []
            for mutation in mutations[:3]:
                candidate = self._validate_mutation(mutation)
                if candidate is not None:
                    validated.append(candidate)

            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(confidence, 1.0))
            return {
                "mutations": validated,
                "confidence": confidence,
                "explanation": str(parsed.get("explanation", ""))[:1000],
            }
        except Exception as exc:
            logger.warning("Failed to validate LLM response: %s", exc)
            return self._empty_result(str(exc))

    @staticmethod
    def _empty_result(reason: str) -> Dict[str, Any]:
        return {"mutations": [], "confidence": 0.0, "explanation": reason}

    def _validate_mutation(self, mutation: Any) -> Dict[str, Any] | None:
        if not isinstance(mutation, dict):
            return None
        field = mutation.get("field")
        if field not in ALLOWED_MUTATION_FIELDS:
            logger.warning("Rejected LLM mutation for unsupported field: %r", field)
            return None
        if "suggested_value" not in mutation:
            return None
        value = mutation["suggested_value"]

        if field in ENUM_FIELDS and value not in ENUM_FIELDS[field]:
            return None
        if field in BOOL_FIELDS and not isinstance(value, bool):
            return None
        if field == "services" and (
            not isinstance(value, list) or not 2 <= len(value) <= 6 or not all(isinstance(v, str) for v in value)
        ):
            return None
        if field in {"retry_policy", "timeout_config"} and not isinstance(value, dict):
            return None
        if field == "deployment_target" and value not in {"docker-compose", "docker"}:
            return None

        return {
            "field": field,
            "current_value": mutation.get("current_value"),
            "suggested_value": value,
            "reason": str(mutation.get("reason", ""))[:500],
        }

    def _fallback_mutation(self, genome: Dict[str, Any]) -> Dict[str, Any]:
        mutations = []
        if genome.get("database") == "sqlite":
            mutations.append({"field": "database", "current_value": "sqlite", "suggested_value": "postgres", "reason": "Use a production database."})
        if not genome.get("cache_enabled"):
            mutations.append({"field": "cache_enabled", "current_value": False, "suggested_value": True, "reason": "Enable caching."})
        if not genome.get("rate_limiting"):
            mutations.append({"field": "rate_limiting", "current_value": False, "suggested_value": True, "reason": "Add rate limiting."})
        return {"mutations": mutations[:2], "confidence": 0.5, "explanation": "Fallback mutations"}

    def apply_suggested_mutations(self, genome: Dict[str, Any], suggestions: Dict[str, Any], acceptance_threshold: float = 0.6) -> Dict[str, Any]:
        if not 0.0 <= acceptance_threshold <= 1.0:
            raise ValueError("acceptance_threshold must be between 0 and 1")
        mutated = dict(genome)
        confidence = max(0.0, min(float(suggestions.get("confidence", 0.0)), 1.0))
        applied = 0
        for mutation in suggestions.get("mutations", []):
            validated = self._validate_mutation(mutation)
            if validated is None:
                continue
            if confidence >= acceptance_threshold or random.random() < confidence:
                mutated[validated["field"]] = validated["suggested_value"]
                applied += 1
        logger.info("Applied %s validated LLM mutations", applied)
        return mutated

    def clear_cache(self):
        self.mutation_cache.clear()


async def llm_guided_crossover_and_mutation(parent1: Dict, parent2: Dict, fitness1: float, fitness2: float, generation: int, llm_mutator: LLMGuidedMutator, context: str = "") -> Dict:
    offspring = {}
    keys = parent1.keys() | parent2.keys()
    for key in keys:
        if key not in parent2:
            offspring[key] = parent1[key]
        elif key not in parent1:
            offspring[key] = parent2[key]
        elif fitness1 > fitness2:
            offspring[key] = parent1[key] if random.random() < 0.7 else parent2[key]
        else:
            offspring[key] = parent2[key] if random.random() < 0.7 else parent1[key]

    estimated_fitness = (fitness1 + fitness2) / 2
    suggestions = await llm_mutator.suggest_mutations(
        genome=offspring,
        fitness_score=estimated_fitness,
        generation=generation,
        context=context,
    )
    return llm_mutator.apply_suggested_mutations(
        genome=offspring,
        suggestions=suggestions,
        acceptance_threshold=0.7,
    )
