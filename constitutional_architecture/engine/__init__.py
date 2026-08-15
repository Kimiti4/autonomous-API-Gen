"""
Evolution Engine 2.0 — Constitutional Architecture Platform.

This engine evolves software architectures represented as immutable ISR graphs.
It operates EXCLUSIVELY on ISR objects. It contains ZERO framework-specific knowledge.
"""

from constitutional_architecture.engine.evolution_engine import EvolutionEngine
from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.individual import Individual
from constitutional_architecture.engine.fitness import FitnessVector

__all__ = [
    "EvolutionEngine",
    "EvolutionConfig",
    "Individual",
    "FitnessVector",
]
