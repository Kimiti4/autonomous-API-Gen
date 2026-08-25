import random
from app.engine.genome import Genome


def mutate(genome: Genome, mutation_rate: float = 0.2) -> Genome:
    """
    Apply mutations to a genome with given probability.
    Returns a new mutated genome.
    """
    genome_data = genome.encode()
    
    # Mutate services (add/remove)
    if random.random() < mutation_rate:
        available_services = [
            "auth", "users", "payments", "analytics",
            "notifications", "search", "files", "admin"
        ]
        current = set(genome_data["services"])
        
        if random.random() < 0.5 and len(current) > 2:
            # Remove a service
            service_to_remove = random.choice(list(current))
            current.remove(service_to_remove)
        else:
            # Add a service
            available = set(available_services) - current
            if available:
                current.add(random.choice(list(available)))
        
        genome_data["services"] = list(current)
    
    # Mutate auth method
    if random.random() < mutation_rate:
        auth_options = ["jwt", "oauth2", "api_key", "basic"]
        genome_data["auth"] = random.choice(auth_options)
    
    # Mutate database
    if random.random() < mutation_rate:
        db_options = ["postgres", "sqlite", "mysql"]
        genome_data["database"] = random.choice(db_options)
    
    # Mutate boolean features
    if random.random() < mutation_rate:
        genome_data["cache_enabled"] = not genome_data["cache_enabled"]
    
    if random.random() < mutation_rate:
        genome_data["rate_limiting"] = not genome_data["rate_limiting"]
    
    if random.random() < mutation_rate:
        genome_data["cors_enabled"] = not genome_data["cors_enabled"]
    
    # Mutate logging level
    if random.random() < mutation_rate:
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        genome_data["logging_level"] = random.choice(log_levels)
    
    # Mutate API version
    if random.random() < mutation_rate:
        versions = ["v1", "v2", "v3"]
        genome_data["api_version"] = random.choice(versions)
    
    return Genome(genome_data=genome_data)
