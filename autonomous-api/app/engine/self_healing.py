"""
Self-Healing Evolution Runs
============================

This module implements self-healing capabilities for evolution runs that
learn from failures and automatically improve candidate architectures.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from app.engine.genome import Genome
from app.engine.production_gate import ProductionReadinessGate
from app.engine.production_analyzers import ProductionFitnessScorer


class FailureType(Enum):
    """Types of evolution failures"""
    BUILD_ERROR = "build_error"
    TEST_FAILURE = "test_failure"
    DEPLOYMENT_ERROR = "deployment_error"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE_FAILURE = "compliance_failure"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    CONFIGURATION_ERROR = "configuration_error"


class SeverityLevel(Enum):
    """Severity levels for failures"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureRecord:
    """Record of a failure event"""
    failure_id: str
    timestamp: datetime
    failure_type: FailureType
    severity: SeverityLevel
    genome_id: str
    failure_message: str
    error_details: Dict[str, Any]
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: Optional[str] = None
    resolution_timestamp: Optional[datetime] = None


@dataclass
class HealingStrategy:
    """Strategy for healing a specific failure type"""
    strategy_id: str
    failure_type: FailureType
    name: str
    description: str
    mutation_rules: List[Dict[str, Any]]
    success_probability: float
    confidence_score: float
    applicable_scenarios: List[str]


@dataclass
class HealingResult:
    """Result of a healing attempt"""
    healing_id: str
    original_genome: Genome
    healed_genome: Genome
    strategy: HealingStrategy
    success: bool
    improvement_score: float
    failure_details: FailureRecord
    applied_mutations: List[str]
    timestamp: datetime


