from typing import List
from app.engine.genome import Genome
from app.engine.fitness import pareto_front_analysis


class Population:
    """Manages a population of genomes for evolutionary search."""

    def __init__(self, size: int = 10, genomes: List[Genome] = None):
        if size < 1 and not genomes:
            raise ValueError("population size must be positive")
        self.individuals = genomes if genomes is not None else [Genome() for _ in range(size)]

    def size(self) -> int:
        return len(self.individuals)

    def get_best(self, fitness_scores: List[float]) -> Genome:
        if not fitness_scores:
            return self.individuals[0]
        return self.individuals[fitness_scores.index(max(fitness_scores))]

    def select_parents(self, fitness_scores: List[float], num_parents: int = 2) -> List[Genome]:
        """Select parents from the current Pareto front, then scalar-rank ties.

        The scalar fitness remains a deterministic tie-breaker, but dominance
        across security, performance, cost, and complexity now determines the
        primary candidate set.
        """
        if len(fitness_scores) != len(self.individuals):
            raise ValueError("Fitness scores length must match population size")
        if num_parents < 1:
            raise ValueError("num_parents must be positive")

        analysis = pareto_front_analysis(self.individuals)
        front_ids = {genome.genome_id for genome, _ in analysis["pareto_front"]}
        ranked = sorted(
            enumerate(self.individuals),
            key=lambda item: (item[1].genome_id in front_ids, fitness_scores[item[0]]),
            reverse=True,
        )
        return [genome for _, genome in ranked[:min(num_parents, len(ranked))]]

    def replace(self, new_individuals: List[Genome]):
        if not new_individuals:
            raise ValueError("population cannot be empty")
        self.individuals = new_individuals

    def to_dict(self) -> dict:
        return {
            "size": self.size(),
            "individuals": [g.encode() for g in self.individuals],
        }
