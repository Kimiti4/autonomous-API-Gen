from typing import Dict, List
from app.core.population import Population
from app.engine.genome import Genome
from app.core.logger import logger


class MultiPopulationSystem:
    """
    Manages multiple specialized populations that evolve with different objectives.
    
    Groups:
    - performance: Optimized for speed and efficiency
    - security: Optimized for security features
    - operations: Optimized for production readiness
    - balanced: Balanced optimization across all metrics
    - minimal: Minimal viable architecture
    """
    
    def __init__(self, population_size: int = 8):
        self.population_size = population_size
        self.groups: Dict[str, Population] = {
            "performance": self._create_performance_population(),
            "security": self._create_security_population(),
            "operations": self._create_operations_population(),
            "balanced": Population(size=population_size),
            "minimal": self._create_minimal_population()
        }
        
        logger.info(f"Multi-population system initialized with {len(self.groups)} groups")
    
    def _create_performance_population(self) -> Population:
        """Create population biased towards performance"""
        genomes = []
        for _ in range(self.population_size):
            genome_data = {
                "services": ["auth", "users"],
                "auth": "jwt",
                "database": "postgres",
                "cache_enabled": True,
                "rate_limiting": True,
                "cors_enabled": True,
                "logging_level": "WARNING",  # Less logging = faster
                "api_version": "v2"
            }
            genomes.append(Genome(genome_data=genome_data))
        
        return Population(genomes=genomes)

    def _create_operations_population(self) -> Population:
        """Create population biased towards production readiness"""
        genomes = []
        for _ in range(self.population_size):
            genome_data = {
                "services": ["auth", "users", "admin"],
                "auth": "oauth2",
                "database": "postgres",
                "cache_enabled": True,
                "rate_limiting": True,
                "cors_enabled": True,
                "logging_level": "INFO",
                "api_version": "v2"
            }
            genomes.append(Genome(genome_data=genome_data))

        return Population(genomes=genomes)
    
    def _create_security_population(self) -> Population:
        """Create population biased towards security"""
        genomes = []
        for _ in range(self.population_size):
            genome_data = {
                "services": ["auth", "users", "payments"],
                "auth": "oauth2",
                "database": "postgres",
                "cache_enabled": True,
                "rate_limiting": True,
                "cors_enabled": True,
                "logging_level": "DEBUG",  # More logging for security
                "api_version": "v2"
            }
            genomes.append(Genome(genome_data=genome_data))
        
        return Population(genomes=genomes)
    
    def _create_minimal_population(self) -> Population:
        """Create population with minimal architectures"""
        genomes = []
        for _ in range(self.population_size):
            genome_data = {
                "services": ["auth"],
                "auth": "api_key",
                "database": "sqlite",
                "cache_enabled": False,
                "rate_limiting": False,
                "cors_enabled": False,
                "logging_level": "ERROR",
                "api_version": "v1"
            }
            genomes.append(Genome(genome_data=genome_data))
        
        return Population(genomes=genomes)
    
    def get_group(self, group_name: str) -> Population:
        """Get a specific population group"""
        if group_name not in self.groups:
            raise ValueError(f"Unknown group: {group_name}")
        return self.groups[group_name]
    
    def get_all_genomes(self) -> List[tuple]:
        """Get all genomes from all groups with their group names"""
        all_genomes = []
        for group_name, population in self.groups.items():
            for genome in population.individuals:
                all_genomes.append((group_name, genome))
        return all_genomes
    
    def update_group(self, group_name: str, new_population: Population):
        """Update a specific group's population"""
        if group_name in self.groups:
            self.groups[group_name] = new_population
    
    def get_group_statistics(self) -> Dict[str, dict]:
        """Get statistics for each group"""
        stats = {}
        for group_name, population in self.groups.items():
            stats[group_name] = {
                "size": population.size(),
                "sample_genome": population.individuals[0].encode() if population.individuals else None
            }
        return stats
    
    def migrate_best(self, source_group: str, target_group: str, num_individuals: int = 1):
        """Migrate best individuals from source to target group"""
        source_pop = self.get_group(source_group)
        target_pop = self.get_group(target_group)
        
        # Get best from source (assuming we have fitness scores)
        # For now, just take first N individuals
        migrants = source_pop.individuals[:num_individuals]
        
        # Add to target (replace worst)
        target_pop.individuals[num_individuals:] = migrants
        
        logger.info(f"Migrated {num_individuals} from {source_group} to {target_group}")
    
    def cross_pollinate(self):
        """Exchange individuals between groups to maintain diversity"""
        group_names = list(self.groups.keys())
        
        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                # Exchange 1 individual between groups
                self.migrate_best(group_names[i], group_names[j], 1)
                self.migrate_best(group_names[j], group_names[i], 1)
        
        logger.info("Cross-pollination completed")
