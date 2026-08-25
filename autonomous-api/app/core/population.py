from typing import List
from app.engine.genome import Genome


class Population:
    """Manages a population of genomes for evolution"""
    
    def __init__(self, size: int = 10, genomes: List[Genome] = None):
        if genomes:
            self.individuals = genomes
        else:
            self.individuals = [Genome() for _ in range(size)]
    
    def size(self) -> int:
        return len(self.individuals)
    
    def get_best(self, fitness_scores: List[float]) -> Genome:
        """Get the genome with highest fitness"""
        if not fitness_scores:
            return self.individuals[0]
        
        best_idx = fitness_scores.index(max(fitness_scores))
        return self.individuals[best_idx]
    
    def select_parents(self, fitness_scores: List[float], num_parents: int = 2) -> List[Genome]:
        """Tournament selection of parents based on fitness"""
        if len(fitness_scores) != len(self.individuals):
            raise ValueError("Fitness scores length must match population size")
        
        # Create list of (genome, fitness) pairs
        paired = list(zip(self.individuals, fitness_scores))
        
        # Sort by fitness (descending)
        paired.sort(key=lambda x: x[1], reverse=True)
        
        # Select top individuals as parents
        parents = [p[0] for p in paired[:num_parents]]
        return parents
    
    def replace(self, new_individuals: List[Genome]):
        """Replace current population with new individuals"""
        self.individuals = new_individuals
    
    def to_dict(self) -> dict:
        """Convert population to dictionary for serialization"""
        return {
            "size": self.size(),
            "individuals": [g.encode() for g in self.individuals]
        }
