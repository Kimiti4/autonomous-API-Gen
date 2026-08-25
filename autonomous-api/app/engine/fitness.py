from app.engine.genome import Genome
from app.engine.security import calculate_security_score
from app.engine.production_analyzers import ProductionFitnessScorer


def calculate_fitness(genome: Genome) -> float:
    """
    Enhanced multi-objective fitness function that evaluates genome quality
    with comprehensive production fitness scoring.

    Fitness components:
    - Security (15%): Authentication and security features
    - Architecture (10%): Service composition and complexity
    - Performance (15%): Caching and optimization
    - Best Practices (10%): Rate limiting, logging, CORS
    - Database Choice (5%): Production-ready databases
    - OpenAPI Completeness (10%): API documentation quality
    - Auth Coverage (10%): Authentication coverage
    - Migration Safety (5%): Migration compatibility
    - Observability (5%): Monitoring and tracing
    - Cost Efficiency (5%): Cloud cost optimization

    Returns a fitness score (higher is better).
    """
    fitness = 0.0

    # 1. Security Score (weight: 0.15)
    security = calculate_security_score(genome)
    fitness += security * 0.15

    # 2. Architecture Richness (weight: 0.10)
    # More services = more complex architecture (up to a point)
    num_services = len(genome.services)
    architecture_score = min(num_services / 6.0, 1.0)  # Normalize to max 6 services
    fitness += architecture_score * 0.10

    # 3. Performance Features (weight: 0.15)
    performance_score = 0.0
    if genome.cache_enabled:
        performance_score += 0.5
    if genome.circuit_breaker:
        performance_score += 0.3
    if genome.tracing_enabled:
        performance_score += 0.2
    fitness += performance_score * 0.15

    # 4. Best Practices (weight: 0.10)
    best_practices_score = 0.0
    if genome.rate_limiting:
        best_practices_score += 0.4
    if genome.cors_enabled:
        best_practices_score += 0.3
    if genome.logging_level in ["INFO", "WARNING"]:  # Good production levels
        best_practices_score += 0.2
    if genome.health_endpoints:
        best_practices_score += 0.1
    fitness += best_practices_score * 0.10

    # 5. Database Quality (weight: 0.05)
    db_scores = {
        "postgres": 1.0,   # Production-grade
        "mysql": 0.9,      # Production-grade
        "sqlite": 0.4      # Development/testing
    }
    db_score = db_scores.get(genome.database, 0.5)
    fitness += db_score * 0.05

    # 6. Production Fitness Score (weight: 0.30)
    # Calculate comprehensive production metrics
    fitness_scorer = ProductionFitnessScorer()
    production_metrics = fitness_scorer.score_genome(genome)
    production_score = production_metrics["production_score"]
    fitness += production_score * 0.30

    return round(fitness, 3)


def calculate_production_fitness(genome: Genome) -> dict:
    """
    Calculate detailed production fitness score with all metrics.
    
    Args:
        genome: The genome to evaluate
        
    Returns:
        Dictionary with detailed fitness breakdown
    """
    fitness_scorer = ProductionFitnessScorer()
    production_metrics = fitness_scorer.score_genome(genome)
    
    # Calculate component scores
    component_scores = {
        "security": calculate_security_score(genome),
        "architecture": min(len(genome.services) / 6.0, 1.0),
        "performance": _calculate_performance_score(genome),
        "best_practices": _calculate_best_practices_score(genome),
        "database_quality": _calculate_database_score(genome),
        "production_metrics": production_metrics["production_score"]
    }
    
    # Calculate weighted total
    total_fitness = sum(
        score * weight 
        for score, weight in [
            (component_scores["security"], 0.15),
            (component_scores["architecture"], 0.10),
            (component_scores["performance"], 0.15),
            (component_scores["best_practices"], 0.10),
            (component_scores["database_quality"], 0.05),
            (component_scores["production_metrics"], 0.30)
        ]
    )
    
    return {
        "total_fitness": round(total_fitness, 3),
        "component_scores": component_scores,
        "production_metrics": production_metrics,
        "recommendations": production_metrics.get("recommendations", [])
    }


