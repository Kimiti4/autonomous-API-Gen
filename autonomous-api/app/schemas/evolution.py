"""
Pydantic models for API request/response validation.
Ensures type safety and input validation across all endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== EVOLUTION REQUESTS ====================

class EvolutionRequest(BaseModel):
    """Base evolution request model"""
    generations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of evolution generations (1-100)"
    )
    population_size: int = Field(
        default=10,
        ge=4,
        le=50,
        description="Population size per generation (4-50)"
    )
    use_docker: bool = Field(
        default=False,
        description="Whether to build and test with Docker"
    )
    
    @validator('generations')
    def validate_generations(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Generations must be between 1 and 100")
        return v
    
    @validator('population_size')
    def validate_population_size(cls, v):
        if v < 4 or v > 50:
            raise ValueError("Population size must be between 4 and 50")
        return v


class EliteEvolutionRequest(EvolutionRequest):
    """Elite evolution request with advanced options"""
    use_multi_population: bool = Field(
        default=True,
        description="Use multi-population system with specialized groups"
    )
    enable_adaptive_mutation: bool = Field(
        default=True,
        description="Enable adaptive mutation that learns from success"
    )


# ==================== EVOLUTION RESPONSES ====================

class EvolutionResponse(BaseModel):
    """Standard evolution response"""
    message: str
    note: Optional[str] = None
    run_id: Optional[str] = None


class EliteEvolutionResponse(EvolutionResponse):
    """Elite evolution response with feature details"""
    features: Dict[str, bool] = {}


class EvolutionResult(BaseModel):
    """Complete evolution result"""
    run_id: str
    best_genome: Optional[Dict[str, Any]] = None
    best_fitness: float
    history: Dict[str, List[Dict]] = {}
    output_path: Optional[str] = None
    total_generations: int
    insights: Optional[Dict[str, Any]] = None
    top_features: Optional[List] = None
    memory_stats: Optional[Dict[str, Any]] = None


# ==================== GENOME & INSIGHTS ====================

class GenomeData(BaseModel):
    """Genome configuration data"""
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
    """Pattern analysis insight"""
    method: Optional[str] = None
    type: Optional[str] = None
    avg_score: float
    occurrences: int


class InsightsResponse(BaseModel):
    """Learning insights response"""
    statistics: Dict[str, Any] = {}
    pattern_insights: Dict[str, Any] = {}
    suggested_genome: Optional[Dict[str, Any]] = None
    adaptive_bias: Optional[Dict[str, float]] = None


# ==================== PRODUCTION READINESS ====================

class ProductionReadinessRequest(BaseModel):
    """Analyze whether a genome is ready for a production deployment target"""
    genome: GenomeData
    deployment_target: str = Field(
        default="docker_compose",
        description="Target profile: local, docker_compose, kubernetes, ecs, or enterprise"
    )


class ProductionReadinessResponse(BaseModel):
    """Production readiness gate report for a genome"""
    status: str
    score: float
    deployment_target: str
    blockers: List[str] = []
    warnings: List[str] = []
    dimensions: List[Dict[str, Any]] = []
    risk_register: List[Dict[str, str]] = []
    recommendations: List[str] = []
    required_capabilities: List[str] = []


# ==================== HEALTH & STATUS ====================

class HealthCheckResponse(BaseModel):
    """System health check response"""
    status: str
    version: str
    timestamp: str
    components: Dict[str, str] = {}
    database: str = "unknown"
    memory_usage: Optional[Dict[str, float]] = None


class ComponentStatus(BaseModel):
    """Individual component status"""
    name: str
    status: str
    message: Optional[str] = None
    latency_ms: Optional[float] = None


# ==================== ERROR RESPONSES ====================

class ErrorResponse(BaseModel):
    """Standardized error response"""
    error: str
    message: str
    details: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None


class ValidationErrorResponse(ErrorResponse):
    """Validation error with field details"""
    field_errors: List[Dict[str, str]] = []


# ==================== RUN HISTORY ====================

class RunInfo(BaseModel):
    """Evolution run information"""
    run_id: str
    status: str
    total_generations: int
    best_fitness: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class RunListResponse(BaseModel):
    """List of evolution runs"""
    runs: List[RunInfo]
    total: int
    page: Optional[int] = 1
    page_size: Optional[int] = 50
