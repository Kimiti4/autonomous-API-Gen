"""
LLM-Guided Mutation System
Uses language models to intelligently suggest architectural mutations
based on evolution context, performance data, and best practices.

This is a GAME-CHANGING feature that combines genetic algorithms with
LLM reasoning for superior API architecture discovery.
"""

import json
from typing import Dict, List, Optional, Any
from app.core.logger import logger
from app.engine.llm import get_llm_client


class LLMGuidedMutator:
    """
    Uses LLM to guide mutation decisions based on:
    - Current genome performance
    - Historical success patterns
    - Architectural best practices
    - Domain-specific knowledge
    """
    
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.client = get_llm_client()
        self.mutation_cache = {}  # Cache LLM suggestions
    
    async def suggest_mutations(
        self,
        genome: Dict[str, Any],
        fitness_score: float,
        generation: int,
        run_history: List[Dict] = None,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Use LLM to suggest intelligent mutations for a genome.
        
        Args:
            genome: Current genome configuration
            fitness_score: Current fitness score (0-1)
            generation: Current generation number
            run_history: Previous evolution runs for context
            context: Additional context (e.g., "optimize for security")
        
        Returns:
            Suggested mutations as dictionary
        """
        try:
            # Check cache first
            cache_key = f"{json.dumps(genome, sort_keys=True)}_{fitness_score}"
            if cache_key in self.mutation_cache:
                logger.debug("Using cached LLM suggestion")
                return self.mutation_cache[cache_key]
            
            # Build prompt for LLM
            prompt = self._build_mutation_prompt(
                genome, fitness_score, generation, run_history, context
            )
            
            # Get LLM suggestion
            response = await self.client.generate(prompt)
            
            # Parse suggestion
            suggested_mutations = self._parse_llm_response(response)
            
            # Cache result
            self.mutation_cache[cache_key] = suggested_mutations
            
            # Limit cache size
            if len(self.mutation_cache) > 100:
                oldest_key = next(iter(self.mutation_cache))
                del self.mutation_cache[oldest_key]
            
            logger.info(f"LLM suggested {len(suggested_mutations)} mutations")
            return suggested_mutations
        
        except Exception as e:
            logger.error(f"LLM-guided mutation failed: {e}")
            # Fallback to random mutation
            return self._fallback_mutation(genome)
    
    def _build_mutation_prompt(
        self,
        genome: Dict,
        fitness: float,
        generation: int,
        history: List = None,
        context: str = ""
    ) -> str:
        """Build prompt for LLM mutation suggestion"""
        
        prompt = f"""You are an expert API architect helping evolve better API designs.

CURRENT GENOME:
{json.dumps(genome, indent=2)}

PERFORMANCE:
- Fitness Score: {fitness:.3f} ({'excellent' if fitness > 0.8 else 'good' if fitness > 0.6 else 'poor'})
- Generation: {generation}

CONTEXT: {context or "General optimization"}

TASK:
Suggest 2-3 specific mutations to improve this API architecture. Consider:
1. Security improvements (authentication, rate limiting, input validation)
2. Performance optimizations (caching, database choice, async operations)
3. Scalability enhancements (microservices, load balancing, horizontal scaling)
4. Best practices (error handling, logging, monitoring)

FORMAT YOUR RESPONSE AS JSON:
{{
  "mutations": [
    {{
      "field": "database",
      "current_value": "sqlite",
      "suggested_value": "postgres",
      "reason": "PostgreSQL offers better concurrency and ACID compliance for production APIs"
    }},
    ...
  ],
  "confidence": 0.85,
  "explanation": "Brief explanation of why these changes will help"
}}

RULES:
- Only suggest realistic, implementable changes
- Consider trade-offs (complexity vs benefits)
- Don't suggest removing critical features
- Focus on high-impact improvements
- Keep suggestions concise

RESPOND WITH JSON ONLY:"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured mutations"""
        try:
            # Try to extract JSON from response
            if "{" in response:
                json_start = response.index("{")
                json_end = response.rindex("}") + 1
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate structure
                if "mutations" in parsed and isinstance(parsed["mutations"], list):
                    return parsed
            
            # If parsing fails, return empty
            return {"mutations": [], "confidence": 0.0, "explanation": "Parsing failed"}
        
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return {"mutations": [], "confidence": 0.0, "explanation": str(e)}
    
    def _fallback_mutation(self, genome: Dict) -> Dict[str, Any]:
        """Fallback mutation when LLM fails"""
        import random
        
        possible_mutations = []
        
        # Database upgrade
        if genome.get("database") == "sqlite":
            possible_mutations.append({
                "field": "database",
                "current_value": "sqlite",
                "suggested_value": "postgres",
                "reason": "Fallback: PostgreSQL for better performance"
            })
        
        # Add caching
        if not genome.get("cache"):
            possible_mutations.append({
                "field": "cache",
                "current_value": False,
                "suggested_value": True,
                "reason": "Fallback: Enable caching for performance"
            })
        
        # Add rate limiting
        if not genome.get("rate_limiting"):
            possible_mutations.append({
                "field": "rate_limiting",
                "current_value": False,
                "suggested_value": True,
                "reason": "Fallback: Add rate limiting for security"
            })
        
        return {
            "mutations": possible_mutations[:2],  # Limit to 2
            "confidence": 0.5,
            "explanation": "Fallback mutations (LLM unavailable)"
        }
    
    def apply_suggested_mutations(
        self,
        genome: Dict[str, Any],
        suggestions: Dict[str, Any],
        acceptance_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Apply LLM-suggested mutations to genome with probabilistic acceptance.
        
        Args:
            genome: Original genome
            suggestions: LLM suggestions
            acceptance_threshold: Minimum confidence to accept (0-1)
        
        Returns:
            Mutated genome
        """
        import random
        
        mutated_genome = genome.copy()
        applied_count = 0
        
        for mutation in suggestions.get("mutations", []):
            confidence = suggestions.get("confidence", 0.5)
            
            # Probabilistic acceptance based on confidence
            if confidence >= acceptance_threshold or random.random() < confidence:
                field = mutation["field"]
                new_value = mutation["suggested_value"]
                
                # Apply mutation
                mutated_genome[field] = new_value
                applied_count += 1
                
                logger.info(
                    f"Applied LLM mutation: {field} = {new_value} "
                    f"(confidence: {confidence:.2f})"
                )
        
        logger.info(f"Applied {applied_count}/{len(suggestions.get('mutations', []))} LLM mutations")
        return mutated_genome
    
    def clear_cache(self):
        """Clear mutation cache"""
        self.mutation_cache.clear()
        logger.info("LLM mutation cache cleared")


# Integration helper for evolution engine
async def llm_guided_crossover_and_mutation(
    parent1: Dict,
    parent2: Dict,
    fitness1: float,
    fitness2: float,
    generation: int,
    llm_mutator: LLMGuidedMutator,
    context: str = ""
) -> Dict:
    """
    Perform crossover followed by LLM-guided mutation.
    
    This is the game-changing combination:
    1. Traditional genetic crossover creates offspring
    2. LLM analyzes offspring and suggests improvements
    3. High-confidence suggestions are applied
    
    Args:
        parent1: First parent genome
        parent2: Second parent genome
        fitness1: Parent 1 fitness
        fitness2: Parent 2 fitness
        generation: Current generation
        llm_mutator: LLM mutator instance
        context: Optimization context
    
    Returns:
        Offspring genome with LLM-guided improvements
    """
    import random
    
    # Step 1: Traditional crossover
    offspring = {}
    for key in parent1.keys():
        # Inherit from fitter parent more often
        if fitness1 > fitness2:
            offspring[key] = parent1[key] if random.random() < 0.7 else parent2[key]
        else:
            offspring[key] = parent2[key] if random.random() < 0.7 else parent1[key]
    
    # Calculate offspring fitness estimate (average of parents)
    estimated_fitness = (fitness1 + fitness2) / 2
    
    # Step 2: LLM-guided mutation
    suggestions = await llm_mutator.suggest_mutations(
        genome=offspring,
        fitness_score=estimated_fitness,
        generation=generation,
        context=context
    )
    
    # Step 3: Apply high-confidence suggestions
    improved_offspring = llm_mutator.apply_suggested_mutations(
        genome=offspring,
        suggestions=suggestions,
        acceptance_threshold=0.7  # Only apply confident suggestions
    )
    
    return improved_offspring
