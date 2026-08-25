"""
Architecture Diff Explorer
==========================

This module implements architecture comparison and diff analysis for evolved
API candidates.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.engine.genome import Genome, ProductionMetrics
from app.engine.production_analyzers import ProductionFitnessScorer


@dataclass
class ServiceGraphDiff:
    """Results from service graph comparison"""
    added_services: List[str]
    removed_services: List[str]
    modified_services: List[str]
    service_dependencies: Dict[str, List[str]]
    complexity_change: float
    risk_impact: float


@dataclass
class EndpointDiff:
    """Results from endpoint comparison"""
    added_endpoints: List[Dict[str, Any]]
    removed_endpoints: List[Dict[str, Any]]
    modified_endpoints: List[Dict[str, Any]]
    endpoint_coverage: float
    api_compatibility_score: float


@dataclass
class SecurityPolicyDiff:
    """Results from security policy comparison"""
    added_policies: List[Dict[str, Any]]
    removed_policies: List[Dict[str, Any]]
    modified_policies: List[Dict[str, Any]]
    security_improvement: float
    compliance_gaps: List[str]


@dataclass
class DatabaseDiff:
    """Results from database/schema comparison"""
    schema_changes: List[Dict[str, Any]]
    migration_impact: str
    data_loss_risk: float
    performance_impact: float


@dataclass
class CostPerformanceDiff:
    """Results from cost/performance comparison"""
    cost_change: float
    performance_change: float
    roi_score: float
    scalability_impact: float


@dataclass
class ArchitectureComparison:
    """Complete architecture comparison results"""
    baseline_genome: Genome
    candidate_genome: Genome
    service_graph_diff: ServiceGraphDiff
    endpoint_diff: EndpointDiff
    security_diff: SecurityPolicyDiff
    database_diff: DatabaseDiff
    cost_performance_diff: CostPerformanceDiff
    overall_similarity: float
    recommendation: str
    tradeoffs: List[str]


class ArchitectureDiffExplorer:
    """Explores differences between evolved architecture candidates"""
    
    def __init__(self):
        self.fitness_scorer = ProductionFitnessScorer()
        
    def compare_architectures(self, baseline: Genome, candidate: Genome) -> ArchitectureComparison:
        """
        Compare two architectures and generate detailed diff analysis
        
        Args:
            baseline: Baseline genome for comparison
            candidate: Candidate genome to compare against baseline
            
        Returns:
            ArchitectureComparison with detailed analysis
        """
        # Compare service graphs
        service_graph_diff = self._compare_service_graphs(baseline, candidate)
        
        # Compare endpoints
        endpoint_diff = self._compare_endpoints(baseline, candidate)
        
        # Compare security policies
        security_diff = self._compare_security_policies(baseline, candidate)
        
        # Compare database/schema
        database_diff = self._compare_databases(baseline, candidate)
        
        # Compare cost/performance
        cost_performance_diff = self._compare_cost_performance(baseline, candidate)
        
        # Calculate overall similarity
        overall_similarity = self._calculate_similarity(baseline, candidate)
        
        # Generate recommendation and tradeoffs
        recommendation, tradeoffs = self._generate_recommendation(
            baseline, candidate, 
            service_graph_diff, endpoint_diff, security_diff,
            database_diff, cost_performance_diff, overall_similarity
        )
        
        return ArchitectureComparison(
            baseline_genome=baseline,
            candidate_genome=candidate,
            service_graph_diff=service_graph_diff,
            endpoint_diff=endpoint_diff,
            security_diff=security_diff,
            database_diff=database_diff,
            cost_performance_diff=cost_performance_diff,
            overall_similarity=overall_similarity,
            recommendation=recommendation,
            tradeoffs=tradeoffs
        )
    
    def _compare_service_graphs(self, baseline: Genome, candidate: Genome) -> ServiceGraphDiff:
        """Compare service architectures"""
        baseline_services = set(baseline.services)
        candidate_services = set(candidate.services)
        
        added_services = list(candidate_services - baseline_services)
        removed_services = list(baseline_services - candidate_services)
        common_services = baseline_services & candidate_services
        
        modified_services = []
        for service in common_services:
            if self._is_service_modified(baseline, candidate, service):
                modified_services.append(service)
        
        # Analyze dependencies
        service_dependencies = self._analyze_service_dependencies(candidate)
        
        # Calculate complexity change
        complexity_change = len(candidate.services) - len(baseline.services)
        
        # Calculate risk impact
        risk_impact = self._calculate_service_risk_impact(added_services, removed_services)
        
        return ServiceGraphDiff(
            added_services=added_services,
            removed_services=removed_services,
            modified_services=modified_services,
            service_dependencies=service_dependencies,
            complexity_change=complexity_change,
            risk_impact=risk_impact
        )
    
    def _is_service_modified(self, baseline: Genome, candidate: Genome, service: str) -> bool:
        """Check if a service has been modified"""
        # Compare service configurations
        baseline_auth = self._get_service_auth(baseline, service)
        candidate_auth = self._get_service_auth(candidate, service)
        
        if baseline_auth != candidate_auth:
            return True
            
        # Compare service features
        baseline_features = self._get_service_features(baseline, service)
        candidate_features = self._get_service_features(candidate, service)
        
        return baseline_features != candidate_features
    
    def _get_service_auth(self, genome: Genome, service: str) -> str:
        """Get authentication method for a service"""
        # Simplified - in reality this would be service-specific
        if service == "auth":
            return genome.auth
        return "inherit"
    
    def _get_service_features(self, genome: Genome, service: str) -> Dict[str, Any]:
        """Get features for a service"""
        features = {
            "service": service,
            "cache_enabled": genome.cache_enabled,
            "rate_limiting": genome.rate_limiting,
            "tracing_enabled": genome.tracing_enabled
        }
        
        # Add service-specific features
        if service in ["payments", "users"]:
            features["auth_required"] = True
        if service == "analytics":
            features["heavy_computation"] = True
            
        return features
    
    def _analyze_service_dependencies(self, genome: Genome) -> Dict[str, List[str]]:
        """Analyze service dependencies"""
        dependencies = {}
        
        for service in genome.services:
            # Simplified dependency analysis
            if service == "auth":
                dependencies[service] = []
            elif service in ["users", "payments", "admin"]:
                dependencies[service] = ["auth"]
            elif service in ["analytics", "notifications"]:
                dependencies[service] = ["users", "auth"]
            else:
                dependencies[service] = ["auth"]
                
        return dependencies
    
    def _calculate_service_risk_impact(self, added: List[str], removed: List[str]) -> float:
        """Calculate risk impact from service changes"""
        risk_score = 0.0
        
        # High-risk services
        high_risk_services = ["payments", "auth", "admin"]
        
        for service in added:
            if service in high_risk_services:
                risk_score += 0.3
            else:
                risk_score += 0.1
                
        for service in removed:
            if service in high_risk_services:
                risk_score -= 0.3
            else:
                risk_score -= 0.1
                
        return max(0.0, risk_score)
    
    def _compare_endpoints(self, baseline: Genome, candidate: Genome) -> EndpointDiff:
        """Compare endpoint configurations"""
        baseline_endpoints = self._collect_endpoints(baseline)
        candidate_endpoints = self._collect_endpoints(candidate)
        
        # Find differences
        added_endpoints = []
        removed_endpoints = []
        modified_endpoints = []
        
        # Check for new endpoints
        for endpoint in candidate_endpoints:
            if endpoint not in baseline_endpoints:
                added_endpoints.append(endpoint)
                
        # Check for removed endpoints
        for endpoint in baseline_endpoints:
            if endpoint not in candidate_endpoints:
                removed_endpoints.append(endpoint)
                
        # Check for modified endpoints
        for endpoint in candidate_endpoints:
            if endpoint in baseline_endpoints:
                baseline_endpoint = next(e for e in baseline_endpoints if e["path"] == endpoint["path"])
                if self._is_endpoint_modified(baseline_endpoint, endpoint):
                    modified_endpoints.append(endpoint)
        
        # Calculate endpoint coverage
        total_endpoints = len(baseline_endpoints) + len(added_endpoints)
        endpoint_coverage = len(candidate_endpoints) / max(total_endpoints, 1)
        
        # Calculate API compatibility
        api_compatibility_score = self._calculate_api_compatibility(baseline, candidate)
        
        return EndpointDiff(
            added_endpoints=added_endpoints,
            removed_endpoints=removed_endpoints,
            modified_endpoints=modified_endpoints,
            endpoint_coverage=endpoint_coverage,
            api_compatibility_score=api_compatibility_score
        )
    
    def _collect_endpoints(self, genome: Genome) -> List[Dict[str, Any]]:
        """Collect all endpoints for a genome"""
        endpoints = []
        
        for service in genome.services:
            service_endpoints = self._get_service_endpoints(service, genome)
            endpoints.extend(service_endpoints)
            
        return endpoints
    
    def _get_service_endpoints(self, service: str, genome: Genome) -> List[Dict[str, Any]]:
        """Get endpoints for a specific service"""
        # Standard REST endpoints
        base_endpoints = [
            {"service": service, "path": f"/{service}", "method": "GET"},
            {"service": service, "path": f"/{service}", "method": "POST"},
            {"service": service, "path": f"/{service}/{{id}}", "method": "GET"},
            {"service": service, "path": f"/{service}/{{id}}", "method": "PUT"},
            {"service": service, "path": f"/{service}/{{id}}", "method": "DELETE"}
        ]
        
        # Service-specific endpoints
        service_specific = {
            "auth": [
                {"service": "auth", "path": "/auth/login", "method": "POST"},
                {"service": "auth", "path": "/auth/logout", "method": "POST"},
                {"service": "auth", "path": "/auth/refresh", "method": "POST"}
            ],
            "users": [
                {"service": "users", "path": "/users/profile", "method": "GET"},
                {"service": "users", "path": "/users/profile", "method": "PUT"}
            ],
            "payments": [
                {"service": "payments", "path": "/payments/process", "method": "POST"},
                {"service": "payments", "path": "/payments/refund", "method": "POST"}
            ]
        }
        
        if service in service_specific:
            base_endpoints.extend(service_specific[service])
            
        return base_endpoints
    
    def _is_endpoint_modified(self, baseline: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        """Check if an endpoint has been modified"""
        # Compare basic properties
        if baseline["method"] != candidate["method"]:
            return True
            
        # Compare auth requirements
        baseline_auth = self._get_endpoint_auth(baseline, baseline["service"])
        candidate_auth = self._get_endpoint_auth(candidate, candidate["service"])
        
        return baseline_auth != candidate_auth
    
    def _get_endpoint_auth(self, endpoint: Dict[str, Any], service: str) -> bool:
        """Determine if an endpoint requires authentication"""
        # Public endpoints
        if endpoint["path"] in ["/auth/login", "/auth/register"]:
            return False
            
        # Service-specific rules
        if service in ["analytics", "search"]:
            return False
            
        return True
    
    def _calculate_api_compatibility(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate API compatibility score"""
        compatibility = 0.0
        
        # Check authentication compatibility
        if baseline.auth == candidate.auth:
            compatibility += 0.3
            
        # Check database compatibility
        if baseline.database == candidate.database:
            compatibility += 0.2
            
        # Check service compatibility
        common_services = len(set(baseline.services) & set(candidate.services))
        total_services = len(set(baseline.services) | set(candidate.services))
        service_compatibility = common_services / max(total_services, 1)
        compatibility += service_compatibility * 0.3
        
        # Check configuration compatibility
        config_compatibility = self._calculate_config_compatibility(baseline, candidate)
        compatibility += config_compatibility * 0.2
        
        return min(compatibility, 1.0)
    
    def _calculate_config_compatibility(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate configuration compatibility"""
        compatibility = 0.0
        
        # Check middleware compatibility
        baseline_middleware = set(baseline.middleware)
        candidate_middleware = set(candidate.middleware)
        common_middleware = len(baseline_middleware & candidate_middleware)
        total_middleware = len(baseline_middleware | candidate_middleware)
        middleware_compatibility = common_middleware / max(total_middleware, 1)
        compatibility += middleware_compatibility * 0.5
        
        # Check backend compatibility
        baseline_backends = {b["type"] for b in baseline.backends}
        candidate_backends = {b["type"] for b in candidate.backends}
        common_backends = len(baseline_backends & candidate_backends)
        total_backends = len(baseline_backends | candidate_backends)
        backend_compatibility = common_backends / max(total_backends, 1)
        compatibility += backend_compatibility * 0.5
        
        return compatibility
    
    def _compare_security_policies(self, baseline: Genome, candidate: Genome) -> SecurityPolicyDiff:
        """Compare security policies"""
        baseline_policies = baseline.security_policies
        candidate_policies = candidate.security_policies
        
        # Find policy differences
        added_policies = []
        removed_policies = []
        modified_policies = []
        
        # Check for new policies
        for policy in candidate_policies:
            if not any(self._is_same_policy(bp, policy) for bp in baseline_policies):
                added_policies.append(policy)
                
        # Check for removed policies
        for policy in baseline_policies:
            if not any(self._is_same_policy(cp, policy) for cp in candidate_policies):
                removed_policies.append(policy)
                
        # Check for modified policies
        for policy in candidate_policies:
            for baseline_policy in baseline_policies:
                if self._is_same_policy(baseline_policy, policy):
                    if self._is_policy_modified(baseline_policy, policy):
                        modified_policies.append(policy)
                    break
        
        # Calculate security improvement
        security_improvement = self._calculate_security_improvement(baseline, candidate)
        
        # Find compliance gaps
        compliance_gaps = self._find_compliance_gaps(candidate)
        
        return SecurityPolicyDiff(
            added_policies=added_policies,
            removed_policies=removed_policies,
            modified_policies=modified_policies,
            security_improvement=security_improvement,
            compliance_gaps=compliance_gaps
        )
    
    def _is_same_policy(self, policy1: Dict[str, Any], policy2: Dict[str, Any]) -> bool:
        """Check if two policies are the same type"""
        return policy1.get("type") == policy2.get("type")
    
    def _is_policy_modified(self, baseline: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        """Check if a policy has been modified"""
        # Compare policy properties
        for key in baseline:
            if key in candidate and baseline[key] != candidate[key]:
                return True
        return False
    
    def _calculate_security_improvement(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate security improvement score"""
        improvement = 0.0
        
        # Check authentication strength improvement
        auth_scores = {"basic": 0.3, "api_key": 0.6, "jwt": 0.9, "oauth2": 1.0}
        baseline_auth_score = auth_scores.get(baseline.auth, 0.0)
        candidate_auth_score = auth_scores.get(candidate.auth, 0.0)
        improvement += (candidate_auth_score - baseline_auth_score) * 0.4
        
        # Check security features
        baseline_features = sum(1 for _ in baseline.security_policies)
        candidate_features = sum(1 for _ in candidate.security_policies)
        improvement += (candidate_features - baseline_features) * 0.1
        
        # Check rate limiting
        if candidate.rate_limiting and not baseline.rate_limiting:
            improvement += 0.2
            
        # Check CORS
        if candidate.cors_enabled and not baseline.cors_enabled:
            improvement += 0.1
            
        # Check tracing
        if candidate.tracing_enabled and not baseline.tracing_enabled:
            improvement += 0.1
            
        # Check circuit breaker
        if candidate.circuit_breaker and not baseline.circuit_breaker:
            improvement += 0.1
            
        return max(0.0, improvement)
    
    def _find_compliance_gaps(self, genome: Genome) -> List[str]:
        """Find compliance gaps in security policies"""
        gaps = []
        
        # Check for missing rate limiting
        if not genome.rate_limiting:
            gaps.append("Missing rate limiting policy")
            
        # Check for weak authentication
        if genome.auth in ["basic", "api_key"] and len(genome.services) > 3:
            gaps.append("Weak authentication for multi-service architecture")
            
        # Check for missing health checks
        if not genome.health_endpoints:
            gaps.append("Missing health check endpoints")
            
        # Check for missing metrics
        if not genome.metrics_endpoints:
            gaps.append("Missing metrics endpoints")
            
        return gaps
    
    def _compare_databases(self, baseline: Genome, candidate: Genome) -> DatabaseDiff:
        """Compare database configurations"""
        schema_changes = []
        migration_impact = "low"
        data_loss_risk = 0.0
        performance_impact = 0.0
        
        # Check database changes
        if baseline.database != candidate.database:
            schema_changes.append({
                "type": "database_change",
                "from": baseline.database,
                "to": candidate.database,
                "impact": "high"
            })
            migration_impact = "high"
            data_loss_risk = 0.3
            performance_impact = 0.2
            
        # Check schema changes
        if baseline.services != candidate.services:
            schema_changes.append({
                "type": "schema_change",
                "services_added": list(set(candidate.services) - set(baseline.services)),
                "services_removed": list(set(baseline.services) - set(candidate.services)),
                "impact": "medium"
            })
            
        # Calculate performance impact
        if candidate.cache_enabled and not baseline.cache_enabled:
            performance_impact += 0.3
            
        if len(candidate.backends) > len(baseline.backends):
            performance_impact += 0.1
            
        return DatabaseDiff(
            schema_changes=schema_changes,
            migration_impact=migration_impact,
            data_loss_risk=data_loss_risk,
            performance_impact=performance_impact
        )
    
    def _compare_cost_performance(self, baseline: Genome, candidate: Genome) -> CostPerformanceDiff:
        """Compare cost and performance characteristics"""
        # Calculate cost change
        baseline_cost = self._estimate_cost(baseline)
        candidate_cost = self._estimate_cost(candidate)
        cost_change = (candidate_cost - baseline_cost) / baseline_cost
        
        # Calculate performance change
        baseline_performance = self._estimate_performance(baseline)
        candidate_performance = self._estimate_performance(candidate)
        performance_change = (candidate_performance - baseline_performance) / baseline_performance
        
        # Calculate ROI score
        roi_score = self._calculate_roi(candidate_cost, candidate_performance)
        
        # Calculate scalability impact
        scalability_impact = self._calculate_scalability_impact(candidate)
        
        return CostPerformanceDiff(
            cost_change=cost_change,
            performance_change=performance_change,
            roi_score=roi_score,
            scalability_impact=scalability_impact
        )
    
    def _estimate_cost(self, genome: Genome) -> float:
        """Estimate deployment cost"""
        cost = 0.0
        
        # Service costs
        cost += len(genome.services) * 50.0
        
        # Database costs
        db_costs = {"sqlite": 0.0, "mysql": 30.0, "postgres": 40.0}
        cost += db_costs.get(genome.database, 0.0)
        
        # Backend costs
        for backend in genome.backends:
            cost += 20.0 if backend["type"] == "cache" else 50.0
            
        # Optimization costs (reductions)
        if genome.cache_enabled:
            cost *= 0.9
        if genome.circuit_breaker:
            cost *= 0.95
            
        return cost
    
    def _estimate_performance(self, genome: Genome) -> float:
        """Estimate performance score"""
        performance = 1.0
        
        # Service count impact
        performance -= len(genome.services) * 0.05
        
        # Database impact
        db_performance = {"sqlite": 1.0, "mysql": 0.8, "postgres": 0.7}
        performance *= db_performance.get(genome.database, 0.8)
        
        # Optimization impact
        if genome.cache_enabled:
            performance *= 1.2
        if genome.circuit_breaker:
            performance *= 1.1
            
        return performance
    
    def _calculate_roi(self, cost: float, performance: float) -> float:
        """Calculate ROI score"""
        return (performance - 1.0) / max(cost, 1.0)
    
    def _calculate_scalability_impact(self, genome: Genome) -> float:
        """Calculate scalability impact"""
        scalability = 1.0
        
        # Service count impact
        scalability -= len(genome.services) * 0.1
        
        # Backend impact
        for backend in genome.backends:
            if backend["type"] == "message_queue":
                scalability *= 1.2
            elif backend["type"] == "cache":
                scalability *= 1.1
                
        # Configuration impact
        if genome.circuit_breaker:
            scalability *= 1.1
        if genome.retry_policy:
            scalability *= 1.05
            
        return scalability
    
    def _calculate_similarity(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate overall similarity between two genomes"""
        similarity = 0.0
        
        # Service similarity
        common_services = len(set(baseline.services) & set(candidate.services))
        total_services = len(set(baseline.services) | set(candidate.services))
        service_similarity = common_services / max(total_services, 1)
        similarity += service_similarity * 0.3
        
        # Auth similarity
        auth_similarity = 1.0 if baseline.auth == candidate.auth else 0.0
        similarity += auth_similarity * 0.2
        
        # Database similarity
        db_similarity = 1.0 if baseline.database == candidate.database else 0.0
        similarity += db_similarity * 0.1
        
        # Configuration similarity
        config_similarity = self._calculate_config_similarity(baseline, candidate)
        similarity += config_similarity * 0.2
        
        # Feature similarity
        feature_similarity = self._calculate_feature_similarity(baseline, candidate)
        similarity += feature_similarity * 0.2
        
        return similarity
    
    def _calculate_config_similarity(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate configuration similarity"""
        similarity = 0.0
        
        # Middleware similarity
        baseline_middleware = set(baseline.middleware)
        candidate_middleware = set(candidate.middleware)
        common_middleware = len(baseline_middleware & candidate_middleware)
        middleware_similarity = common_middleware / max(len(baseline_middleware | candidate_middleware), 1)
        similarity += middleware_similarity * 0.5
        
        # Backend similarity
        baseline_backends = set(b["type"] for b in baseline.backends)
        candidate_backends = set(b["type"] for b in candidate.backends)
        common_backends = len(baseline_backends & candidate_backends)
        backend_similarity = common_backends / max(len(baseline_backends | candidate_backends), 1)
        similarity += backend_similarity * 0.5
        
        return similarity
    
    def _calculate_feature_similarity(self, baseline: Genome, candidate: Genome) -> float:
        """Calculate feature similarity"""
        similarity = 0.0
        features_checked = 0
        
        # Check feature matches
        if baseline.cache_enabled == candidate.cache_enabled:
            similarity += 1.0
        features_checked += 1
        
        if baseline.rate_limiting == candidate.rate_limiting:
            similarity += 1.0
        features_checked += 1
        
        if baseline.cors_enabled == candidate.cors_enabled:
            similarity += 1.0
        features_checked += 1
        
        if baseline.tracing_enabled == candidate.tracing_enabled:
            similarity += 1.0
        features_checked += 1
        
        if baseline.circuit_breaker == candidate.circuit_breaker:
            similarity += 1.0
        features_checked += 1
        
        return similarity / max(features_checked, 1)
    
    def _generate_recommendation(self, baseline: Genome, candidate: Genome, 
                               *diffs) -> Tuple[str, List[str]]:
        """Generate recommendation and tradeoffs"""
        tradeoffs = []
        
        # Analyze the diffs
        for diff in diffs:
            if hasattr(diff, 'added_services') and diff.added_services:
                tradeoffs.append(f"Added services: {', '.join(diff.added_services)}")
            if hasattr(diff, 'removed_services') and diff.removed_services:
                tradeoffs.append(f"Removed services: {', '.join(diff.removed_services)}")
            if hasattr(diff, 'security_improvement') and diff.security_improvement > 0:
                tradeoffs.append(f"Security improvement: {diff.security_improvement:.2f}")
            if hasattr(diff, 'cost_change') and diff.cost_change != 0:
                tradeoffs.append(f"Cost change: {diff.cost_change:+.1%}")
        
        # Generate recommendation based on overall factors
        baseline_score = baseline.get_production_score()
        candidate_score = candidate.get_production_score()
        
        if candidate_score > baseline_score + 0.1:
            recommendation = "RECOMMEND - Candidate architecture shows significant improvement"
        elif candidate_score > baseline_score:
            recommendation = "RECOMMEND - Candidate architecture shows marginal improvement"
        elif abs(candidate_score - baseline_score) < 0.05:
            recommendation = "NEUTRAL - Candidate architecture is similar to baseline"
        else:
            recommendation = "NOT RECOMMENDED - Candidate architecture shows degradation"
        
        # Add specific reasons
        if candidate_score > baseline_score:
            tradeoffs.append(f"Production score improved from {baseline_score:.3f} to {candidate_score:.3f}")
        else:
            tradeoffs.append(f"Production score decreased from {baseline_score:.3f} to {candidate_score:.3f}")
        
        return recommendation, tradeoffs