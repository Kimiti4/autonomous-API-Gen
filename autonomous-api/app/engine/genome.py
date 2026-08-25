import random
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ServiceBlueprint:
    """Represents a reusable service blueprint"""
    name: str
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    observability: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    performance_score: float = 0.0


@dataclass
class ProductionMetrics:
    """Production fitness scoring metrics"""
    openapi_completeness: float = 0.0
    auth_coverage: float = 0.0
    migration_safety: float = 0.0
    observability_coverage: float = 0.0
    latency_estimate: float = 0.0
    error_budget_estimate: float = 0.0
    dependency_risk: float = 0.0
    cloud_cost_estimate: float = 0.0
    test_coverage_score: float = 0.0
    security_score: float = 0.0
    architecture_complexity: float = 0.0
    performance_score: float = 0.0


class Genome:
    """
    Represents the DNA of an API system.
    Encodes architectural decisions as evolvable genes.
    Enhanced with production fitness scoring capabilities.
    """

    def __init__(self, genome_data: Dict[str, Any] = None):
        self.genome_id = str(uuid.uuid4())
        self.metrics = ProductionMetrics()
        self.blueprints_used: List[str] = []
        self.deployment_target: str = "docker-compose"
        self.policies_applied: List[str] = []
        
        # Original basic properties
        if genome_data:
            # Load from existing data
            self.services = genome_data.get("services", [])
            self.auth = genome_data.get("auth", "jwt")
            self.database = genome_data.get("database", "postgres")
            self.cache_enabled = genome_data.get("cache_enabled", False)
            self.rate_limiting = genome_data.get("rate_limiting", False)
            self.cors_enabled = genome_data.get("cors_enabled", True)
            self.logging_level = genome_data.get("logging_level", "INFO")
            self.api_version = genome_data.get("api_version", "v1")
            self.security_score = genome_data.get("security_score", 1.0)
            
            # Load production features
            self.openapi_version = genome_data.get("openapi_version", "3.0.0")
            self.health_endpoints = genome_data.get("health_endpoints", True)
            self.metrics_endpoints = genome_data.get("metrics_endpoints", True)
            self.tracing_enabled = genome_data.get("tracing_enabled", False)
            self.circuit_breaker = genome_data.get("circuit_breaker", False)
            self.retry_policy = genome_data.get("retry_policy", {})
            self.timeout_config = genome_data.get("timeout_config", {})
            self.backends = genome_data.get("backends", [])
            self.middleware = genome_data.get("middleware", [])
            self.security_policies = genome_data.get("security_policies", [])
            
            # Load metrics if available
            metrics_data = genome_data.get("metrics")
            if metrics_data:
                self.metrics = ProductionMetrics(**metrics_data)
                
            # Load blueprints and policies
            self.blueprints_used = genome_data.get("blueprints_used", [])
            self.policies_applied = genome_data.get("policies_applied", [])
            self.deployment_target = genome_data.get("deployment_target", "docker-compose")
            
        else:
            # Generate random genome with enhanced features
            self._generate_random_genome()

    def _generate_random_genome(self):
        """Generate random genome with production features"""
        # Basic properties
        self.services = self._random_services()
        self.auth = random.choice(["jwt", "oauth2", "api_key", "basic"])
        self.database = random.choice(["postgres", "sqlite", "mysql"])
        self.cache_enabled = random.choice([True, False])
        self.rate_limiting = random.choice([True, False])
        self.cors_enabled = random.choice([True, False])
        self.logging_level = random.choice(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.api_version = random.choice(["v1", "v2", "v3"])
        self.security_score = 1.0
        
        # Enhanced production features
        self.openapi_version = random.choice(["3.0.0", "3.1.0"])
        self.health_endpoints = random.choice([True, False])
        self.metrics_endpoints = random.choice([True, False])
        self.tracing_enabled = random.choice([True, False])
        self.circuit_breaker = random.choice([True, False])
        
        # Configurations
        self.retry_policy = self._generate_retry_policy()
        self.timeout_config = self._generate_timeout_config()
        self.backends = self._generate_backends()
        self.middleware = self._generate_middleware()
        self.security_policies = self._generate_security_policies()

    def _random_services(self) -> List[str]:
        """Generate random microservice architecture"""
        available_services = [
            "auth", "users", "payments", "analytics",
            "notifications", "search", "files", "admin",
            "products", "orders", "inventory", "reports"
        ]
        num_services = random.randint(2, 6)
        return random.sample(available_services, num_services)

    def _generate_retry_policy(self) -> Dict[str, Any]:
        """Generate retry policy configuration"""
        return {
            "max_attempts": random.randint(2, 5),
            "base_delay": random.uniform(0.1, 2.0),
            "max_delay": random.uniform(5.0, 30.0),
            "backoff_multiplier": random.uniform(1.5, 3.0)
        }

    def _generate_timeout_config(self) -> Dict[str, Any]:
        """Generate timeout configuration"""
        return {
            "connect_timeout": random.uniform(5.0, 30.0),
            "read_timeout": random.uniform(10.0, 60.0),
            "write_timeout": random.uniform(10.0, 60.0),
            "request_timeout": random.uniform(30.0, 120.0)
        }

    def _generate_backends(self) -> List[Dict[str, Any]]:
        """Generate backend configurations"""
        backends = []
        if self.cache_enabled:
            backends.append({
                "type": "cache",
                "implementation": random.choice(["redis", "memcached"]),
                "connection_pool_size": random.randint(5, 20)
            })
        
        if len(self.services) > 3:
            backends.append({
                "type": "message_queue",
                "implementation": random.choice(["rabbitmq", "kafka"]),
                "partitions": random.randint(1, 8)
            })
        
        return backends

    def _generate_middleware(self) -> List[str]:
        """Generate middleware stack"""
        available_middleware = [
            "auth", "caching", "logging", "tracing",
            "rate_limiting", "circuit_breaker", "retry",
            "compression", "cors", "security_headers"
        ]
        return random.sample(available_middleware, random.randint(2, 6))

    def _generate_security_policies(self) -> List[Dict[str, Any]]:
        """Generate security policies"""
        policies = []
        if self.auth == "jwt":
            policies.append({
                "type": "jwt_validation",
                "algorithm": random.choice(["HS256", "RS256"]),
                "expiration_minutes": random.randint(60, 1440)
            })
        if self.rate_limiting:
            policies.append({
                "type": "rate_limiting",
                "requests_per_minute": random.randint(10, 100),
                "burst_size": random.randint(5, 50)
            })
        return policies

    def encode(self) -> Dict[str, Any]:
        """Encode genome to dictionary for serialization"""
        return {
            "genome_id": self.genome_id,
            "services": self.services,
            "auth": self.auth,
            "database": self.database,
            "cache_enabled": self.cache_enabled,
            "rate_limiting": self.rate_limiting,
            "cors_enabled": self.cors_enabled,
            "logging_level": self.logging_level,
            "api_version": self.api_version,
            "security_score": self.security_score,
            # Enhanced production features
            "openapi_version": self.openapi_version,
            "health_endpoints": self.health_endpoints,
            "metrics_endpoints": self.metrics_endpoints,
            "tracing_enabled": self.tracing_enabled,
            "circuit_breaker": self.circuit_breaker,
            "retry_policy": self.retry_policy,
            "timeout_config": self.timeout_config,
            "backends": self.backends,
            "middleware": self.middleware,
            "security_policies": self.security_policies,
            "metrics": self.metrics.__dict__,
            "blueprints_used": self.blueprints_used,
            "policies_applied": self.policies_applied,
            "deployment_target": self.deployment_target
        }

    def decode(self, data: Dict[str, Any]):
        """Decode dictionary back to genome"""
        self.services = data.get("services", self.services)
        self.auth = data.get("auth", self.auth)
        self.database = data.get("database", self.database)
        self.cache_enabled = data.get("cache_enabled", self.cache_enabled)
        self.rate_limiting = data.get("rate_limiting", self.rate_limiting)
        self.cors_enabled = data.get("cors_enabled", self.cors_enabled)
        self.logging_level = data.get("logging_level", self.logging_level)
        self.api_version = data.get("api_version", self.api_version)
        self.security_score = data.get("security_score", self.security_score)
        
        # Enhanced production features
        self.openapi_version = data.get("openapi_version", "3.0.0")
        self.health_endpoints = data.get("health_endpoints", True)
        self.metrics_endpoints = data.get("metrics_endpoints", True)
        self.tracing_enabled = data.get("tracing_enabled", False)
        self.circuit_breaker = data.get("circuit_breaker", False)
        self.retry_policy = data.get("retry_policy", {})
        self.timeout_config = data.get("timeout_config", {})
        self.backends = data.get("backends", [])
        self.middleware = data.get("middleware", [])
        self.security_policies = data.get("security_policies", [])
        
        # Load metrics
        metrics_data = data.get("metrics")
        if metrics_data:
            self.metrics = ProductionMetrics(**metrics_data)
            
        # Load blueprints and policies
        self.blueprints_used = data.get("blueprints_used", [])
        self.policies_applied = data.get("policies_applied", [])
        self.deployment_target = data.get("deployment_target", "docker-compose")

    def get_production_score(self) -> float:
        """Calculate overall production fitness score"""
        score = 0.0
        
        # Weight each metric
        weights = {
            "openapi_completeness": 0.10,
            "auth_coverage": 0.15,
            "migration_safety": 0.08,
            "observability_coverage": 0.12,
            "latency_estimate": 0.10,
            "error_budget_estimate": 0.10,
            "dependency_risk": 0.10,  # Inverted (lower risk = higher score)
            "cloud_cost_estimate": 0.05,  # Inverted (lower cost = higher score)
            "test_coverage_score": 0.10,
            "security_score": 0.10
        }
        
        for metric, weight in weights.items():
            value = getattr(self.metrics, metric, 0.0)
            if metric in ["dependency_risk", "cloud_cost_estimate"]:
                # Inverted metrics where lower values are better
                score += (1.0 - min(value, 1.0)) * weight
            else:
                score += value * weight
                
        return round(score, 3)

    def __repr__(self):
        return f"Genome(id={self.genome_id[:8]}, services={self.services}, auth={self.auth}, production_score={self.get_production_score()})"
