"""
Policy-Aware Generation System
==============================

This module implements organization policies as constraints for genome generation.
Ensures evolved architectures comply with organizational requirements and standards.
"""

import json
import random
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from app.engine.genome import Genome, ServiceBlueprint


class PolicyType(Enum):
    """Types of organization policies"""
    TECHNICAL = "technical"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    COST = "cost"
    OPERATIONAL = "operational"
    ARCHITECTURE = "architecture"


class PolicyEnforcement(Enum):
    """Policy enforcement levels"""
    MANDATORY = "mandatory"  # Must comply
    RECOMMENDED = "recommended"  # Should comply
    OPTIONAL = "optional"  # Nice to have


@dataclass
class PolicyRule:
    """Individual policy rule"""
    rule_id: str
    name: str
    description: str
    policy_type: PolicyType
    enforcement: PolicyEnforcement
    constraints: Dict[str, Any]
    weight: float = 1.0
    exception_scenarios: List[str] = field(default_factory=list)


@dataclass
class PolicyViolation:
    """Policy violation result"""
    rule_id: str
    rule_name: str
    severity: str
    message: str
    suggestion: str
    violation_type: str
    genome_field: str


@dataclass
class PolicyCompliance:
    """Policy compliance results"""
    compliant: bool
    violations: List[PolicyViolation]
    score: float
    enforced_rules: int
    total_rules: int
    compliance_rate: float


