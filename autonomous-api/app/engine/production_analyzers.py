"""
Production Fitness Scoring Analyzers
====================================

This module implements comprehensive analyzers for evaluating API architectures 
against production readiness criteria.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from app.engine.genome import Genome, ProductionMetrics


@dataclass
class OpenAPIAnalysis:
    """Results from OpenAPI completeness analysis"""
    completeness_score: float
    missing_components: List[str]
    issues: List[str]
    recommendations: List[str]
    schema_coverage: Dict[str, float]


@dataclass
class AuthAnalysis:
    """Results from auth coverage analysis"""
    coverage_score: float
    auth_methods: Dict[str, bool]
    missing_auth: List[str]
    security_issues: List[str]
    recommendations: List[str]


@dataclass
class MigrationAnalysis:
    """Results from migration safety analysis"""
    safety_score: float
    risk_factors: List[str]
    compatibility_issues: List[str]
    migration_difficulty: str
    recommendations: List[str]


class OpenAPICompletenessAnalyzer:
    """Analyzes OpenAPI specification completeness"""
    
    def __init__(self):
        self.required_components = [
            "openapi", "info", "paths", "servers", "components"
        ]
        self.required_security_schemes = [
            "api_key", "oauth2", "http", "openIdConnect"
        ]
        self.required_path_items = ["get", "post", "put", "delete", "patch"]
        
    def analyze(self, genome: Genome) -> OpenAPIAnalysis:
        """
        Analyze OpenAPI completeness for a genome
        
        Args:
            genome: The genome to analyze
            
        Returns:
            OpenAPIAnalysis with detailed results
        """
        issues = []
        missing_components = []
        recommendations = []
        schema_coverage = {}
        
        # Check OpenAPI version
        if not genome.openapi_version:
            missing_components.append("OpenAPI version specification")
            recommendations.append("Define OpenAPI version (3.0.0 or 3.1.0)")
        
        # Analyze services for OpenAPI completeness
        all_paths = 0
        documented_paths = 0
        
        for service in genome.services:
            service_coverage = self._analyze_service_openapi(service, genome)
            schema_coverage[service] = service_coverage

            # Track path coverage
            expected_paths = self._get_expected_paths(service)
            all_paths += len(expected_paths)
            documented_paths += int(
                service_coverage.get("endpoints", 0.0) * len(expected_paths)
            )
            
            # Check for service-specific issues
            if service_coverage.get("endpoints", 0) == 0:
                issues.append(f"No endpoints documented for {service}")
        
        # Calculate completeness score
        if all_paths > 0:
            path_completeness = documented_paths / all_paths
        else:
            path_completeness = 0.0
            
        schema_completeness = (
            sum(c.get("schemas", 0.0) for c in schema_coverage.values())
            / len(genome.services) if genome.services else 0.0
        )
        
        # Weight different aspects
        completeness_score = (
            path_completeness * 0.4 +
            schema_completeness * 0.3 +
            self._check_security_schemes(genome) * 0.3
        )
        
        # Generate recommendations
        if completeness_score < 0.7:
            recommendations.append("Generate comprehensive OpenAPI documentation for all endpoints")
        if not genome.health_endpoints:
            recommendations.append("Add health check endpoints (/health, /ready)")
        if not genome.metrics_endpoints:
            recommendations.append("Add metrics endpoints for observability")
        
        return OpenAPIAnalysis(
            completeness_score=completeness_score,
            missing_components=missing_components,
            issues=issues,
            recommendations=recommendations,
            schema_coverage=schema_coverage
        )
    
    def _analyze_service_openapi(self, service: str, genome: Genome) -> Dict[str, float]:
        """Analyze OpenAPI coverage for a specific service"""
        coverage = {
            "endpoints": 0.0,
            "schemas": 0.0,
            "security": 0.0,
            "parameters": 0.0,
            "responses": 0.0
        }
        
        # Simulate endpoint analysis based on service type
        expected_endpoints = self._get_expected_paths(service)
        
        # Check if service has basic OpenAPI structure
        if genome.openapi_version:
            coverage["schemas"] = 0.6  # Basic schema coverage
            coverage["parameters"] = 0.7  # Parameter coverage
            
            # Security coverage based on auth type
            if genome.auth in ["jwt", "oauth2", "api_key"]:
                coverage["security"] = 0.8
            else:
                coverage["security"] = 0.3
                
            # Response coverage
            coverage["responses"] = 0.5
            
            # Endpoint coverage (simulated)
            if service in ["auth", "users", "admin"]:
                coverage["endpoints"] = min(len(expected_endpoints) / 8.0, 1.0)
            else:
                coverage["endpoints"] = min(len(expected_endpoints) / 6.0, 1.0)
        
        return coverage
    
    def _get_expected_paths(self, service: str) -> List[str]:
        """Get expected paths for a service type"""
        expected_paths = {
            "auth": ["/login", "/register", "/logout", "/refresh"],
            "users": ["/users", "/users/{id}", "/users/profile"],
            "payments": ["/payments", "/payments/{id}", "/refunds"],
            "analytics": ["/analytics", "/reports", "/dashboard"],
            "notifications": ["/notifications", "/subscribe", "/unsubscribe"],
            "search": ["/search", "/suggest", "/index"],
            "files": ["/files", "/files/{id}", "/upload"],
            "admin": ["/admin", "/admin/users", "/admin/settings"],
            "products": ["/products", "/products/{id}", "/categories"],
            "orders": ["/orders", "/orders/{id}", "/orders/status"],
            "inventory": ["/inventory", "/inventory/{id}", "/stock"],
            "reports": ["/reports", "/reports/{type}", "/export"]
        }
        return expected_paths.get(service, ["/api", "/data"])
    
    def _check_security_schemes(self, genome: Genome) -> float:
        """Check OpenAPI security scheme completeness"""
        if not genome.openapi_version:
            return 0.0
            
        score = 0.0
        if genome.auth == "jwt":
            score += 0.4
        if genome.auth == "oauth2":
            score += 0.5
        if genome.auth == "api_key":
            score += 0.3
        if genome.auth == "basic":
            score += 0.1
            
        # Add security policies
        if genome.rate_limiting:
            score += 0.1
            
        return min(score, 1.0)


class AuthCoverageAnalyzer:
    """Analyzes authentication and authorization coverage"""
    
    def __init__(self):
        self.required_endpoints = [
            "/auth/login", "/auth/logout", "/auth/refresh",
            "/users", "/users/profile", "/admin"
        ]
        self.secure_methods = ["POST", "PUT", "DELETE", "PATCH"]
        
    def analyze(self, genome: Genome) -> AuthAnalysis:
        """
        Analyze authentication coverage for a genome
        
        Args:
            genome: The genome to analyze
            
        Returns:
            AuthAnalysis with detailed results
        """
        auth_methods = {}
        missing_auth = []
        security_issues = []
        recommendations = []
        
        # Analyze authentication method
        auth_score = self._score_auth_method(genome.auth)
        auth_methods[genome.auth] = True
        
        # Check for secure endpoints
        secure_endpoints = self._get_secure_endpoints(genome)
        auth_coverage = len(secure_endpoints) / len(self.required_endpoints)
        
        # Check security policies
        if genome.auth == "basic" and len(genome.services) > 3:
            security_issues.append("Basic auth is not recommended for multi-service architectures")
            recommendations.append("Consider JWT or OAuth2 for better security")
        
        # Check for missing security features
        if not genome.rate_limiting:
            missing_auth.append("Rate limiting")
            recommendations.append("Implement rate limiting to prevent brute force attacks")
            
        if genome.cors_enabled and genome.auth in ["basic", "api_key"]:
            security_issues.append("CORS with weak auth methods may expose credentials")
            recommendations.append("Use stronger auth methods with CORS")
        
        # Generate comprehensive auth coverage score
        coverage_score = (
            auth_coverage * 0.5 +
            auth_score * 0.3 +
            self._score_security_features(genome) * 0.2
        )
        
        return AuthAnalysis(
            coverage_score=coverage_score,
            auth_methods=auth_methods,
            missing_auth=missing_auth,
            security_issues=security_issues,
            recommendations=recommendations
        )
    
    def _score_auth_method(self, auth_method: str) -> float:
        """Score authentication method strength"""
        auth_scores = {
            "oauth2": 1.0,
            "jwt": 0.9,
            "api_key": 0.6,
            "basic": 0.3
        }
        return auth_scores.get(auth_method, 0.0)
    
    def _get_secure_endpoints(self, genome: Genome) -> List[str]:
        """Get endpoints that should be secured"""
        secure_endpoints = []
        
        for service in genome.services:
            if service in ["auth", "users", "admin"]:
                secure_endpoints.extend(self._get_auth_required_paths(service))
            elif service in ["payments", "analytics"]:
                secure_endpoints.extend(["/" + service])
                
        return secure_endpoints
    
    def _get_auth_required_paths(self, service: str) -> List[str]:
        """Get paths requiring authentication"""
        auth_paths = {
            "auth": ["/auth/login", "/auth/refresh"],
            "users": ["/users", "/users/{id}", "/users/profile"],
            "admin": ["/admin", "/admin/users", "/admin/settings"]
        }
        return auth_paths.get(service, [])
    
    def _score_security_features(self, genome: Genome) -> float:
        """Score implemented security features"""
        score = 0.0
        if genome.rate_limiting:
            score += 0.3
        if genome.cors_enabled:
            score += 0.2
        if genome.tracing_enabled:
            score += 0.1
        if genome.circuit_breaker:
            score += 0.2
        if genome.security_policies:
            score += 0.2
            
        return min(score, 1.0)


class MigrationSafetyAnalyzer:
    """Analyzes migration safety and compatibility"""
    
    def __init__(self):
        self.compatibility_checks = {
            "postgres": ["backward_compatible", "migration_tools"],
            "mysql": ["backward_compatible", "migration_tools"],
            "sqlite": ["limited_compatibility", "no_migration_tools"]
        }
        
    def analyze(self, genome: Genome) -> MigrationAnalysis:
        """
        Analyze migration safety for a genome
        
        Args:
            genome: The genome to analyze
            
        Returns:
            MigrationAnalysis with detailed results
        """
        risk_factors = []
        compatibility_issues = []
        recommendations = []
        
        # Analyze database compatibility
        db_compatibility = self._check_database_compatibility(genome.database)
        if db_compatibility < 0.7:
            risk_factors.append(f"Database {genome.database} has limited compatibility")
            compatibility_issues.append("Limited backward compatibility with existing systems")
        
        # Check service dependencies
        dependency_risk = self._check_dependency_risk(genome)
        if dependency_risk > 0.7:
            risk_factors.append("High dependency risk")
            recommendations.append("Reduce external dependencies or implement fallbacks")
        
        # Check configuration compatibility
        config_compatibility = self._check_config_compatibility(genome)
        if config_compatibility < 0.5:
            risk_factors.append("Configuration incompatibility")
            recommendations.append("Standardize configuration across services")
        
        # Calculate overall safety score
        safety_score = (
            db_compatibility * 0.4 +
            (1.0 - dependency_risk) * 0.3 +
            config_compatibility * 0.3
        )
        
        # Determine migration difficulty
        if safety_score > 0.8:
            migration_difficulty = "low"
        elif safety_score > 0.6:
            migration_difficulty = "medium"
        else:
            migration_difficulty = "high"
        
        # Generate recommendations
        if migration_difficulty == "high":
            recommendations.append("Consider incremental migration strategy")
            recommendations.append("Implement comprehensive rollback procedures")
        elif migration_difficulty == "medium":
            recommendations.append("Plan migration during low-traffic periods")
            recommendations.append("Implement monitoring during migration")
        
        return MigrationAnalysis(
            safety_score=safety_score,
            risk_factors=risk_factors,
            compatibility_issues=compatibility_issues,
            migration_difficulty=migration_difficulty,
            recommendations=recommendations
        )
    
    def _check_database_compatibility(self, database: str) -> float:
        """Check database migration compatibility"""
        compatibility_scores = {
            "postgres": 0.9,
            "mysql": 0.8,
            "sqlite": 0.4
        }
        return compatibility_scores.get(database, 0.5)
    
    def _check_dependency_risk(self, genome: Genome) -> float:
        """Check dependency migration risk"""
        risk = 0.0
        
        # Check for external dependencies
        for backend in genome.backends:
            if backend["type"] == "message_queue":
                risk += 0.3
            elif backend["type"] == "cache":
                risk += 0.2
                
        # Check for complex services
        if len(genome.services) > 5:
            risk += 0.2
            
        # Check for auth complexity
        if genome.auth == "oauth2":
            risk += 0.3
            
        return min(risk, 1.0)
    
    def _check_config_compatibility(self, genome: Genome) -> float:
        """Check configuration compatibility"""
        score = 0.0
        
        # Check timeout configurations
        if all(key in genome.timeout_config for key in ["connect_timeout", "read_timeout", "write_timeout"]):
            score += 0.3
            
        # Check retry policies
        if all(key in genome.retry_policy for key in ["max_attempts", "base_delay"]):
            score += 0.3
            
        # Check middleware compatibility
        compatible_middleware = ["logging", "caching", "tracing", "rate_limiting"]
        for middleware in genome.middleware:
            if middleware in compatible_middleware:
                score += 0.1
                
        return min(score, 1.0)


class ObservabilityAnalyzer:
    """Analyzes observability coverage"""
    
    def __init__(self):
        self.required_metrics = [
            "request_count", "response_time", "error_rate", "cpu_usage", "memory_usage"
        ]
        self.required_traces = ["requests", "database_calls", "external_calls"]
        
    def analyze(self, genome: Genome) -> Dict[str, Any]:
        """Analyze observability coverage"""
        coverage_score = 0.0
        missing_components = []
        recommendations = []
        
        # Check metrics endpoints
        metrics_coverage = 0.0
        if genome.metrics_endpoints:
            metrics_coverage += 0.4
        if genome.tracing_enabled:
            metrics_coverage += 0.3
        if genome.health_endpoints:
            metrics_coverage += 0.3
            
        coverage_score = metrics_coverage
        
        # Generate recommendations
        if coverage_score < 0.7:
            if not genome.metrics_endpoints:
                missing_components.append("Metrics endpoints")
                recommendations.append("Add Prometheus metrics endpoint")
            if not genome.tracing_enabled:
                missing_components.append("Distributed tracing")
                recommendations.append("Enable OpenTelemetry tracing")
            if not genome.health_endpoints:
                missing_components.append("Health checks")
                recommendations.append("Add health check endpoints")
        
        return {
            "coverage_score": coverage_score,
            "missing_components": missing_components,
            "recommendations": recommendations,
            "enabled_features": {
                "metrics": genome.metrics_endpoints,
                "tracing": genome.tracing_enabled,
                "health_checks": genome.health_endpoints
            }
        }


class LatencyAnalyzer:
    """Analyzes latency and performance characteristics"""
    
    def analyze(self, genome: Genome) -> Dict[str, Any]:
        """Analyze latency characteristics"""
        latency_estimate = 0.0
        error_budget_estimate = 0.0
        
        # Calculate base latency based on architecture
        base_latency = self._calculate_base_latency(genome)
        
        # Adjust for optimization features
        if genome.cache_enabled:
            base_latency *= 0.7  # 30% improvement with caching
        if genome.circuit_breaker:
            base_latency *= 0.9  # 10% improvement with circuit breaker
        if len(genome.backends) > 0:
            base_latency *= 1.2  # 20% overhead for additional backends
            
        latency_estimate = min(base_latency, 5000.0)  # Cap at 5 seconds
        
        # Calculate error budget based on reliability features
        reliability_score = self._calculate_reliability(genome)
        error_budget_estimate = (1.0 - reliability_score) * 0.01  # 1% max error budget
        
        return {
            "latency_estimate_ms": round(latency_estimate, 2),
            "error_budget_estimate": round(error_budget_estimate, 6),
            "reliability_score": reliability_score,
            "optimization_features": {
                "caching": genome.cache_enabled,
                "circuit_breaker": genome.circuit_breaker,
                "backends": len(genome.backends)
            }
        }
    
    def _calculate_base_latency(self, genome: Genome) -> float:
        """Calculate base latency based on architecture"""
        base_latency = 100.0  # Base 100ms
        
        # Add latency for each service
        base_latency += len(genome.services) * 50.0
        
        # Add latency for database type
        db_latency = {
            "sqlite": 0.0,
            "mysql": 20.0,
            "postgres": 25.0
        }
        base_latency += db_latency.get(genome.database, 0.0)
        
        # Add latency for auth complexity
        auth_latency = {
            "basic": 10.0,
            "api_key": 15.0,
            "jwt": 20.0,
            "oauth2": 30.0
        }
        base_latency += auth_latency.get(genome.auth, 0.0)
        
        return base_latency
    
    def _calculate_reliability(self, genome: Genome) -> float:
        """Calculate system reliability score"""
        reliability = 0.0
        
        # Add reliability features
        if genome.circuit_breaker:
            reliability += 0.2
        if genome.retry_policy:
            reliability += 0.2
        if genome.cache_enabled:
            reliability += 0.1
        if len(genome.backends) > 0:
            reliability += 0.1
            
        # Service count reliability impact
        if len(genome.services) <= 3:
            reliability += 0.2
        elif len(genome.services) <= 5:
            reliability += 0.1
        else:
            reliability -= 0.1
            
        return min(reliability, 1.0)


class ProductionFitnessScorer:
    """Main orchestrator for production fitness scoring"""
    
    def __init__(self):
        self.openapi_analyzer = OpenAPICompletenessAnalyzer()
        self.auth_analyzer = AuthCoverageAnalyzer()
        self.migration_analyzer = MigrationSafetyAnalyzer()
        self.observability_analyzer = ObservabilityAnalyzer()
        self.latency_analyzer = LatencyAnalyzer()
        
    def score_genome(self, genome: Genome) -> Dict[str, Any]:
        """
        Score a genome against all production fitness criteria
        
        Args:
            genome: The genome to score
            
        Returns:
            Comprehensive fitness scoring results
        """
        # Run all analyzers
        openapi_result = self.openapi_analyzer.analyze(genome)
        auth_result = self.auth_analyzer.analyze(genome)
        migration_result = self.migration_analyzer.analyze(genome)
        observability_result = self.observability_analyzer.analyze(genome)
        latency_result = self.latency_analyzer.analyze(genome)
        
        # Update genome metrics
        genome.metrics.openapi_completeness = openapi_result.completeness_score
        genome.metrics.auth_coverage = auth_result.coverage_score
        genome.metrics.migration_safety = migration_result.safety_score
        genome.metrics.observability_coverage = observability_result["coverage_score"]
        genome.metrics.latency_estimate = latency_result["latency_estimate_ms"]
        genome.metrics.error_budget_estimate = latency_result["error_budget_estimate"]
        genome.metrics.dependency_risk = self._calculate_dependency_risk(genome)
        genome.metrics.cloud_cost_estimate = self._estimate_cloud_cost(genome)
        genome.metrics.test_coverage_score = self._estimate_test_coverage(genome)
        genome.metrics.security_score = auth_result.coverage_score
        
        # Calculate overall production score
        production_score = genome.get_production_score()
        
        return {
            "production_score": production_score,
            "openapi_analysis": openapi_result,
            "auth_analysis": auth_result,
            "migration_analysis": migration_result,
            "observability_analysis": observability_result,
            "latency_analysis": latency_result,
            "recommendations": self._generate_combined_recommendations(
                openapi_result, auth_result, migration_result, 
                observability_result, latency_result
            )
        }
    
    def _calculate_dependency_risk(self, genome: Genome) -> float:
        """Calculate dependency risk score"""
        risk = 0.0
        
        # External dependencies
        for backend in genome.backends:
            if backend["implementation"] in ["kafka", "rabbitmq"]:
                risk += 0.3
            elif backend["implementation"] in ["redis", "memcached"]:
                risk += 0.1
                
        # Service complexity
        if len(genome.services) > 4:
            risk += 0.2
            
        # Authentication complexity
        if genome.auth == "oauth2":
            risk += 0.2
            
        return min(risk, 1.0)
    
    def _estimate_cloud_cost(self, genome: Genome) -> float:
        """Estimate cloud deployment costs"""
        base_cost = 100.0  # Base $100/month
        
        # Service costs
        base_cost += len(genome.services) * 50.0
        
        # Database costs
        db_costs = {
            "sqlite": 0.0,
            "mysql": 30.0,
            "postgres": 40.0
        }
        base_cost += db_costs.get(genome.database, 0.0)
        
        # Backend costs
        for backend in genome.backends:
            if backend["type"] == "cache":
                base_cost += 20.0
            elif backend["type"] == "message_queue":
                base_cost += 50.0
                
        # Optimization features reduce cost
        if genome.cache_enabled:
            base_cost *= 0.9
        if genome.circuit_breaker:
            base_cost *= 0.95
            
        return base_cost
    
    def _estimate_test_coverage(self, genome: Genome) -> float:
        """Estimate test coverage based on architecture"""
        coverage = 0.0
        
        # Base coverage for services
        coverage += len(genome.services) * 0.1
        
        # Auth testing
        if genome.auth in ["jwt", "oauth2"]:
            coverage += 0.2
            
        # Integration testing
        if len(genome.services) > 1:
            coverage += 0.1
            
        # Performance testing
        if genome.circuit_breaker or genome.retry_policy:
            coverage += 0.1
            
        return min(coverage, 1.0)
    
    def _generate_combined_recommendations(self, *analyzers) -> List[str]:
        """Generate combined recommendations from all analyzers"""
        recommendations = []
        
        for analyzer in analyzers:
            if hasattr(analyzer, 'recommendations'):
                recommendations.extend(analyzer.recommendations)
                
        # Remove duplicates and prioritize
        unique_recommendations = list(set(recommendations))
        priority_recommendations = []
        
        # Prioritize security recommendations
        for rec in unique_recommendations:
            if any(word in rec.lower() for word in ["security", "auth", "rate limiting"]):
                priority_recommendations.append(rec)
                
        # Add remaining recommendations
        for rec in unique_recommendations:
            if rec not in priority_recommendations:
                priority_recommendations.append(rec)
                
        return priority_recommendations[:10]  # Top 10 recommendations