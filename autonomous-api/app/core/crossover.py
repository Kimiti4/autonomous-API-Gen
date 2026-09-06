import copy
import random
from app.engine.genome import Genome


# These fields are runtime/derived state rather than evolvable genes.
_NON_GENES = {"genome_id", "metrics"}


def crossover(parent1: Genome, parent2: Genome) -> Genome:
    """Perform uniform crossover across the complete evolvable genome.

    Every persisted gene is inherited from one of the parents. Runtime identity
    and measured production metrics are not inherited. This prevents crossover
    from silently regenerating unrelated genes and makes lineage meaningful.
    """
    p1 = parent1.encode()
    p2 = parent2.encode()

    child_data = {}
    for field in p1.keys() | p2.keys():
        if field in _NON_GENES:
            continue
        if field not in p1:
            value = p2[field]
        elif field not in p2:
            value = p1[field]
        else:
            value = p1[field] if random.random() < 0.5 else p2[field]
        child_data[field] = copy.deepcopy(value)

    child = Genome(genome_data=child_data)
    child.metrics = type(child.metrics)()
    child.lineage = {
        "operator": "uniform_crossover",
        "parent_ids": [parent1.genome_id, parent2.genome_id],
    }
    return child
