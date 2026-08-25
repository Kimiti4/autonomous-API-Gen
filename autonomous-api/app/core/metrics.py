"""
Prometheus metrics instrumentation for monitoring.
Tracks API performance, evolution runs, and system health.
"""

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge, Summary
import time


# ==================== CUSTOM METRICS ====================

# Evolution Metrics
evolution_runs_total = Counter(
    'evolution_runs_total',
    'Total number of evolution runs',
    ['type', 'status']  # type: standard/elite, status: success/failed
)

evolution_duration_seconds = Histogram(
    'evolution_duration_seconds',
    'Time spent on evolution runs',
    ['type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]  # 1s to 10min
)

generation_fitness = Gauge(
    'generation_best_fitness',
    'Best fitness score per generation',
    ['run_id', 'generation']
)

population_size_gauge = Gauge(
    'population_size',
    'Current population size',
    ['run_id']
)

# Genome Metrics
genome_evaluations_total = Counter(
    'genome_evaluations_total',
    'Total number of genome evaluations'
)

genome_build_success = Counter(
    'genome_build_success_total',
    'Successful genome builds',
    ['service_type']
)

genome_build_failure = Counter(
    'genome_build_failure_total',
    'Failed genome builds',
    ['service_type', 'error_type']
)

# Performance Metrics
api_request_duration = Summary(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

# Learning Metrics
memory_entries = Gauge(
    'memory_entries_total',
    'Total entries in evolution memory'
)

adaptive_bias_values = Gauge(
    'adaptive_mutation_bias',
    'Adaptive mutation bias values',
    ['feature']
)

# Multi-Population Metrics
group_population_size = Gauge(
    'group_population_size',
    'Population size per group',
    ['group_name']
)

group_best_fitness = Gauge(
    'group_best_fitness',
    'Best fitness per group',
    ['group_name']
)

cross_pollination_events = Counter(
    'cross_pollination_events_total',
    'Total cross-pollination events between groups'
)


def setup_metrics(app):
    """
    Set up Prometheus metrics for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add default instrumentation (request count, duration, etc.)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    
    # Custom metrics are already defined above and can be used anywhere


def track_evolution_run(run_type: str, status: str, duration: float):
    """
    Track an evolution run completion.
    
    Args:
        run_type: 'standard' or 'elite'
        status: 'success' or 'failed'
        duration: Run duration in seconds
    """
    evolution_runs_total.labels(type=run_type, status=status).inc()
    evolution_duration_seconds.labels(type=run_type).observe(duration)


def track_generation_fitness(run_id: str, generation: int, fitness: float):
    """
    Track best fitness for a generation.
    
    Args:
        run_id: Unique run identifier
        generation: Generation number
        fitness: Best fitness score
    """
    generation_fitness.labels(run_id=run_id, generation=str(generation)).set(fitness)


def track_genome_evaluation():
    """Track a genome evaluation"""
    genome_evaluations_total.inc()


def track_genome_build(service_type: str, success: bool, error_type: str = None):
    """
    Track genome build result.
    
    Args:
        service_type: Type of service being built
        success: Whether build succeeded
        error_type: Error type if failed
    """
    if success:
        genome_build_success.labels(service_type=service_type).inc()
    else:
        genome_build_failure.labels(
            service_type=service_type,
            error_type=error_type or "unknown"
        ).inc()


def track_api_request(method: str, endpoint: str, duration: float):
    """
    Track API request duration.
    
    Args:
        method: HTTP method
        endpoint: API endpoint path
        duration: Request duration in seconds
    """
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def update_active_connections(count: int):
    """
    Update active WebSocket connection count.
    
    Args:
        count: Number of active connections
    """
    active_connections.set(count)


def update_memory_stats(entries: int):
    """
    Update memory statistics.
    
    Args:
        entries: Total memory entries
    """
    memory_entries.set(entries)


def update_adaptive_bias(feature: str, bias_value: float):
    """
    Update adaptive mutation bias value.
    
    Args:
        feature: Feature name
        bias_value: Bias value (0-1)
    """
    adaptive_bias_values.labels(feature=feature).set(bias_value)


def update_group_metrics(group_name: str, population: int, best_fitness: float):
    """
    Update multi-population group metrics.
    
    Args:
        group_name: Group name (performance/security/balanced/minimal)
        population: Group population size
        best_fitness: Best fitness in group
    """
    group_population_size.labels(group_name=group_name).set(population)
    group_best_fitness.labels(group_name=group_name).set(best_fitness)


def track_cross_pollination():
    """Track a cross-pollination event"""
    cross_pollination_events.inc()