class PolicyAwareGenerator:
    """
    Policy-aware genome generation system that enforces organization policies
    as constraints during evolution.
    """
    
    def __init__(self):
        self.policies: List[PolicyRule] = self._initialize_default_policies()
        self.policy_violations_history: List[PolicyViolation] = []
        self.compliance_statistics: Dict[str, int] = {}
        
    def _initialize_default_policies(self) -> List[PolicyRule]:
        """Initialize default organization policies"""
        policies = [
            # Technical Policies
            PolicyRule(
                rule_id="tech_db_requirement",
                name="Database Technology Requirement",
                description="Must use production-grade databases",
                policy_type=PolicyType.TECHNICAL,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "allowed_databases": ["postgres", "mysql"],
                    "blocked_databases": ["sqlite"],
                    "exception_scenarios": ["development", "testing"]
                },
                weight=2.0
            ),
            
            # Security Policies
            PolicyRule(
                rule_id="security_auth_minimum",
                name="Minimum Authentication Requirements",
                description="Must use strong authentication methods",
                policy_type=PolicyType.SECURITY,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "allowed_auth_methods": ["jwt", "oauth2"],
                    "blocked_auth_methods": ["basic", "api_key"],
                    "exception_scenarios": ["internal_tools", "legacy_systems"]
                },
                weight=3.0
            ),
            
            PolicyRule(
                rule_id="security_rate_limiting",
                name="Rate Limiting Requirement",
                description="All public APIs must have rate limiting",
                policy_type=PolicyType.SECURITY,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "require_rate_limiting": True,
                    "minimum_requests_per_minute": 100,
                    "exception_scenarios": ["internal_apis", "admin_interfaces"]
                },
                weight=2.5
            ),
            
            # Compliance Policies
            PolicyRule(
                rule_id="compliance_pii_protection",
                name="PII Data Protection",
                description="Services handling PII require additional protections",
                policy_type=PolicyType.COMPLIANCE,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "pii_services": ["users", "payments", "auth"],
                    "required_features": ["tracing", "audit_logs", "encryption"],
                    "blocked_features": ["basic_auth"]
                },
                weight=4.0
            ),
            
            # Performance Policies
            PolicyRule(
                rule_id="performance_cache_requirement",
                name="Caching Requirement",
                description="High-traffic services must implement caching",
                policy_type=PolicyType.PERFORMANCE,
                enforcement=PolicyEnforcement.RECOMMENDED,
                constraints={
                    "high_traffic_services": ["analytics", "search", "files"],
                    "required_backends": ["cache"],
                    "performance_threshold": 1000  # requests per minute
                },
                weight=1.5
            ),
            
            # Cost Policies
            PolicyRule(
                rule_id="cost_database_optimization",
                name="Database Cost Optimization",
                description="Optimize database usage for cost efficiency",
                policy_type=PolicyType.COST,
                enforcement=PolicyEnforcement.RECOMMENDED,
                constraints={
                    "max_services_per_database": 5,
                    "prefer_connection_pooling": True,
                    "blocked_expensive_operations": ["full_table_scans", "complex_joins"]
                },
                weight=1.0
            ),
            
            # Operational Policies
            PolicyRule(
                rule_id="operational_health_checks",
                name="Health Check Endpoints",
                description="All services must expose health check endpoints",
                policy_type=PolicyType.OPERATIONAL,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "require_health_endpoints": True,
                    "health_check_paths": ["/health", "/ready"],
                    "health_check_interval": 30
                },
                weight=2.0
            ),
            
            PolicyRule(
                rule_id="operational_monitoring",
                name="Monitoring Requirements",
                description="All services must expose metrics endpoints",
                policy_type=PolicyType.OPERATIONAL,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "require_metrics_endpoints": True,
                    "metrics_format": "prometheus",
                    "monitoring_targets": ["cpu", "memory", "requests", "errors"]
                },
                weight=1.5
            ),
            
            # Architecture Policies
            PolicyRule(
                rule_id="architecture_service_boundaries",
                name="Service Boundaries",
                description="Define clear service boundaries and dependencies",
                policy_type=PolicyType.ARCHITECTURE,
                enforcement=PolicyEnforcement.RECOMMENDED,
                constraints={
                    "max_services": 8,
                    "allowed_dependencies": {
                        "auth": ["users", "payments", "admin"],
                        "users": ["analytics", "notifications"],
                        "payments": ["analytics"]
                    },
                    "blocked_cycles": True
                },
                weight=1.8
            ),
            
            PolicyRule(
                rule_id="architecture_api_standards",
                name="API Standards",
                description="All APIs must follow organizational standards",
                policy_type=PolicyType.ARCHITECTURE,
                enforcement=PolicyEnforcement.MANDATORY,
                constraints={
                    "openapi_version": "3.0.0",
                    "require_documentation": True,
                    "api_version_prefix": True,
                    "blocked_methods": ["PATCH"]  # Example policy
                },
                weight=1.5
            )
        ]
        
        return policies
    
    def generate_policy_compliant_genome(self, base_genome: Optional[Genome] = None) -> Genome:
        """
        Generate a policy-compliant genome by applying policy constraints.
        
        Args:
            base_genome: Optional base genome to modify
            
        Returns:
            Policy-compliant genome
        """
        if base_genome:
            genome = Genome(base_genome.encode())  # Create a copy
        else:
            genome = Genome()  # Generate random genome
            
        # Apply policy constraints
        self._apply_policy_constraints(genome)
        
        # Validate compliance
        compliance = self.validate_genome_compliance(genome)
        
        # If not compliant, try to fix violations
        if not compliance.compliant:
            genome = self._fix_policy_violations(genome, compliance)
        
        return genome
    
    def _apply_policy_constraints(self, genome: Genome):
        """Apply policy constraints to a genome"""
        for policy in self.policies:
            if policy.enforcement == PolicyEnforcement.MANDATORY:
                self._apply_mandatory_policy(genome, policy)
            elif policy.enforcement == PolicyEnforcement.RECOMMENDED:
                self._apply_recommended_policy(genome, policy)
    
    def _apply_mandatory_policy(self, genome: Genome, policy: PolicyRule):
        """Apply a mandatory policy constraint"""
        if policy.rule_id == "tech_db_requirement":
            # Enforce database requirements
            if genome.database not in policy.constraints["allowed_databases"]:
                genome.database = random.choice(policy.constraints["allowed_databases"])
                
        elif policy.rule_id == "security_auth_minimum":
            # Enforce authentication requirements
            if genome.auth not in policy.constraints["allowed_auth_methods"]:
                genome.auth = random.choice(policy.constraints["allowed_auth_methods"])
                
        elif policy.rule_id == "security_rate_limiting":
            # Enforce rate limiting
            if not genome.rate_limiting:
                genome.rate_limiting = True
                
        elif policy.rule_id == "compliance_pii_protection":
            # Enforce PII protections
            pii_services = policy.constraints["pii_services"]
            if any(service in genome.services for service in pii_services):
                # Add required features
                if "tracing" not in genome.middleware:
                    genome.middleware.append("tracing")
                genome.tracing_enabled = True
                
        elif policy.rule_id == "operational_health_checks":
            # Enforce health checks
            genome.health_endpoints = True
            
        elif policy.rule_id == "operational_monitoring":
            # Enforce monitoring
            genome.metrics_endpoints = True
            
        elif policy.rule_id == "architecture_api_standards":
            # Enforce API standards
            genome.openapi_version = policy.constraints["openapi_version"]
    
    def _apply_recommended_policy(self, genome: Genome, policy: PolicyRule):
        """Apply a recommended policy constraint"""
        if policy.rule_id == "performance_cache_requirement":
            # Apply caching for high-traffic services
            high_traffic_services = policy.constraints["high_traffic_services"]
            if any(service in genome.services for service in high_traffic_services):
                if not genome.cache_enabled:
                    genome.cache_enabled = True
                    
        elif policy.rule_id == "cost_database_optimization":
            # Optimize database usage
            if len(genome.services) > policy.constraints["max_services_per_database"]:
                # Split services across multiple databases (simplified)
                if genome.database == "postgres":  # Only if using supported DB
                    pass  # In reality, would create database instances
                    
        elif policy.rule_id == "architecture_service_boundaries":
            # Apply service boundary constraints
            if len(genome.services) > policy.constraints["max_services"]:
                # Remove excess services
                genome.services = genome.services[:policy.constraints["max_services"]]
    
    def validate_genome_compliance(self, genome: Genome) -> PolicyCompliance:
        """
        Validate a genome against all policies.
        
        Args:
            genome: The genome to validate
            
        Returns:
            PolicyCompliance results
        """
        violations = []
        total_weight = 0.0
        violation_weight = 0.0
        
        for policy in self.policies:
            policy_violations = self._check_policy_compliance(genome, policy)
            
            if policy_violations:
                violations.extend(policy_violations)
                violation_weight += sum(v.weight for v in policy_violations)
            
            total_weight += policy.weight
        
        # Calculate compliance score
        if total_weight > 0:
            compliance_score = max(0.0, (total_weight - violation_weight) / total_weight)
        else:
            compliance_score = 1.0
            
        enforced_rules = len([p for p in self.policies if p.enforcement == PolicyEnforcement.MANDATORY])
        
        return PolicyCompliance(
            compliant=len(violations) == 0 and enforced_rules == 0,
            violations=violations,
            score=compliance_score,
            enforced_rules=enforced_rules,
            total_rules=len(self.policies),
            compliance_rate=compliance_score
        )
    
    def _check_policy_compliance(self, genome: Genome, policy: PolicyRule) -> List[PolicyViolation]:
        """Check a single policy compliance"""
        violations = []
        
        if policy.rule_id == "tech_db_requirement":
            if genome.database not in policy.constraints["allowed_databases"]:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="high" if policy.enforcement == PolicyEnforcement.MANDATORY else "medium",
                    message=f"Database {genome.database} not allowed",
                    suggestion=f"Use one of: {policy.constraints['allowed_databases']}",
                    violation_type="database_violation",
                    genome_field="database"
                ))
                
        elif policy.rule_id == "security_auth_minimum":
            if genome.auth not in policy.constraints["allowed_auth_methods"]:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="high" if policy.enforcement == PolicyEnforcement.MANDATORY else "medium",
                    message=f"Authentication method {genome.auth} not allowed",
                    suggestion=f"Use one of: {policy.constraints['allowed_auth_methods']}",
                    violation_type="auth_violation",
                    genome_field="auth"
                ))
                
        elif policy.rule_id == "security_rate_limiting":
            if not genome.rate_limiting:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="high" if policy.enforcement == PolicyEnforcement.MANDATORY else "medium",
                    message="Rate limiting not enabled",
                    suggestion="Enable rate limiting for public APIs",
                    violation_type="security_violation",
                    genome_field="rate_limiting"
                ))
                
        elif policy.rule_id == "operational_health_checks":
            if not genome.health_endpoints:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="high" if policy.enforcement == PolicyEnforcement.MANDATORY else "medium",
                    message="Health check endpoints not enabled",
                    suggestion="Enable health check endpoints",
                    violation_type="operational_violation",
                    genome_field="health_endpoints"
                ))
                
        elif policy.rule_id == "operational_monitoring":
            if not genome.metrics_endpoints:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="high" if policy.enforcement == PolicyEnforcement.MANDATORY else "medium",
                    message="Metrics endpoints not enabled",
                    suggestion="Enable metrics endpoints",
                    violation_type="operational_violation",
                    genome_field="metrics_endpoints"
                ))
                
        elif policy.rule_id == "architecture_service_boundaries":
            if len(genome.services) > policy.constraints["max_services"]:
                violations.append(PolicyViolation(
                    rule_id=policy.rule_id,
                    rule_name=policy.name,
                    severity="medium" if policy.enforcement == PolicyEnforcement.MANDATORY else "low",
                    message=f"Too many services: {len(genome.services)} (max: {policy.constraints['max_services']})",
                    suggestion="Reduce number of services or split into bounded contexts",
                    violation_type="architecture_violation",
                    genome_field="services"
                ))
        
        # Add weight to violations
        for violation in violations:
            violation.weight = policy.weight
            
        return violations
    
    def _fix_policy_violations(self, genome: Genome, compliance: PolicyCompliance) -> Genome:
        """Fix policy violations in a genome"""
        fixed_genome = Genome(genome.encode())  # Create a copy
        
        for violation in compliance.violations:
            if violation.severity == "high" or violation.rule_id.endswith("_requirement"):
                # Try to fix high-severity violations
                self._fix_violation(fixed_genome, violation)
        
        return fixed_genome
    
    def _fix_violation(self, genome: Genome, violation: PolicyViolation):
        """Fix a specific policy violation"""
        if violation.violation_type == "database_violation":
            # Fix database violation
            allowed_databases = ["postgres", "mysql"]
            genome.database = random.choice(allowed_databases)
            
        elif violation.violation_type == "auth_violation":
            # Fix auth violation
            allowed_auth = ["jwt", "oauth2"]
            genome.auth = random.choice(allowed_auth)
            
        elif violation.violation_type == "security_violation":
            # Fix security violation
            if "rate_limiting" in violation.genome_field:
                genome.rate_limiting = True
                
        elif violation.violation_type == "operational_violation":
            # Fix operational violation
            if "health_endpoints" in violation.genome_field:
                genome.health_endpoints = True
            elif "metrics_endpoints" in violation.genome_field:
                genome.metrics_endpoints = True
                
        elif violation.violation_type == "architecture_violation":
            # Fix architecture violation
            max_services = 8  # Default max
            if len(genome.services) > max_services:
                genome.services = genome.services[:max_services]
    
    def add_policy(self, policy: PolicyRule):
        """Add a new policy to the system"""
        self.policies.append(policy)
        
    def remove_policy(self, rule_id: str):
        """Remove a policy from the system"""
        self.policies = [p for p in self.policies if p.rule_id != rule_id]
        
    def get_policy_by_id(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a specific policy by ID"""
        for policy in self.policies:
            if policy.rule_id == rule_id:
                return policy
        return None
    
    def get_policies_by_type(self, policy_type: PolicyType) -> List[PolicyRule]:
        """Get all policies of a specific type"""
        return [p for p in self.policies if p.policy_type == policy_type]
    
    def get_policy_statistics(self) -> Dict[str, Any]:
        """Get policy compliance statistics"""
        total_policies = len(self.policies)
        mandatory_policies = len([p for p in self.policies if p.enforcement == PolicyEnforcement.MANDATORY])
        recommended_policies = len([p for p in self.policies if p.enforcement == PolicyEnforcement.RECOMMENDED])
        optional_policies = len([p for p in self.policies if p.enforcement == PolicyEnforcement.OPTIONAL])
        
        policies_by_type = {}
        for policy_type in PolicyType:
            policies_by_type[policy_type.value] = len(self.get_policies_by_type(policy_type))
        
        return {
            "total_policies": total_policies,
            "mandatory_policies": mandatory_policies,
            "recommended_policies": recommended_policies,
            "optional_policies": optional_policies,
            "policies_by_type": policies_by_type,
            "average_weight": sum(p.weight for p in self.policies) / max(total_policies, 1)
        }
    
    def export_policies(self, file_path: str):
        """Export policies to a file"""
        policies_data = [
            {
                "rule_id": p.rule_id,
                "name": p.name,
                "description": p.description,
                "policy_type": p.policy_type.value,
                "enforcement": p.enforcement.value,
                "constraints": p.constraints,
                "weight": p.weight,
                "exception_scenarios": p.exception_scenarios
            }
            for p in self.policies
        ]
        
        with open(file_path, 'w') as f:
            json.dump(policies_data, f, indent=2)
    
    def import_policies(self, file_path: str):
        """Import policies from a file"""
        with open(file_path, 'r') as f:
            policies_data = json.load(f)
        
        for policy_data in policies_data:
            policy = PolicyRule(
                rule_id=policy_data["rule_id"],
                name=policy_data["name"],
                description=policy_data["description"],
                policy_type=PolicyType(policy_data["policy_type"]),
                enforcement=PolicyEnforcement(policy_data["enforcement"]),
                constraints=policy_data["constraints"],
                weight=policy_data.get("weight", 1.0),
                exception_scenarios=policy_data.get("exception_scenarios", [])
            )
            self.add_policy(policy)
    
    def generate_policy_report(self, genome: Genome) -> Dict[str, Any]:
        """Generate a comprehensive policy compliance report"""
        compliance = self.validate_genome_compliance(genome)
        
        # Group violations by type
        violations_by_type = {}
        for violation in compliance.violations:
            violation_type = violation.violation_type
            if violation_type not in violations_by_type:
                violations_by_type[violation_type] = []
            violations_by_type[violation_type].append(violation)
        
        # Generate recommendations
        recommendations = []
        for violation in compliance.violations:
            recommendations.append(violation.suggestion)
        
        # Remove duplicates
        unique_recommendations = list(set(recommendations))
        
        return {
            "genome_id": genome.genome_id,
            "compliance_score": compliance.score,
            "compliant": compliance.compliant,
            "total_violations": len(compliance.violations),
            "mandatory_violations": len([v for v in compliance.violations if v.severity == "high"]),
            "recommended_violations": len([v for v in compliance.violations if v.severity == "medium"]),
            "violations_by_type": violations_by_type,
            "recommendations": unique_recommendations,
            "policy_summary": self.get_policy_statistics()
        }
    
    def simulate_policy_impact(self, base_genome: Genome, policy_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulate the impact of policy changes on genome generation.
        
        Args:
            base_genome: Base genome to evaluate
            policy_changes: List of policy modifications
            
        Returns:
            Simulation results
        """
        # Create a copy of policies
        original_policies = self.policies.copy()
        
        # Apply policy changes
        for change in policy_changes:
            if change["action"] == "add":
                new_policy = PolicyRule(
                    rule_id=change["rule_id"],
                    name=change["name"],
                    description=change["description"],
                    policy_type=PolicyType(change["policy_type"]),
                    enforcement=PolicyEnforcement(change["enforcement"]),
                    constraints=change["constraints"],
                    weight=change.get("weight", 1.0)
                )
                self.add_policy(new_policy)
            elif change["action"] == "remove":
                self.remove_policy(change["rule_id"])
            elif change["action"] == "modify":
                policy = self.get_policy_by_id(change["rule_id"])
                if policy:
                    for key, value in change["changes"].items():
                        if hasattr(policy, key):
                            setattr(policy, key, value)
        
        # Generate compliant genome
        compliant_genome = self.generate_policy_compliant_genome(base_genome)
        
        # Analyze impact
        original_compliance = self.validate_genome_compliance(base_genome)
        new_compliance = self.validate_genome_compliance(compliant_genome)
        
        # Restore original policies
        self.policies = original_policies
        
        return {
            "original_compliance": {
                "score": original_compliance.score,
                "violations": len(original_compliance.violations)
            },
            "new_compliance": {
                "score": new_compliance.score,
                "violations": len(new_compliance.violations)
            },
            "improvement": new_compliance.score - original_compliance.score,
            "policy_changes": policy_changes,
            "genome_changes": self._compare_genomes(base_genome, compliant_genome)
        }
    
    def _compare_genomes(self, genome1: Genome, genome2: Genome) -> Dict[str, Any]:
        """Compare two genomes"""
        differences = {}
        
        # Compare fields
        fields_to_compare = ["services", "auth", "database", "cache_enabled", 
                           "rate_limiting", "cors_enabled", "health_endpoints", 
                           "metrics_endpoints", "tracing_enabled"]
        
        for field in fields_to_compare:
            val1 = getattr(genome1, field)
            val2 = getattr(genome2, field)
            if val1 != val2:
                differences[field] = {"from": val1, "to": val2}
        
        return differences