class SelfHealingEvolutionEngine:
    """
    Self-healing evolution engine that learns from failures and
    automatically improves candidate architectures.
    """
    
    def __init__(self):
        self.failure_records: List[FailureRecord] = []
        self.healing_results: List[HealingResult] = []
        self.healing_strategies = self._initialize_healing_strategies()
        self.failure_patterns: Dict[str, int] = {}
        self.successful_healings: Dict[FailureType, int] = {}
        self.production_gate = ProductionReadinessGate(strict_mode=False)
        self.fitness_scorer = ProductionFitnessScorer()
        
    def _initialize_healing_strategies(self) -> List[HealingStrategy]:
        """Initialize healing strategies for different failure types"""
        strategies = [
            # Build Error Healing Strategies
            HealingStrategy(
                strategy_id="build_docker_fix",
                failure_type=FailureType.BUILD_ERROR,
                name="Docker Build Configuration Fix",
                description="Fix Docker build issues by adjusting service configurations",
                mutation_rules=[
                    {"type": "replace", "field": "database", "values": ["postgres", "mysql"]},
                    {"type": "add", "field": "health_endpoints", "value": True},
                    {"type": "add", "field": "metrics_endpoints", "value": True}
                ],
                success_probability=0.8,
                confidence_score=0.9,
                applicable_scenarios=["docker_build_failed", "service_startup_failed"]
            ),
            
            # Test Failure Healing Strategies
            HealingStrategy(
                strategy_id="test_coverage_boost",
                failure_type=FailureType.TEST_FAILURE,
                name="Test Coverage Improvement",
                description="Improve test coverage by adding missing test scenarios",
                mutation_rules=[
                    {"type": "add", "field": "health_endpoints", "value": True},
                    {"type": "add", "field": "metrics_endpoints", "value": True},
                    {"type": "add", "field": "tracing_enabled", "value": True},
                    {"type": "replace", "field": "logging_level", "values": ["INFO", "WARNING"]}
                ],
                success_probability=0.7,
                confidence_score=0.8,
                applicable_scenarios=["unit_tests_failed", "integration_tests_failed"]
            ),
            
            # Performance Issue Healing Strategies
            HealingStrategy(
                strategy_id="performance_optimization",
                failure_type=FailureType.PERFORMANCE_ISSUE,
                name="Performance Optimization",
                description="Optimize performance by adding caching and circuit breakers",
                mutation_rules=[
                    {"type": "add", "field": "cache_enabled", "value": True},
                    {"type": "add", "field": "circuit_breaker", "value": True},
                    {"type": "add", "field": "retry_policy", "value": {"max_attempts": 3}},
                    {"type": "replace", "field": "timeout_config", "values": [
                        {"connect_timeout": 10.0, "read_timeout": 30.0, "write_timeout": 30.0}
                    ]}
                ],
                success_probability=0.75,
                confidence_score=0.85,
                applicable_scenarios=["high_latency", "high_memory_usage", "cpu_spike"]
            ),
            
            # Security Violation Healing Strategies
            HealingStrategy(
                strategy_id="security_hardening",
                failure_type=FailureType.SECURITY_VIOLATION,
                name="Security Hardening",
                description="Improve security by adding security policies and hardening configurations",
                mutation_rules=[
                    {"type": "replace", "field": "auth", "values": ["jwt", "oauth2"]},
                    {"type": "add", "field": "rate_limiting", "value": True},
                    {"type": "add", "field": "security_policies", "value": [
                        {"type": "jwt_validation", "algorithm": "RS256"}
                    ]},
                    {"type": "add", "field": "circuit_breaker", "value": True}
                ],
                success_probability=0.9,
                confidence_score=0.95,
                applicable_scenarios=["auth_bypass", "rate_limit_exceeded", "data_leak"]
            ),
            
            # Dependency Conflict Healing Strategies
            HealingStrategy(
                strategy_id="dependency_resolution",
                failure_type=FailureType.DEPENDENCY_CONFLICT,
                name="Dependency Resolution",
                description="Resolve dependency conflicts by updating configurations",
                mutation_rules=[
                    {"type": "replace", "field": "database", "values": ["postgres"]},
                    {"type": "replace", "field": "backends", "values": [
                        {"type": "cache", "implementation": "redis"}
                    ]},
                    {"type": "add", "field": "circuit_breaker", "value": True},
                    {"type": "add", "field": "retry_policy", "value": {"max_attempts": 2}}
                ],
                success_probability=0.8,
                confidence_score=0.85,
                applicable_scenarios=["dependency_version_conflict", "service_unavailable"]
            ),
            
            # Configuration Error Healing Strategies
            HealingStrategy(
                strategy_id="configuration_standardization",
                failure_type=FailureType.CONFIGURATION_ERROR,
                name="Configuration Standardization",
                description="Standardize configuration across services",
                mutation_rules=[
                    {"type": "add", "field": "timeout_config", "value": {
                        "connect_timeout": 5.0,
                        "read_timeout": 30.0,
                        "write_timeout": 30.0,
                        "request_timeout": 60.0
                    }},
                    {"type": "add", "field": "retry_policy", "value": {
                        "max_attempts": 3,
                        "base_delay": 1.0,
                        "max_delay": 10.0
                    }},
                    {"type": "add", "field": "logging_level", "value": "INFO"}
                ],
                success_probability=0.85,
                confidence_score=0.9,
                applicable_scenarios=["configuration_parse_error", "invalid_parameter"]
            )
        ]
        
        return strategies
    
    def record_failure(self, genome: Genome, failure_type: FailureType, 
                      failure_message: str, error_details: Dict[str, Any],
                      stack_trace: Optional[str] = None,
                      context: Optional[Dict[str, Any]] = None) -> str:
        """
        Record a failure event for analysis and healing.
        
        Args:
            genome: The genome that failed
            failure_type: Type of failure
            failure_message: Description of the failure
            error_details: Detailed error information
            stack_trace: Stack trace if available
            context: Additional context information
            
        Returns:
            Failure ID for tracking
        """
        failure_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Determine severity based on failure type
        severity_map = {
            FailureType.BUILD_ERROR: SeverityLevel.HIGH,
            FailureType.TEST_FAILURE: SeverityLevel.MEDIUM,
            FailureType.DEPLOYMENT_ERROR: SeverityLevel.HIGH,
            FailureType.PERFORMANCE_ISSUE: SeverityLevel.MEDIUM,
            FailureType.SECURITY_VIOLATION: SeverityLevel.CRITICAL,
            FailureType.COMPLIANCE_FAILURE: SeverityLevel.CRITICAL,
            FailureType.DEPENDENCY_CONFLICT: SeverityLevel.HIGH,
            FailureType.CONFIGURATION_ERROR: SeverityLevel.MEDIUM
        }
        
        severity = severity_map.get(failure_type, SeverityLevel.MEDIUM)
        
        # Create failure record
        failure_record = FailureRecord(
            failure_id=failure_id,
            timestamp=timestamp,
            failure_type=failure_type,
            severity=severity,
            genome_id=genome.genome_id,
            failure_message=failure_message,
            error_details=error_details,
            stack_trace=stack_trace,
            context=context or {},
            resolved=False
        )
        
        self.failure_records.append(failure_record)
        
        # Update failure patterns
        pattern_key = f"{failure_type.value}_{failure_message}"
        self.failure_patterns[pattern_key] = self.failure_patterns.get(pattern_key, 0) + 1
        
        # Analyze failure and trigger healing
        self._analyze_and_heal(failure_record)
        
        return failure_id
    
    def _analyze_and_heal(self, failure_record: FailureRecord):
        """Analyze failure and attempt healing"""
        # Find appropriate healing strategies
        applicable_strategies = self._find_applicable_strategies(failure_record)
        
        if not applicable_strategies:
            return
        
        # Select best strategy based on success probability and confidence
        best_strategy = max(applicable_strategies, 
                          key=lambda s: s.success_probability * s.confidence_score)
        
        # Apply healing strategy
        original_genome = self._get_genome_by_id(failure_record.genome_id)
        if original_genome:
            healed_genome, applied_mutations = self._apply_healing_strategy(
                original_genome, best_strategy, failure_record
            )
            
            # Evaluate healing success
            success, improvement_score = self._evaluate_healing(
                original_genome, healed_genome, failure_record
            )
            
            # Record healing result
            healing_result = HealingResult(
                healing_id=str(uuid.uuid4()),
                original_genome=original_genome,
                healed_genome=healed_genome,
                strategy=best_strategy,
                success=success,
                improvement_score=improvement_score,
                failure_details=failure_record,
                applied_mutations=applied_mutations,
                timestamp=datetime.utcnow()
            )
            
            self.healing_results.append(healing_result)
            
            # Update statistics
            if success:
                self.successful_healings[best_strategy.failure_type] = \
                    self.successful_healings.get(best_strategy.failure_type, 0) + 1
                
                # Mark failure as resolved
                failure_record.resolved = True
                failure_record.resolution = f"Healed using {best_strategy.name}"
                failure_record.resolution_timestamp = datetime.utcnow()
    
    def _find_applicable_strategies(self, failure_record: FailureRecord) -> List[HealingStrategy]:
        """Find applicable healing strategies for a failure"""
        applicable_strategies = []
        
        # Filter by failure type
        matching_strategies = [
            strategy for strategy in self.healing_strategies
            if strategy.failure_type == failure_record.failure_type
        ]
        
        # Filter by context
        for strategy in matching_strategies:
            if self._is_strategy_applicable(strategy, failure_record):
                applicable_strategies.append(strategy)
                
        return applicable_strategies
    
    def _is_strategy_applicable(self, strategy: HealingStrategy, failure_record: FailureRecord) -> bool:
        """Check if a healing strategy is applicable to a failure"""
        # Check applicable scenarios
        context = failure_record.context
        
        for scenario in strategy.applicable_scenarios:
            if scenario in context.get("scenarios", []):
                return True
                
        # Default to applicable if no specific scenarios match
        return True
    
    def _get_genome_by_id(self, genome_id: str) -> Optional[Genome]:
        """Get genome by ID (simplified - in reality would load from storage)"""
        # This is a placeholder - in a real implementation, you'd load from storage
        return None
    
    def _apply_healing_strategy(self, genome: Genome, strategy: HealingStrategy, 
                              failure_record: FailureRecord) -> Tuple[Genome, List[str]]:
        """Apply a healing strategy to a genome"""
        healed_genome = Genome(genome.encode())  # Create a copy
        applied_mutations = []
        
        # Apply mutation rules
        for rule in strategy.mutation_rules:
            mutation_applied = self._apply_mutation_rule(healed_genome, rule)
            if mutation_applied:
                applied_mutations.append(f"{rule['type']}: {rule['field']}")
        
        return healed_genome, applied_mutations
    
    def _apply_mutation_rule(self, genome: Genome, rule: Dict[str, Any]) -> bool:
        """Apply a single mutation rule to a genome"""
        field = rule["field"]
        mutation_type = rule["type"]
        
        # Handle different mutation types
        if mutation_type == "add":
            value = rule["value"]
            if hasattr(genome, field):
                if field == "security_policies":
                    genome.security_policies.extend(value if isinstance(value, list) else [value])
                elif field == "backends":
                    genome.backends.extend(value if isinstance(value, list) else [value])
                else:
                    setattr(genome, field, value)
                return True
                
        elif mutation_type == "replace":
            values = rule["values"]
            if hasattr(genome, field):
                if isinstance(values, list):
                    # Choose random value from list
                    new_value = values[0]  # Simplified - could use weighted selection
                else:
                    new_value = values
                setattr(genome, field, new_value)
                return True
                
        elif mutation_type == "update":
            value = rule["value"]
            if hasattr(genome, field):
                current_value = getattr(genome, field)
                if isinstance(current_value, dict):
                    current_value.update(value)
                    setattr(genome, field, current_value)
                    return True
                    
        return False
    
    def _evaluate_healing(self, original_genome: Genome, healed_genome: Genome, 
                         failure_record: FailureRecord) -> Tuple[bool, float]:
        """Evaluate if healing was successful"""
        # Check if healed genome passes production gate
        evaluation = self.production_gate.evaluate_genome(healed_genome)
        
        success = evaluation.overall_result.value == "passed"
        
        # Calculate improvement score
        original_score = original_genome.get_production_score()
        healed_score = healed_genome.get_production_score()
        improvement_score = healed_score - original_score
        
        return success, improvement_score
    
    def get_failure_insights(self) -> Dict[str, Any]:
        """Get insights from failure patterns"""
        total_failures = len(self.failure_records)
        resolved_failures = len([f for f in self.failure_records if f.resolved])
        
        failure_by_type = {}
        for failure in self.failure_records:
            failure_type = failure.failure_type.value
            failure_by_type[failure_type] = failure_by_type.get(failure_type, 0) + 1
        
        success_rates = {}
        for failure_type, count in self.successful_healings.items():
            total_type_failures = failure_by_type.get(failure_type.value, 0)
            if total_type_failures > 0:
                success_rates[failure_type.value] = count / total_type_failures
        
        top_failure_patterns = sorted(
            self.failure_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_failures": total_failures,
            "resolved_failures": resolved_failures,
            "resolution_rate": resolved_failures / max(total_failures, 1),
            "failure_by_type": failure_by_type,
            "success_rates": success_rates,
            "top_failure_patterns": top_failure_patterns,
            "healing_strategies_count": len(self.healing_strategies)
        }
    
    def get_healing_statistics(self) -> Dict[str, Any]:
        """Get healing statistics"""
        total_healings = len(self.healing_results)
        successful_healings = len([h for h in self.healing_results if h.success])
        
        healing_by_type = {}
        for result in self.healing_results:
            failure_type = result.strategy.failure_type.value
            healing_by_type[failure_type] = healing_by_type.get(failure_type, 0) + 1
        
        avg_improvement = sum(h.improvement_score for h in self.healing_results) / max(total_healings, 1)
        
        return {
            "total_healings": total_healings,
            "successful_healings": successful_healings,
            "success_rate": successful_healings / max(total_healings, 1),
            "healing_by_type": healing_by_type,
            "avg_improvement_score": avg_improvement,
            "strategies_used": len(set(h.strategy.strategy_id for h in self.healing_results))
        }
    
    def predict_failures(self, genome: Genome) -> List[Dict[str, Any]]:
        """Predict potential failures for a genome"""
        predictions = []
        
        # Analyze genome for potential failure points
        if genome.auth == "basic" and len(genome.services) > 3:
            predictions.append({
                "failure_type": FailureType.SECURITY_VIOLATION,
                "probability": 0.8,
                "severity": SeverityLevel.HIGH,
                "prediction": "Basic auth vulnerable in multi-service architecture",
                "recommendation": "Use JWT or OAuth2 for better security"
            })
        
        if not genome.rate_limiting and len(genome.services) > 2:
            predictions.append({
                "failure_type": FailureType.PERFORMANCE_ISSUE,
                "probability": 0.6,
                "severity": SeverityLevel.MEDIUM,
                "prediction": "No rate limiting may cause performance issues",
                "recommendation": "Implement rate limiting to prevent abuse"
            })
        
        if genome.database == "sqlite" and len(genome.services) > 2:
            predictions.append({
                "failure_type": FailureType.DEPLOYMENT_ERROR,
                "probability": 0.7,
                "severity": SeverityLevel.HIGH,
                "prediction": "SQLite not suitable for multi-service production",
                "recommendation": "Use PostgreSQL or MySQL for production"
            })
        
        if not genome.health_endpoints:
            predictions.append({
                "failure_type": FailureType.CONFIGURATION_ERROR,
                "probability": 0.5,
                "severity": SeverityLevel.LOW,
                "prediction": "Missing health endpoints",
                "recommendation": "Add health check endpoints"
            })
        
        return predictions
    
    def add_custom_healing_strategy(self, strategy: HealingStrategy):
        """Add a custom healing strategy"""
        self.healing_strategies.append(strategy)
    
    def get_healing_strategies(self) -> List[HealingStrategy]:
        """Get all available healing strategies"""
        return self.healing_strategies.copy()
    
    def get_failure_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failure history"""
        recent_failures = sorted(
            self.failure_records,
            key=lambda f: f.timestamp,
            reverse=True
        )[:limit]
        
        return [
            {
                "failure_id": f.failure_id,
                "timestamp": f.timestamp.isoformat(),
                "failure_type": f.failure_type.value,
                "severity": f.severity.value,
                "message": f.failure_message,
                "resolved": f.resolved,
                "genome_id": f.genome_id
            }
            for f in recent_failures
        ]
    
    def get_healing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get healing history"""
        recent_healings = sorted(
            self.healing_results,
            key=lambda h: h.timestamp,
            reverse=True
        )[:limit]
        
        return [
            {
                "healing_id": h.healing_id,
                "timestamp": h.timestamp.isoformat(),
                "failure_type": h.strategy.failure_type.value,
                "success": h.success,
                "improvement_score": h.improvement_score,
                "original_score": h.original_genome.get_production_score(),
                "healed_score": h.healed_genome.get_production_score(),
                "applied_mutations": h.applied_mutations
            }
            for h in recent_healings
        ]
    
    def export_failure_data(self, file_path: str):
        """Export failure data for analysis"""
        data = {
            "failures": [
                {
                    "failure_id": f.failure_id,
                    "timestamp": f.timestamp.isoformat(),
                    "failure_type": f.failure_type.value,
                    "severity": f.severity.value,
                    "genome_id": f.genome_id,
                    "failure_message": f.failure_message,
                    "error_details": f.error_details,
                    "context": f.context,
                    "resolved": f.resolved,
                    "resolution": f.resolution,
                    "resolution_timestamp": f.resolution_timestamp.isoformat() if f.resolution_timestamp else None
                }
                for f in self.failure_records
            ],
            "healings": [
                {
                    "healing_id": h.healing_id,
                    "timestamp": h.timestamp.isoformat(),
                    "failure_type": h.strategy.failure_type.value,
                    "success": h.success,
                    "improvement_score": h.improvement_score,
                    "original_genome": h.original_genome.encode(),
                    "healed_genome": h.healed_genome.encode(),
                    "applied_mutations": h.applied_mutations
                }
                for h in self.healing_results
            ],
            "insights": self.get_failure_insights(),
            "statistics": self.get_healing_statistics()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def clear_old_failures(self, days: int = 30):
        """Clear failure records older than specified days"""
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        self.failure_records = [
            f for f in self.failure_records
            if f.timestamp >= cutoff_date
        ]
        
        # Also clear corresponding healing results
        self.healing_results = [
            h for h in self.healing_results
            if h.failure_details.timestamp >= cutoff_date
        ]