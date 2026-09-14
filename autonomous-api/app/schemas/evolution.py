"""
Pydantic models for API request/response validation.
Ensures type safety and input validation across all endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class EvolutionRequest(BaseModel):
    """Evolution request. Runtime Docker evaluation is the default research gate."""
    generations: int = Field(default=10, ge=1, le=100, description="Number of evolution generations (1-100)")
    population_size: int = Field(default=10, ge=4, le=50, description="Population size per generation (4-50)")
    use_docker: bool = Field(default=True, description="Run generated candidates in isolated Docker runtime; false explicitly selects static heuristic evaluation")
    seed: Optional[int] = Field(default=None, description="Optional deterministic seed for reproducible evolutionary runs")

    @validator('generations')
    def validate_generations(cls, v):
        if v < 1 or v > 100: raise ValueError("Generations must be between 1 and 100")
        return v

    @validator('population_size')
    def validate_population_size(cls, v):
        if v < 4 or v > 50: raise ValueError("Population size must be between 4 and 50")
        return v

class EliteEvolutionRequest(EvolutionRequest):
    use_multi_population: bool = Field(default=True, description="Use multi-population system with specialized groups")
    enable_adaptive_mutation: bool = Field(default=True, description="Enable adaptive mutation that learns from success")

class EvolutionResponse(BaseModel):
    message: str
    note: Optional[str] = None
    run_id: Optional[str] = None

class EliteEvolutionResponse(EvolutionResponse):
    features: Dict[str, bool] = {}

class EvolutionResult(BaseModel):
    run_id: str
    best_genome: Optional[Dict[str, Any]] = None
    best_fitness: float
    history: Dict[str, List[Dict]] = {}
    output_path: Optional[str] = None
    total_generations: int
    insights: Optional[Dict[str, Any]] = None
    top_features: Optional[List] = None
    memory_stats: Optional[Dict[str, Any]] = None

class GenomeData(BaseModel):
    services: List[str]
    auth: str
    database: str
    cache_enabled: bool
    rate_limiting: bool
    cors_enabled: bool
    logging_level: str
    api_version: str
    security_score: Optional[float] = None

class PatternInsight(BaseModel):
    method: Optional[str] = None
    type: Optional[str] = None
    avg_score: float
    occurrences: int

class InsightsResponse(BaseModel):
    statistics: Dict[str, Any] = {}
    pattern_insights: Dict[str, Any] = {}
    suggested_genome: Optional[Dict[str, Any]] = None
    adaptive_bias: Optional[Dict[str, float]] = None

class ProductionReadinessRequest(BaseModel):
    genome: GenomeData
    deployment_target: str = Field(default="docker_compose", description="Target profile: local, docker_compose, kubernetes, ecs, or enterprise")

class ProductionReadinessResponse(BaseModel):
    status: str
    score: float
    deployment_target: str
    blockers: List[str] = []
    warnings: List[str] = []
    dimensions: List[Dict[str, Any]] = []
    risk_register: List[Dict[str, str]] = []
    recommendations: List[str] = []
    required_capabilities: List[str] = []

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    components: Dict[str, str] = {}
    database: str = "unknown"
    memory_usage: Optional[Dict[str, float]] = None

class ComponentStatus(BaseModel):
    name: str
    status: str
    message: Optional[str] = None
    latency_ms: Optional[float] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None

class ValidationErrorResponse(ErrorResponse):
    field_errors: List[Dict[str, str]] = []

class RunInfo(BaseModel):
    run_id: str
    status: str
    total_generations: int
    best_fitness: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class RunListResponse(BaseModel):
    runs: List[RunInfo]
    total: int
    page: Optional[int] = 1
    page_size: Optional[int] = 50
