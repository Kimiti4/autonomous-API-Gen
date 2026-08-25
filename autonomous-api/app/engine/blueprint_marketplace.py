"""
Service Blueprint Marketplace
=============================

This module implements a marketplace of reusable service blueprints that can be
used to accelerate and standardize API generation.
"""

import json
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from app.engine.genome import Genome, ServiceBlueprint


class BlueprintCategory(Enum):
    """Categories of service blueprints"""
    AUTHENTICATION = "authentication"
    USER_MANAGEMENT = "user_management"
    PAYMENT_PROCESSING = "payment_processing"
    NOTIFICATIONS = "notifications"
    ANALYTICS = "analytics"
    FILE_MANAGEMENT = "file_management"
    SEARCH_ENGINEERING = "search_engineering"
    ADMIN_DASHBOARD = "admin_dashboard"
    API_GATEWAY = "api_gateway"
    MESSAGE_QUEUE = "message_queue"


class BlueprintComplexity(Enum):
    """Complexity levels of blueprints"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


@dataclass
class ServiceBlueprint:
    """Enhanced service blueprint with comprehensive production features"""
    blueprint_id: str
    name: str
    description: str
    category: BlueprintCategory
    complexity: BlueprintComplexity
    version: str
    author: str
    organization: str
    tags: List[str] = field(default_factory=list)
    
    # Core service configuration
    services: List[str] = field(default_factory=list)
    auth_methods: List[str] = field(default_factory=list)
    database_type: str = "postgres"
    cache_enabled: bool = True
    rate_limiting: bool = True
    
    # Endpoints and API design
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    api_version: str = "v1"
    openapi_spec: Dict[str, Any] = field(default_factory=dict)
    
    # Security features
    security_features: List[Dict[str, Any]] = field(default_factory=list)
    auth_requirements: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)
    
    # Performance and scalability
    performance_features: List[str] = field(default_factory=list)
    scalability_features: List[str] = field(default_factory=list)
    caching_strategy: Dict[str, Any] = field(default_factory=dict)
    
    # Observability
    monitoring_endpoints: List[str] = field(default_factory=list)
    logging_configuration: Dict[str, Any] = field(default_factory=dict)
    tracing_enabled: bool = True
    
    # Testing
    test_suites: List[Dict[str, Any]] = field(default_factory=list)
    test_coverage: float = 0.0
    
    # Deployment
    deployment_config: Dict[str, Any] = field(default_factory=dict)
    docker_config: Dict[str, Any] = field(default_factory=dict)
    kubernetes_config: Dict[str, Any] = field(default_factory=dict)
    
    # Cost and performance estimates
    estimated_monthly_cost: float = 0.0
    estimated_requests_per_second: float = 0.0
    estimated_latency_ms: float = 0.0
    reliability_score: float = 0.0
    
    # Usage statistics
    usage_count: int = 0
    success_rate: float = 0.0
    average_rating: float = 0.0
    user_ratings: List[int] = field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    is_verified: bool = False
    is_featured: bool = False
    download_count: int = 0
    
    def to_genome_config(self) -> Dict[str, Any]:
        """Convert blueprint to genome configuration"""
        return {
            "services": self.services,
            "auth": self.auth_methods[0] if self.auth_methods else "jwt",
            "database": self.database_type,
            "cache_enabled": self.cache_enabled,
            "rate_limiting": self.rate_limiting,
            "cors_enabled": True,
            "logging_level": "INFO",
            "api_version": self.api_version,
            "openapi_version": "3.0.0",
            "health_endpoints": True,
            "metrics_endpoints": True,
            "tracing_enabled": self.tracing_enabled,
            "circuit_breaker": "circuit_breaker" in self.performance_features,
            "retry_policy": {"max_attempts": 3} if "retry" in self.performance_features else {},
            "backends": self._get_backend_configs(),
            "middleware": self._get_middleware_configs(),
            "security_policies": self.security_features,
            "blueprints_used": [self.blueprint_id],
            "deployment_target": "docker-compose"
        }
    
    def _get_backend_configs(self) -> List[Dict[str, Any]]:
        """Get backend configurations from blueprint"""
        backends = []
        
        if self.cache_enabled:
            backends.append({
                "type": "cache",
                "implementation": "redis",
                "connection_pool_size": 10
            })
        
        if self.category == BlueprintCategory.MESSAGE_QUEUE:
            backends.append({
                "type": "message_queue",
                "implementation": "rabbitmq",
                "partitions": 4
            })
            
        return backends
    
    def _get_middleware_configs(self) -> List[str]:
        """Get middleware configurations from blueprint"""
        middleware = ["logging", "cors"]
        
        if self.tracing_enabled:
            middleware.append("tracing")
            
        if self.rate_limiting:
            middleware.append("rate_limiting")
            
        if "circuit_breaker" in self.performance_features:
            middleware.append("circuit_breaker")
            
        return middleware
    
    def calculate_fitness_score(self) -> float:
        """Calculate the fitness score of this blueprint"""
        score = 0.0
        
        # Security score (30%)
        security_score = len(self.security_features) * 0.1
        if "jwt" in self.auth_methods:
            security_score += 0.2
        if "oauth2" in self.auth_methods:
            security_score += 0.3
        score += min(security_score, 1.0) * 0.3
        
        # Performance score (25%)
        performance_score = len(self.performance_features) * 0.05
        if self.cache_enabled:
            performance_score += 0.2
        if self.tracing_enabled:
            performance_score += 0.1
        score += min(performance_score, 1.0) * 0.25
        
        # Observability score (20%)
        observability_score = len(self.monitoring_endpoints) * 0.1
        if self.test_coverage > 0.8:
            observability_score += 0.2
        score += min(observability_score, 1.0) * 0.2
        
        # Reliability score (15%)
        score += self.reliability_score * 0.15
        
        # User satisfaction score (10%)
        if self.user_ratings:
            avg_rating = sum(self.user_ratings) / len(self.user_ratings)
            score += (avg_rating / 5.0) * 0.1
            
        return round(score, 3)
    
    def update_rating(self, rating: int):
        """Update blueprint rating"""
        if 1 <= rating <= 5:
            self.user_ratings.append(rating)
            self.average_rating = sum(self.user_ratings) / len(self.user_ratings)
            self.download_count += 1


@dataclass
class BlueprintSearchCriteria:
    """Criteria for searching blueprints"""
    category: Optional[BlueprintCategory] = None
    complexity: Optional[BlueprintComplexity] = None
    tags: List[str] = field(default_factory=list)
    min_rating: float = 0.0
    max_cost: float = float('inf')
    services_required: List[str] = field(default_factory=list)
    search_text: str = ""
    sort_by: str = "rating"  # rating, downloads, fitness, updated
    sort_order: str = "desc"  # asc, desc


class BlueprintMarketplace:
    """
    Service blueprint marketplace for discovering and using reusable service blueprints.
    """
    
    def __init__(self):
        self.blueprints: Dict[str, ServiceBlueprint] = {}
        self.categories = list(BlueprintCategory)
        self.complexity_levels = list(BlueprintComplexity)
        self._initialize_default_blueprints()
        
    def _initialize_default_blueprints(self):
        """Initialize the marketplace with default blueprints"""
        # Authentication Service Blueprint
        auth_blueprint = ServiceBlueprint(
            blueprint_id="auth-service-v1",
            name="Authentication Service",
            description="Production-ready authentication service with JWT and OAuth2 support",
            category=BlueprintCategory.AUTHENTICATION,
            complexity=BlueprintComplexity.MODERATE,
            version="1.0.0",
            author="Autonomous Evolution Team",
            organization="Engineering",
            tags=["auth", "security", "jwt", "oauth2"],
            services=["auth"],
            auth_methods=["jwt", "oauth2"],
            database_type="postgres",
            cache_enabled=True,
            rate_limiting=True,
            endpoints=[
                {"path": "/auth/login", "method": "POST", "description": "User login"},
                {"path": "/auth/logout", "method": "POST", "description": "User logout"},
                {"path": "/auth/refresh", "method": "POST", "description": "Token refresh"},
                {"path": "/auth/register", "method": "POST", "description": "User registration"},
                {"path": "/auth/profile", "method": "GET", "description": "Get user profile"},
                {"path": "/auth/profile", "method": "PUT", "description": "Update user profile"}
            ],
            security_features=[
                {"type": "jwt_validation", "algorithm": "RS256"},
                {"type": "rate_limiting", "requests_per_minute": 100},
                {"type": "password_hashing", "algorithm": "bcrypt"}
            ],
            auth_requirements=["api_key", "jwt_token"],
            compliance_requirements=["gdpr", "soc2"],
            performance_features=["caching", "circuit_breaker", "retry"],
            monitoring_endpoints=["/auth/health", "/auth/metrics"],
            test_coverage=0.85,
            estimated_monthly_cost=150.0,
            estimated_requests_per_second=1000.0,
            estimated_latency_ms=50.0,
            reliability_score=0.98,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-15T00:00:00Z",
            is_verified=True,
            is_featured=True
        )
        
        # User Management Service Blueprint
        user_blueprint = ServiceBlueprint(
            blueprint_id="user-service-v1",
            name="User Management Service",
            description="Complete user management service with profile, roles, and permissions",
            category=BlueprintCategory.USER_MANAGEMENT,
            complexity=BlueprintComplexity.MODERATE,
            version="1.0.0",
            author="Autonomous Evolution Team",
            organization="Engineering",
            tags=["users", "management", "roles", "permissions"],
            services=["users"],
            auth_methods=["jwt"],
            database_type="postgres",
            cache_enabled=True,
            rate_limiting=True,
            endpoints=[
                {"path": "/users", "method": "GET", "description": "List all users"},
                {"path": "/users", "method": "POST", "description": "Create new user"},
                {"path": "/users/{id}", "method": "GET", "description": "Get user by ID"},
                {"path": "/users/{id}", "method": "PUT", "description": "Update user"},
                {"path": "/users/{id}", "method": "DELETE", "description": "Delete user"},
                {"path": "/users/{id}/roles", "method": "GET", "description": "Get user roles"},
                {"path": "/users/{id}/roles", "method": "POST", "description": "Assign role to user"}
            ],
            security_features=[
                {"type": "jwt_validation", "algorithm": "RS256"},
                {"type": "role_based_access", "roles": ["admin", "user"]},
                {"type": "rate_limiting", "requests_per_minute": 200}
            ],
            performance_features=["caching", "pagination", "batch_operations"],
            monitoring_endpoints=["/users/health", "/users/metrics"],
            test_coverage=0.90,
            estimated_monthly_cost=200.0,
            estimated_requests_per_second=2000.0,
            estimated_latency_ms=45.0,
            reliability_score=0.99,
            created_at="2024-01-02T00:00:00Z",
            updated_at="2024-01-16T00:00:00Z",
            is_verified=True,
            is_featured=True
        )
        
        # Payment Processing Service Blueprint
        payment_blueprint = ServiceBlueprint(
            blueprint_id="payment-service-v1",
            name="Payment Processing Service",
            description="Secure payment processing with multiple payment methods and compliance",
            category=BlueprintCategory.PAYMENT_PROCESSING,
            complexity=BlueprintComplexity.ENTERPRISE,
            version="1.0.0",
            author="Autonomous Evolution Team",
            organization="Engineering",
            tags=["payments", "stripe", "paypal", "pci"],
            services=["payments"],
            auth_methods=["jwt", "api_key"],
            database_type="postgres",
            cache_enabled=True,
            rate_limiting=True,
            endpoints=[
                {"path": "/payments", "method": "POST", "description": "Create payment"},
                {"path": "/payments/{id}", "method": "GET", "description": "Get payment status"},
                {"path": "/payments/{id}", "method": "PUT", "description": "Update payment"},
                {"path": "/payments/{id}/refund", "method": "POST", "description": "Process refund"},
                {"path": "/payments/webhook", "method": "POST", "description": "Payment webhook"},
                {"path": "/payments/methods", "method": "GET", "description": "Available payment methods"}
            ],
            security_features=[
                {"type": "pci_dss_compliance", "level": "saas"},
                {"type": "jwt_validation", "algorithm": "RS256"},
                {"type": "api_key_validation", "header": "X-API-Key"},
                {"type": "rate_limiting", "requests_per_minute": 50}
            ],
            compliance_requirements=["pci_dss", "gdpr", "sox"],
            performance_features=["caching", "circuit_breaker", "async_processing"],
            monitoring_endpoints=["/payments/health", "/payments/metrics"],
            test_coverage=0.95,
            estimated_monthly_cost=500.0,
            estimated_requests_per_second=500.0,
            estimated_latency_ms=100.0,
            reliability_score=0.999,
            created_at="2024-01-03T00:00:00Z",
            updated_at="2024-01-17T00:00:00Z",
            is_verified=True,
            is_featured=True
        )
        
        # Notification Service Blueprint
        notification_blueprint = ServiceBlueprint(
            blueprint_id="notification-service-v1",
            name="Notification Service",
            description="Multi-channel notification service with email, SMS, and push notifications",
            category=BlueprintCategory.NOTIFICATIONS,
            complexity=BlueprintComplexity.MODERATE,
            version="1.0.0",
            author="Autonomous Evolution Team",
            organization="Engineering",
            tags=["notifications", "email", "sms", "push"],
            services=["notifications"],
            auth_methods=["jwt"],
            database_type="postgres",
            cache_enabled=True,
            rate_limiting=True,
            endpoints=[
                {"path": "/notifications", "method": "POST", "description": "Send notification"},
                {"path": "/notifications/{id}", "method": "GET", "description": "Get notification status"},
                {"path": "/notifications/batch", "method": "POST", "description": "Send batch notifications"},
                {"path": "/notifications/templates", "method": "GET", "description": "Get notification templates"},
                {"path": "/notifications/channels", "method": "GET", "description": "Available notification channels"}
            ],
            security_features=[
                {"type": "jwt_validation", "algorithm": "RS256"},
                {"type": "rate_limiting", "requests_per_minute": 300}
            ],
            performance_features=["caching", "batch_processing", "queue_management"],
            monitoring_endpoints=["/notifications/health", "/notifications/metrics"],
            test_coverage=0.80,
            estimated_monthly_cost=100.0,
            estimated_requests_per_second=1500.0,
            estimated_latency_ms=30.0,
            reliability_score=0.95,
            created_at="2024-01-04T00:00:00Z",
            updated_at="2024-01-18T00:00:00Z",
            is_verified=True
        )
        
        # Analytics Service Blueprint
        analytics_blueprint = ServiceBlueprint(
            blueprint_id="analytics-service-v1",
            name="Analytics Service",
            description="Real-time analytics and reporting service with data visualization",
            category=BlueprintCategory.ANALYTICS,
            complexity=BlueprintComplexity.ENTERPRISE,
            version="1.0.0",
            author="Autonomous Evolution Team",
            organization="Engineering",
            tags=["analytics", "reporting", "visualization", "real-time"],
            services=["analytics"],
            auth_methods=["jwt"],
            database_type="postgres",
            cache_enabled=True,
            rate_limiting=True,
            endpoints=[
                {"path": "/analytics/events", "method": "POST", "description": "Track event"},
                {"path": "/analytics/reports", "method": "GET", "description": "Generate report"},
                {"path": "/analytics/dashboards", "method": "GET", "description": "Get dashboards"},
                {"path": "/analytics/queries", "method": "POST", "description": "Custom query"},
                {"path": "/analytics/export", "method": "POST", "description": "Export data"}
            ],
            security_features=[
                {"type": "jwt_validation", "algorithm": "RS256"},
                {"type": "data_access_control", "roles": ["admin", "analyst"]},
                {"type": "rate_limiting", "requests_per_minute": 100}
            ],
            performance_features=["caching", "query_optimization", "async_processing"],
            monitoring_endpoints=["/analytics/health", "/analytics/metrics"],
            test_coverage=0.85,
            estimated_monthly_cost=300.0,
            estimated_requests_per_second=800.0,
            estimated_latency_ms=200.0,
            reliability_score=0.97,
            created_at="2024-01-05T00:00:00Z",
            updated_at="2024-01-19T00:00:00Z",
            is_verified=True
        )
        
        # Add all blueprints to marketplace
        for blueprint in [auth_blueprint, user_blueprint, payment_blueprint, 
                         notification_blueprint, analytics_blueprint]:
            self.blueprints[blueprint.blueprint_id] = blueprint
    
    def get_blueprint(self, blueprint_id: str) -> Optional[ServiceBlueprint]:
        """Get a blueprint by ID"""
        return self.blueprints.get(blueprint_id)
    
    def search_blueprints(self, criteria: BlueprintSearchCriteria) -> List[ServiceBlueprint]:
        """Search blueprints based on criteria"""
        results = []
        
        for blueprint in self.blueprints.values():
            if self._matches_criteria(blueprint, criteria):
                results.append(blueprint)
        
        # Sort results
        results = self._sort_blueprints(results, criteria)
        
        return results
    
    def _matches_criteria(self, blueprint: ServiceBlueprint, criteria: BlueprintSearchCriteria) -> bool:
        """Check if a blueprint matches search criteria"""
        # Category filter
        if criteria.category and blueprint.category != criteria.category:
            return False
        
        # Complexity filter
        if criteria.complexity and blueprint.complexity != criteria.complexity:
            return False
        
        # Tags filter
        if criteria.tags and not any(tag in blueprint.tags for tag in criteria.tags):
            return False
        
        # Rating filter
        if blueprint.average_rating < criteria.min_rating:
            return False
        
        # Cost filter
        if blueprint.estimated_monthly_cost > criteria.max_cost:
            return False
        
        # Services required filter
        if criteria.services_required and not all(
            service in blueprint.services for service in criteria.services_required
        ):
            return False
        
        # Search text filter
        if criteria.search_text:
            search_text = criteria.search_text.lower()
            searchable_text = (
                f"{blueprint.name} {blueprint.description} {' '.join(blueprint.tags)} "
                f"{' '.join(blueprint.services)}".lower()
            )
            if search_text not in searchable_text:
                return False
        
        return True
    
    def _sort_blueprints(self, blueprints: List[ServiceBlueprint], 
                        criteria: BlueprintSearchCriteria) -> List[ServiceBlueprint]:
        """Sort blueprints based on criteria"""
        reverse_order = criteria.sort_order == "desc"
        
        if criteria.sort_by == "rating":
            return sorted(blueprints, key=lambda b: b.average_rating, reverse=reverse_order)
        elif criteria.sort_by == "downloads":
            return sorted(blueprints, key=lambda b: b.download_count, reverse=reverse_order)
        elif criteria.sort_by == "fitness":
            return sorted(blueprints, key=lambda b: b.calculate_fitness_score(), 
                         reverse=reverse_order)
        elif criteria.sort_by == "updated":
            return sorted(blueprints, key=lambda b: b.updated_at, reverse=reverse_order)
        else:
            return blueprints
    
    def get_featured_blueprints(self) -> List[ServiceBlueprint]:
        """Get featured blueprints"""
        return [b for b in self.blueprints.values() if b.is_featured]
    
    def get_verified_blueprints(self) -> List[ServiceBlueprint]:
        """Get verified blueprints"""
        return [b for b in self.blueprints.values() if b.is_verified]
    
    def get_blueprints_by_category(self, category: BlueprintCategory) -> List[ServiceBlueprint]:
        """Get blueprints by category"""
        return [b for b in self.blueprints.values() if b.category == category]
    
    def get_blueprint_recommendations(self, user_services: List[str], 
                                    user_preferences: Dict[str, Any] = None) -> List[ServiceBlueprint]:
        """Get blueprint recommendations based on user services and preferences"""
        recommendations = []
        
        # Find complementary blueprints
        for blueprint in self.blueprints.values():
            # Check if blueprint services complement user services
            if not any(service in user_services for service in blueprint.services):
                recommendations.append(blueprint)
        
        # Score and sort recommendations
        scored_recommendations = []
        for blueprint in recommendations:
            score = 0.0
            
            # Fitness score
            score += blueprint.calculate_fitness_score() * 0.4
            
            # User rating
            if blueprint.average_rating:
                score += (blueprint.average_rating / 5.0) * 0.3
            
            # Usage count
            score += min(blueprint.download_count / 1000.0, 1.0) * 0.2
            
            # Reliability
            score += blueprint.reliability_score * 0.1
            
            scored_recommendations.append((blueprint, score))
        
        # Sort by score
        scored_recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return [blueprint for blueprint, score in scored_recommendations[:10]]
    
    def create_blueprint_from_genome(self, genome: Genome, 
                                   name: str, description: str, 
                                   author: str = "User", 
                                   organization: str = "Organization") -> ServiceBlueprint:
        """Create a blueprint from a genome"""
        blueprint_id = f"custom-{name.lower().replace(' ', '-')}-v1"
        
        # Extract services and features from genome
        endpoints = self._generate_endpoints_from_services(genome.services)
        security_features = genome.security_policies
        performance_features = []
        
        if genome.cache_enabled:
            performance_features.append("caching")
        if genome.circuit_breaker:
            performance_features.append("circuit_breaker")
        if genome.tracing_enabled:
            performance_features.append("tracing")
        
        # Estimate metrics
        estimated_cost = len(genome.services) * 100.0
        estimated_rps = len(genome.services) * 500.0
        estimated_latency = 100.0 - (len(genome.services) * 10.0)
        
        blueprint = ServiceBlueprint(
            blueprint_id=blueprint_id,
            name=name,
            description=description,
            category=self._infer_category(genome.services),
            complexity=self._infer_complexity(genome),
            version="1.0.0",
            author=author,
            organization=organization,
            tags=genome.services,
            services=genome.services,
            auth_methods=[genome.auth],
            database_type=genome.database,
            cache_enabled=genome.cache_enabled,
            rate_limiting=genome.rate_limiting,
            endpoints=endpoints,
            security_features=security_features,
            performance_features=performance_features,
            test_coverage=0.7,  # Default
            estimated_monthly_cost=estimated_cost,
            estimated_requests_per_second=estimated_rps,
            estimated_latency_ms=max(estimated_latency, 10.0),
            reliability_score=0.9,  # Default
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        # Add to marketplace
        self.blueprints[blueprint_id] = blueprint
        
        return blueprint
    
    def _generate_endpoints_from_services(self, services: List[str]) -> List[Dict[str, Any]]:
        """Generate endpoint list from services"""
        endpoints = []
        
        for service in services:
            # Standard REST endpoints
            endpoints.extend([
                {"path": f"/{service}", "method": "GET", "description": f"Get all {service}"},
                {"path": f"/{service}", "method": "POST", "description": f"Create new {service}"},
                {"path": f"/{service}/{{id}}", "method": "GET", "description": f"Get {service} by ID"},
                {"path": f"/{service}/{{id}}", "method": "PUT", "description": f"Update {service}"},
                {"path": f"/{service}/{{id}}", "method": "DELETE", "description": f"Delete {service}"}
            ])
            
            # Service-specific endpoints
            if service == "auth":
                endpoints.extend([
                    {"path": "/auth/login", "method": "POST", "description": "User login"},
                    {"path": "/auth/logout", "method": "POST", "description": "User logout"},
                    {"path": "/auth/refresh", "method": "POST", "description": "Token refresh"}
                ])
            elif service == "users":
                endpoints.extend([
                    {"path": "/users/profile", "method": "GET", "description": "Get user profile"},
                    {"path": "/users/profile", "method": "PUT", "description": "Update user profile"}
                ])
        
        return endpoints
    
    def _infer_category(self, services: List[str]) -> BlueprintCategory:
        """Infer blueprint category from services"""
        service_category_mapping = {
            "auth": BlueprintCategory.AUTHENTICATION,
            "users": BlueprintCategory.USER_MANAGEMENT,
            "payments": BlueprintCategory.PAYMENT_PROCESSING,
            "notifications": BlueprintCategory.NOTIFICATIONS,
            "analytics": BlueprintCategory.ANALYTICS,
            "search": BlueprintCategory.SEARCH_ENGINEERING,
            "files": BlueprintCategory.FILE_MANAGEMENT,
            "admin": BlueprintCategory.ADMIN_DASHBOARD
        }
        
        for service in services:
            if service in service_category_mapping:
                return service_category_mapping[service]
        
        return BlueprintCategory.USER_MANAGEMENT  # Default
    
    def _infer_complexity(self, genome: Genome) -> BlueprintComplexity:
        """Infer blueprint complexity from genome"""
        complexity_score = 0
        
        # Service count
        if len(genome.services) <= 2:
            complexity_score += 1
        elif len(genome.services) <= 4:
            complexity_score += 2
        else:
            complexity_score += 3
        
        # Feature count
        feature_count = sum([
            genome.cache_enabled,
            genome.rate_limiting,
            genome.tracing_enabled,
            genome.circuit_breaker,
            len(genome.security_policies)
        ])
        
        if feature_count <= 2:
            complexity_score += 1
        elif feature_count <= 4:
            complexity_score += 2
        else:
            complexity_score += 3
        
        # Determine complexity
        if complexity_score <= 3:
            return BlueprintComplexity.SIMPLE
        elif complexity_score <= 6:
            return BlueprintComplexity.MODERATE
        elif complexity_score <= 9:
            return BlueprintComplexity.COMPLEX
        else:
            return BlueprintComplexity.ENTERPRISE
    
    def rate_blueprint(self, blueprint_id: str, rating: int):
        """Rate a blueprint"""
        blueprint = self.get_blueprint(blueprint_id)
        if blueprint:
            blueprint.update_rating(rating)
    
    def get_blueprint_statistics(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        total_blueprints = len(self.blueprints)
        verified_blueprints = len([b for b in self.blueprints.values() if b.is_verified])
        featured_blueprints = len([b for b in self.blueprints.values() if b.is_featured])
        
        category_counts = {}
        for category in BlueprintCategory:
            category_counts[category.value] = len(self.get_blueprints_by_category(category))
        
        complexity_counts = {}
        for complexity in BlueprintComplexity:
            complexity_counts[complexity.value] = len(
                [b for b in self.blueprints.values() if b.complexity == complexity]
            )
        
        total_downloads = sum(b.download_count for b in self.blueprints.values())
        total_ratings = sum(len(b.user_ratings) for b in self.blueprints.values())
        average_rating = sum(b.average_rating * len(b.user_ratings) for b in self.blueprints.values()) / max(total_ratings, 1)
        
        return {
            "total_blueprints": total_blueprints,
            "verified_blueprints": verified_blueprints,
            "featured_blueprints": featured_blueprints,
            "total_downloads": total_downloads,
            "total_ratings": total_ratings,
            "average_rating": round(average_rating, 2),
            "category_distribution": category_counts,
            "complexity_distribution": complexity_counts,
            "most_popular": self._get_most_popular_blueprints(),
            "highest_rated": self._get_highest_rated_blueprints()
        }
    
    def _get_most_popular_blueprints(self) -> List[str]:
        """Get most popular blueprints by downloads"""
        sorted_blueprints = sorted(
            self.blueprints.values(),
            key=lambda b: b.download_count,
            reverse=True
        )
        return [b.blueprint_id for b in sorted_blueprints[:5]]
    
    def _get_highest_rated_blueprints(self) -> List[str]:
        """Get highest rated blueprints"""
        rated_blueprints = [b for b in self.blueprints.values() if b.user_ratings]
        sorted_blueprints = sorted(
            rated_blueprints,
            key=lambda b: b.average_rating,
            reverse=True
        )
        return [b.blueprint_id for b in sorted_blueprints[:5]]
    
    def export_blueprint(self, blueprint_id: str, file_path: str):
        """Export a blueprint to a file"""
        blueprint = self.get_blueprint(blueprint_id)
        if blueprint:
            with open(file_path, 'w') as f:
                json.dump(blueprint.__dict__, f, indent=2)
    
    def import_blueprint(self, file_path: str):
        """Import a blueprint from a file"""
        with open(file_path, 'r') as f:
            blueprint_data = json.load(f)
        
        blueprint = ServiceBlueprint(**blueprint_data)
        self.blueprints[blueprint.blueprint_id] = blueprint
    
    def generate_genome_from_blueprint(self, blueprint_id: str, 
                                     additional_services: List[str] = None) -> Genome:
        """Generate a genome from a blueprint"""
        blueprint = self.get_blueprint(blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint {blueprint_id} not found")
        
        # Get blueprint configuration
        config = blueprint.to_genome_config()
        
        # Add additional services if specified
        if additional_services:
            config["services"] = blueprint.services + additional_services
        
        # Create genome from configuration
        genome = Genome(config)
        
        # Record blueprint usage
        blueprint.usage_count += 1
        
        return genome