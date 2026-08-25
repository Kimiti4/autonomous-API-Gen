import random
from app.engine.genome import Genome


def crossover(parent1: Genome, parent2: Genome) -> Genome:
    """
    Perform crossover between two parent genomes to create a child.
    Uses uniform crossover for most genes.
    """
    child_data = {}
    
    # Services: take first half from parent1, second half from parent2
    all_services = list(set(parent1.services + parent2.services))
    random.shuffle(all_services)
    num_services = random.randint(2, min(5, len(all_services)))
    child_data["services"] = all_services[:num_services]
    
    # Auth: randomly choose from parents
    child_data["auth"] = random.choice([parent1.auth, parent2.auth])
    
    # Database: randomly choose from parents
    child_data["database"] = random.choice([parent1.database, parent2.database])
    
    # Boolean features: 50% chance from each parent
    child_data["cache_enabled"] = random.choice([parent1.cache_enabled, parent2.cache_enabled])
    child_data["rate_limiting"] = random.choice([parent1.rate_limiting, parent2.rate_limiting])
    child_data["cors_enabled"] = random.choice([parent1.cors_enabled, parent2.cors_enabled])
    
    # Logging and version: randomly choose
    child_data["logging_level"] = random.choice([parent1.logging_level, parent2.logging_level])
    child_data["api_version"] = random.choice([parent1.api_version, parent2.api_version])
    
    child_data["security_score"] = 1.0
    
    return Genome(genome_data=child_data)