def _calculate_performance_score(genome: Genome) -> float:
    """Calculate performance component score"""
    score = 0.0
    
    if genome.cache_enabled:
        score += 0.4
    if genome.circuit_breaker:
        score += 0.3
    if genome.tracing_enabled:
        score += 0.2
    if len(genome.backends) > 0:
        score += 0.1
        
    return min(score, 1.0)


def _calculate_best_practices_score(genome: Genome) -> float:
    """Calculate best practices component score"""
    score = 0.0
    
    if genome.rate_limiting:
        score += 0.35
    if genome.cors_enabled:
        score += 0.25
    if genome.logging_level in ["INFO", "WARNING"]:
        score += 0.2
    if genome.health_endpoints:
        score += 0.1
    if genome.metrics_endpoints:
        score += 0.1
        
    return min(score, 1.0)


def _calculate_database_score(genome: Genome) -> float:
    """Calculate database quality component score"""
    db_scores = {
        "postgres": 1.0,
        "mysql": 0.9,
        "sqlite": 0.4
    }
    return db_scores.get(genome.database, 0.5)


def rank_genomes_by_fitness(genomes: list, top_n: int = 10) -> list:
    """
    Rank genomes by fitness score and return top N candidates.
    
    Args:
        genomes: List of genomes to rank
        top_n: Number of top genomes to return
        
    Returns:
        List of (genome, fitness_score) tuples sorted by fitness
    """
    fitness_scores = []
    
    for genome in genomes:
        fitness_score = calculate_fitness(genome)
        fitness_scores.append((genome, fitness_score))
    
    # Sort by fitness score (descending)
    fitness_scores.sort(key=lambda x: x[1], reverse=True)
    
    return fitness_scores[:top_n]


def pareto_front_analysis(genomes: list) -> dict:
    """
    Perform multi-objective Pareto front analysis.
    
    Args:
        genomes: List of genomes to analyze
        
    Returns:
        Dictionary with Pareto front analysis results
    """
    objectives = ["fitness", "cost", "performance", "security", "complexity"]
    
    # Calculate objective scores for each genome
    objective_scores = []
    for genome in genomes:
        scores = {
            "fitness": calculate_fitness(genome),
            "cost": _calculate_cost_score(genome),
            "performance": _calculate_performance_score(genome),
            "security": calculate_security_score(genome),
            "complexity": _calculate_complexity_score(genome)
        }
        objective_scores.append((genome, scores))
    
    # Find Pareto front
    pareto_front = []
    for i, (genome1, scores1) in enumerate(objective_scores):
        dominated = False
        for j, (genome2, scores2) in enumerate(objective_scores):
            if i != j and all(scores2[obj] >= scores1[obj] for obj in objectives):
                dominated = True
                break
        if not dominated:
            pareto_front.append((genome1, scores1))
    
    return {
        "pareto_front": pareto_front,
        "total_genomes": len(genomes),
        "pareto_count": len(pareto_front),
        "objectives": objectives
    }


def _calculate_cost_score(genome: Genome) -> float:
    """Calculate cost optimization score (lower cost = higher score)"""
    cost_scorer = ProductionFitnessScorer()
    cost = cost_scorer._estimate_cloud_cost(genome)
    # Normalize cost to 0-1 scale (assuming max reasonable cost of $1000)
    return max(0.0, 1.0 - min(cost / 1000.0, 1.0))


def _calculate_complexity_score(genome: Genome) -> float:
    """Calculate complexity score (lower complexity = higher score)"""
    complexity = len(genome.services) + len(genome.backends) + len(genome.middleware)
    # Normalize complexity to 0-1 scale (assuming max reasonable complexity of 20)
    return max(0.0, 1.0 - min(complexity / 20.0, 1.0))
