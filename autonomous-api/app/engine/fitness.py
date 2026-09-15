from app.engine.genome import Genome
from app.engine.security import calculate_security_score
from app.engine.production_analyzers import ProductionFitnessScorer
from app.engine.capability_contract import implementation_report, verified_feature


def _calculate_performance_score(genome: Genome) -> float:
    """Score only performance capabilities that the builder actually implements."""
    score = 0.0
    if verified_feature(genome, "cache"):
        score += 0.4
    if verified_feature(genome, "circuit_breaker"):
        score += 0.3
    if verified_feature(genome, "tracing"):
        score += 0.2
    if verified_feature(genome, "backends"):
        score += 0.1
    if verified_feature(genome, "timeout_config"):
        score += 0.1
    return min(score, 1.0)


def _calculate_best_practices_score(genome: Genome) -> float:
    """Score only best-practice capabilities that are actually generated."""
    score = 0.0
    if verified_feature(genome, "rate_limiting"):
        score += 0.35
    if verified_feature(genome, "cors"):
        score += 0.25
    if verified_feature(genome, "logging_level"):
        score += 0.2
    if verified_feature(genome, "health_endpoints"):
        score += 0.1
    if verified_feature(genome, "metrics_endpoints"):
        score += 0.1
    return min(score, 1.0)


def _calculate_database_score(genome: Genome) -> float:
    db_scores = {"postgres": 1.0, "mysql": 0.9, "sqlite": 0.4}
    return db_scores.get(genome.database, 0.5) if verified_feature(genome, "database") else 0.0


def calculate_fitness(genome: Genome) -> float:
    """Calculate scalar evolutionary fitness with fail-closed capability accounting."""
    fitness = 0.0
    security = calculate_security_score(genome) if verified_feature(genome, "authentication") else 0.0
    fitness += security * 0.15

    architecture_score = min(len(genome.services) / 6.0, 1.0) if verified_feature(genome, "services") else 0.0
    fitness += architecture_score * 0.10
    fitness += _calculate_performance_score(genome) * 0.15
    fitness += _calculate_best_practices_score(genome) * 0.10
    fitness += _calculate_database_score(genome) * 0.05

    production_metrics = ProductionFitnessScorer().score_genome(genome)
    production_score = production_metrics["production_score"]
    fitness += production_score * 0.30
    return round(fitness, 3)


def calculate_production_fitness(genome: Genome) -> dict:
    production_metrics = ProductionFitnessScorer().score_genome(genome)
    component_scores = {
        "security": calculate_security_score(genome) if verified_feature(genome, "authentication") else 0.0,
        "architecture": min(len(genome.services) / 6.0, 1.0) if verified_feature(genome, "services") else 0.0,
        "performance": _calculate_performance_score(genome),
        "best_practices": _calculate_best_practices_score(genome),
        "database_quality": _calculate_database_score(genome),
        "production_metrics": production_metrics["production_score"],
    }
    total_fitness = sum(score * weight for score, weight in [
        (component_scores["security"], 0.15),
        (component_scores["architecture"], 0.10),
        (component_scores["performance"], 0.15),
        (component_scores["best_practices"], 0.10),
        (component_scores["database_quality"], 0.05),
        (component_scores["production_metrics"], 0.30),
    ])
    return {
        "total_fitness": round(total_fitness, 3),
        "component_scores": component_scores,
        "production_metrics": production_metrics,
        "capability_report": implementation_report(genome),
        "recommendations": production_metrics.get("recommendations", []),
    }


def rank_genomes_by_fitness(genomes: list, top_n: int = 10) -> list:
    return sorted(((genome, calculate_fitness(genome)) for genome in genomes), key=lambda x: x[1], reverse=True)[:top_n]


def pareto_front_analysis(genomes: list) -> dict:
    objectives = ["fitness", "cost", "performance", "security", "complexity"]
    objective_scores = []
    for genome in genomes:
        scores = {
            "fitness": calculate_fitness(genome),
            "cost": _calculate_cost_score(genome),
            "performance": _calculate_performance_score(genome),
            "security": calculate_security_score(genome) if verified_feature(genome, "authentication") else 0.0,
            "complexity": _calculate_complexity_score(genome),
        }
        objective_scores.append((genome, scores))

    pareto_front = []
    for i, (genome1, scores1) in enumerate(objective_scores):
        if not any(i != j and all(scores2[obj] >= scores1[obj] for obj in objectives)
                   for j, (_, scores2) in enumerate(objective_scores)):
            pareto_front.append((genome1, scores1))
    return {"pareto_front": pareto_front, "total_genomes": len(genomes), "pareto_count": len(pareto_front), "objectives": objectives}


def _calculate_cost_score(genome: Genome) -> float:
    cost = ProductionFitnessScorer()._estimate_cloud_cost(genome)
    return max(0.0, 1.0 - min(cost / 1000.0, 1.0))


def _calculate_complexity_score(genome: Genome) -> float:
    complexity = len(genome.services) + len(genome.backends) + len(genome.middleware)
    return max(0.0, 1.0 - min(complexity / 20.0, 1.0))
