"""
Meta-Evolution Engine — Constitutional Architecture Evolutionary Software Platform.

Evolves the PLATFORM itself. Not user software.

The Meta-Evolution Engine optimizes:
- Mutation strategies and operator weights
- Fitness function parameters
- Compiler pass configuration
- Verification thresholds
- Deployment strategies
- Scheduling policies
- Knowledge retrieval strategies
- Agent collaboration parameters
- Platform performance targets

Constitutional constraints:
1. The Meta-Evolution Engine evolves the PLATFORM, not user software.
2. It NEVER modifies constitutional layers.
3. It requires verification before platform changes take effect.
4. It supports rollback of platform mutations.
5. It preserves compatibility with existing ISRs.
6. It maintains complete lineage for every platform evolution.
7. It operates on a Platform Genome that encodes tunable parameters.
"""

from constitutional_architecture.meta.meta_evolution_engine import MetaEvolutionEngine
from constitutional_architecture.meta.platform_genome import PlatformGenome, GenomeParameter
from constitutional_architecture.meta.platform_fitness import PlatformFitness, PlatformFitnessEvaluator
from constitutional_architecture.meta.safety_gate import SafetyGate

__all__ = [
    "MetaEvolutionEngine",
    "PlatformGenome",
    "GenomeParameter",
    "PlatformFitness",
    "PlatformFitnessEvaluator",
    "SafetyGate",
]
