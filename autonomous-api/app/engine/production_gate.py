"""
Production Readiness Gate
========================

This module implements a production readiness gate that blocks generated APIs
unless they pass comprehensive production checks.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from app.engine.genome import Genome
from app.engine.production_analyzers import ProductionFitnessScorer


class GateResult(Enum):
    """Gate evaluation results"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class CheckType(Enum):
    """Types of production checks"""
    AUTH = "auth"
    SECURITY = "security"
    ANALYSIS = "analysis"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    MONITORING = "monitoring"
    COMPLIANCE = "compliance"


@dataclass
class GateCheck:
    """Individual gate check result"""
    check_type: CheckType
    name: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class GateEvaluation:
    """Complete gate evaluation result"""
    overall_result: GateResult
    checks: List[GateCheck]
    total_score: float
    passed_checks: int
    failed_checks: int
    warning_checks: int
    blocking_issues: List[str]
    recommendations: List[str]
    deployment_readiness: float


class ProductionReadinessGate:
    """
    Production readiness gate that validates generated APIs against
    production deployment requirements.
    """
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.fitness_scorer = ProductionFitnessScorer()
        self.min_scores = {
            "auth_coverage": 0.8,
            "security_score": 0.8,
            "openapi_completeness": 0.7,
            "observability_coverage": 0.7,
            "migration_safety": 0.6,
            "test_coverage_score": 0.6
        }
        self.required_features = [
            "health_endpoints",
            "metrics_endpoints",
            "rate_limiting",
            "cors_enabled"
        ]
        
    def evaluate_genome(self, genome: Genome, deployment_target: str = "docker-compose") -> GateEvaluation:
        """
        Evaluate a genome against production readiness criteria.
        
        Args:
            genome: The genome to evaluate
            deployment_target: Target deployment environment
            
        Returns:
            GateEvaluation with detailed results
        """
        checks = []
        blocking_issues = []
        recommendations = []
        
        # Run all production checks
        auth_check = self._check_authentication(genome)
        checks.append(auth_check)
        
        security_check = self._check_security(genome)
        checks.append(security_check)
        
        analysis_check = self._check_production_analysis(genome)
        checks.append(analysis_check)
        
        deployment_check = self._check_deployment_readiness(genome, deployment_target)
        checks.append(deployment_check)
        
        testing_check = self._check_testing_requirements(genome)
        checks.append(testing_check)
        
        monitoring_check = self._check_monitoring_requirements(genome)
        checks.append(monitoring_check)
        
        compliance_check = self._check_compliance_requirements(genome)
        checks.append(compliance_check)
        
        # Calculate overall results
        total_score = sum(check.score for check in checks)
        passed_checks = sum(1 for check in checks if check.passed)
        failed_checks = sum(1 for check in checks if not check.passed)
        warning_checks = sum(1 for check in checks if check.severity == "warning")
        
        # Determine overall result
        overall_result = self._determine_overall_result(checks)
        
        # Collect blocking issues
        blocking_issues = [
            check.message for check in checks 
            if not check.passed and check.severity in ["high", "critical"]
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(checks)
        
        # Calculate deployment readiness
        deployment_readiness = self._calculate_deployment_readiness(checks, genome)
        
        return GateEvaluation(
            overall_result=overall_result,
            checks=checks,
            total_score=total_score,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            blocking_issues=blocking_issues,
            recommendations=recommendations,
            deployment_readiness=deployment_readiness
        )
    
    def _check_authentication(self, genome: Genome) -> GateCheck:
        """Check authentication requirements"""
        passed = True
        score = 0.0
        message = ""
        details = {}
        
        # Check auth method strength
        auth_scores = {
            "oauth2": 1.0,
            "jwt": 0.9,
            "api_key": 0.6,
            "basic": 0.3
        }
        
        auth_score = auth_scores.get(genome.auth, 0.0)
        details["auth_method"] = genome.auth
        details["auth_score"] = auth_score
        
        # Check for multi-service auth requirements
        if len(genome.services) > 3 and genome.auth in ["basic", "api_key"]:
            passed = False
            message = f"Weak authentication method ({genome.auth}) for multi-service architecture"
            details["recommendation"] = "Use JWT or OAuth2 for multi-service architectures"
            score = 0.3
        elif auth_score < self.min_scores["auth_coverage"]:
            passed = False
            message = f"Authentication method ({genome.auth}) does not meet minimum coverage requirements"
            score = auth_score
        else:
            message = "Authentication requirements satisfied"
            score = auth_score
            
        # Check for security policies
        if genome.security_policies:
            details["security_policies"] = len(genome.security_policies)
            score += min(len(genome.security_policies) * 0.1, 0.2)
            
        return GateCheck(
            check_type=CheckType.AUTH,
            name="Authentication Check",
            passed=passed,
            score=min(score, 1.0),
            message=message,
            details=details,
            severity="high" if not passed else "medium"
        )
    
    def _check_security(self, genome: Genome) -> GateCheck:
        """Check security requirements"""
        passed = True
        score = 0.0
        message = ""
        details = {}
        
        # Check rate limiting
        if not genome.rate_limiting:
            passed = False
            message = "Rate limiting not implemented"
            details["missing_features"] = ["rate_limiting"]
            score = 0.5
        else:
            score += 0.3
            details["rate_limiting"] = "enabled"
            
        # Check CORS
        if not genome.cors_enabled:
            passed = False
            message = "CORS not configured"
            details["missing_features"] = ["cors_enabled"]
            score = 0.6
        else:
            score += 0.2
            details["cors"] = "enabled"
            
        # Check security headers
        security_features = [
            genome.tracing_enabled,
            genome.circuit_breaker,
            genome.health_endpoints,
            genome.metrics_endpoints
        ]
        
        security_score = sum(security_features) / len(security_features)
        score += security_score * 0.3
        details["security_features"] = {
            "tracing": genome.tracing_enabled,
            "circuit_breaker": genome.circuit_breaker,
            "health_checks": genome.health_endpoints,
            "metrics": genome.metrics_endpoints
        }
        
        if score < self.min_scores["security_score"]:
            passed = False
            message = "Security requirements not fully met"
            
        return GateCheck(
            check_type=CheckType.SECURITY,
            name="Security Check",
            passed=passed,
            score=min(score, 1.0),
            message=message,
            details=details,
            severity="high" if not passed else "medium"
        )
    
    def _check_production_analysis(self, genome: Genome) -> GateCheck:
        """Check production analysis requirements"""
        # Use production fitness scorer
        analysis_results = self.fitness_scorer.score_genome(genome)
        score = analysis_results["production_score"]
        
        # Check individual metrics
        checks = []
        
        if genome.metrics.openapi_completeness < self.min_scores["openapi_completeness"]:
            checks.append("OpenAPI completeness")
            
        if genome.metrics.auth_coverage < self.min_scores["auth_coverage"]:
            checks.append("Auth coverage")
            
        if genome.metrics.migration_safety < self.min_scores["migration_safety"]:
            checks.append("Migration safety")
            
        if genome.metrics.observability_coverage < self.min_scores["observability_coverage"]:
            checks.append("Observability coverage")
            
        if genome.metrics.test_coverage_score < self.min_scores["test_coverage_score"]:
            checks.append("Test coverage")
            
        passed = len(checks) == 0
        message = "Production analysis requirements satisfied" if passed else f"Missing: {', '.join(checks)}"
        
        return GateCheck(
            check_type=CheckType.ANALYSIS,
            name="Production Analysis Check",
            passed=passed,
            score=score,
            message=message,
            details=analysis_results,
            severity="medium" if not passed else "low"
        )
    
    def _check_deployment_readiness(self, genome: Genome, deployment_target: str) -> GateCheck:
        """Check deployment readiness for target environment"""
        passed = True
        score = 0.0
        message = ""
        details = {"deployment_target": deployment_target}
        
        # Check target-specific requirements
        if deployment_target == "docker-compose":
            requirements = self._get_docker_compose_requirements(genome)
        elif deployment_target in ["kubernetes", "aws-ecs", "render"]:
            requirements = self._get_cloud_requirements(genome)
        else:
            requirements = self._get_local_requirements(genome)
            
        # Evaluate requirements
        met_requirements = 0
        for requirement, met in requirements.items():
            details[requirement] = met
            if met:
                met_requirements += 1
                score += 1.0 / len(requirements)
                
        passed = met_requirements >= len(requirements) * 0.8  # 80% threshold
        
        if not passed:
            missing = [req for req, met in requirements.items() if not met]
            message = f"Deployment requirements not met: {', '.join(missing)}"
            
        return GateCheck(
            check_type=CheckType.DEPLOYMENT,
            name=f"Deployment Readiness Check ({deployment_target})",
            passed=passed,
            score=score,
            message=message,
            details=details,
            severity="high" if not passed else "medium"
        )
    
    def _get_docker_compose_requirements(self, genome: Genome) -> Dict[str, bool]:
        """Get Docker Compose specific requirements"""
        requirements = {
            "health_endpoints": genome.health_endpoints,
            "metrics_endpoints": genome.metrics.endpoints,
            "proper_database": genome.database in ["postgres", "mysql"],
            "cache_configured": genome.cache_enabled,
            "logging_configured": genome.logging_level != "DEBUG",
            "cors_enabled": genome.cors_enabled
        }
        return requirements
    
    def _get_cloud_requirements(self, genome: Genome) -> Dict[str, bool]:
        """Get cloud deployment requirements"""
        requirements = {
            "health_endpoints": genome.health_endpoints,
            "metrics_endpoints": genome.metrics_endpoints,
            "proper_database": genome.database in ["postgres", "mysql"],
            "cache_configured": genome.cache_enabled,
            "circuit_breaker": genome.circuit_breaker,
            "tracing_enabled": genome.tracing_enabled,
            "rate_limiting": genome.rate_limiting,
            "security_policies": len(genome.security_policies) > 0
        }
        return requirements
    
    def _get_local_requirements(self, genome: Genome) -> Dict[str, bool]:
        """Get local development requirements"""
        requirements = {
            "health_endpoints": genome.health_endpoints,
            "basic_auth": genome.auth in ["jwt", "api_key"],
            "cors_enabled": genome.cors_enabled,
            "logging_configured": genome.logging_level != "DEBUG"
        }
        return requirements
    
    def _check_testing_requirements(self, genome: Genome) -> GateCheck:
        """Check testing requirements"""
        # Estimate test coverage
        test_coverage = self.fitness_scorer._estimate_test_coverage(genome)
        
        # Check for test-related features
        has_tests = test_coverage > 0.5
        has_integration_tests = len(genome.services) > 1 and genome.tracing_enabled
        has_performance_tests = genome.circuit_breaker or genome.retry_policy
        
        score = test_coverage
        if has_integration_tests:
            score += 0.2
        if has_performance_tests:
            score += 0.1
            
        passed = test_coverage >= self.min_scores["test_coverage_score"]
        
        message = "Testing requirements satisfied" if passed else f"Test coverage too low: {test_coverage:.2f}"
        
        return GateCheck(
            check_type=CheckType.TESTING,
            name="Testing Requirements Check",
            passed=passed,
            score=min(score, 1.0),
            message=message,
            details={
                "estimated_coverage": test_coverage,
                "integration_tests": has_integration_tests,
                "performance_tests": has_performance_tests
            },
            severity="medium" if not passed else "low"
        )
    
    def _check_monitoring_requirements(self, genome: Genome) -> GateCheck:
        """Check monitoring and observability requirements"""
        score = 0.0
        details = {}
        
        # Check observability features
        observability_features = [
            (genome.health_endpoints, "health_checks"),
            (genome.metrics_endpoints, "metrics"),
            (genome.tracing_enabled, "tracing")
        ]
        
        for feature, name in observability_features:
            if feature:
                score += 0.3
                details[name] = "enabled"
            else:
                details[name] = "disabled"
                
        # Check database monitoring
        if genome.database in ["postgres", "mysql"]:
            score += 0.1
            details["database_monitoring"] = "supported"
        else:
            details["database_monitoring"] = "limited"
            
        passed = score >= self.min_scores["observability_coverage"]
        
        message = "Monitoring requirements satisfied" if passed else "Insufficient monitoring capabilities"
        
        return GateCheck(
            check_type=CheckType.MONITORING,
            name="Monitoring Requirements Check",
            passed=passed,
            score=score,
            message=message,
            details=details,
            severity="medium" if not passed else "low"
        )
    
    def _check_compliance_requirements(self, genome: Genome) -> GateCheck:
        """Check compliance requirements"""
        score = 0.0
        details = {}
        issues = []
        
        # GDPR compliance (PII handling)
        has_pii_services = any(service in ["users", "payments", "admin"] for service in genome.services)
        if has_pii_services and not genome.tracing_enabled:
            issues.append("PII services require tracing for audit logs")
            score -= 0.2
        else:
            score += 0.2
            
        # SOC2 compliance (access controls)
        if genome.auth in ["jwt", "oauth2"]:
            score += 0.2
            details["access_controls"] = "strong"
        else:
            details["access_controls"] = "weak"
            
        # PCI compliance (payment services)
        if "payments" in genome.services:
            if genome.auth == "jwt" and genome.rate_limiting:
                score += 0.3
                details["pci_compliance"] = "compliant"
            else:
                issues.append("Payment services require JWT auth and rate limiting")
                score -= 0.3
                
        # HIPAA compliance (health data)
        health_services = ["users", "admin"]  # Simplified
        if any(service in health_services for service in genome.services):
            if genome.tracing_enabled and genome.security_policies:
                score += 0.2
                details["hipaa_compliance"] = "compliant"
            else:
                issues.append("Health services require tracing and security policies")
                score -= 0.2
                
        score = max(0.0, score)
        passed = score >= 0.7  # 70% compliance threshold
        
        message = "Compliance requirements satisfied" if passed else f"Compliance issues: {', '.join(issues)}"
        
        return GateCheck(
            check_type=CheckType.COMPLIANCE,
            name="Compliance Requirements Check",
            passed=passed,
            score=score,
            message=message,
            details=details,
            severity="high" if not passed else "medium"
        )
    
    def _determine_overall_result(self, checks: List[GateCheck]) -> GateResult:
        """Determine overall gate evaluation result"""
        critical_failures = [check for check in checks if not check.passed and check.severity == "critical"]
        high_failures = [check for check in checks if not check.passed and check.severity == "high"]
        warnings = [check for check in checks if check.severity == "warning"]
        
        if critical_failures:
            return GateResult.FAILED
        elif high_failures:
            if self.strict_mode:
                return GateResult.FAILED
            else:
                return GateResult.WARNING
        elif warnings:
            return GateResult.WARNING
        else:
            return GateResult.PASSED
    
    def _generate_recommendations(self, checks: List[GateCheck]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        for check in checks:
            if not check.passed or check.severity == "warning":
                if "recommendation" in check.details:
                    recommendations.append(check.details["recommendation"])
                elif check.message:
                    recommendations.append(f"Improve: {check.message}")
                    
        # Remove duplicates
        unique_recommendations = list(set(recommendations))
        
        # Prioritize critical recommendations
        prioritized = []
        for rec in unique_recommendations:
            if any(word in rec.lower() for word in ["security", "auth", "critical"]):
                prioritized.insert(0, rec)
            else:
                prioritized.append(rec)
                
        return prioritized[:10]  # Top 10 recommendations
    
    def _calculate_deployment_readiness(self, checks: List[GateCheck], genome: Genome) -> float:
        """Calculate overall deployment readiness score"""
        # Weight different check types
        check_weights = {
            CheckType.AUTH: 0.2,
            CheckType.SECURITY: 0.2,
            CheckType.ANALYSIS: 0.2,
            CheckType.DEPLOYMENT: 0.15,
            CheckType.TESTING: 0.1,
            CheckType.MONITORING: 0.1,
            CheckType.COMPLIANCE: 0.05
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for check in checks:
            weight = check_weights.get(check.check_type, 0.1)
            total_score += check.score * weight
            total_weight += weight
            
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.0
    
    def should_deploy(self, genome: Genome, deployment_target: str = "docker-compose") -> Tuple[bool, str]:
        """
        Quick check if a genome should be deployed.
        
        Args:
            genome: The genome to check
            deployment_target: Target deployment environment
            
        Returns:
            Tuple of (should_deploy, reason)
        """
        evaluation = self.evaluate_genome(genome, deployment_target)
        
        if evaluation.overall_result == GateResult.PASSED:
            return True, "Production readiness gate passed"
        elif evaluation.overall_result == GateResult.WARNING:
            return not self.strict_mode, "Production readiness gate has warnings"
        else:
            return False, f"Production readiness gate failed: {evaluation.blocking_issues[0]}"
    
    def get_minimum_requirements(self) -> Dict[str, float]:
        """Get minimum requirements for each check type"""
        return self.min_scores.copy()
    
    def set_minimum_requirements(self, requirements: Dict[str, float]):
        """Set custom minimum requirements"""
        self.min_scores.update(requirements)
    
    def set_strict_mode(self, strict: bool):
        """Set strict mode for gate evaluation"""
        self.strict_mode = strict