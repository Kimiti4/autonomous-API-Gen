"""
Production readiness analysis for evolved API architectures.

This turns production constraints into a first-class scoring signal so the
evolution engine can optimize for deployability, not just feature richness.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from app.engine.genome import Genome
from app.engine.security import calculate_security_score


@dataclass(frozen=True)
class ReadinessDimension:
    """One weighted production readiness dimension."""

    name: str
    score: float
    weight: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "weight": self.weight,
            "weighted_score": round(self.score * self.weight, 3),
            "summary": self.summary,
        }


class ProductionReadinessAnalyzer:
    """Scores evolved genomes against production deployment expectations."""

    def analyze(
        self,
        genome: Genome | Dict[str, Any],
        deployment_target: str = "docker_compose",
    ) -> Dict[str, Any]:
        candidate = genome if isinstance(genome, Genome) else Genome(genome_data=genome)

        blockers = self._find_blockers(candidate, deployment_target)
        warnings = self._find_warnings(candidate, deployment_target)
        dimensions = self._score_dimensions(candidate, deployment_target)
        weighted_total = sum(item.score * item.weight for item in dimensions)
        score = round(max(0.0, min(1.0, weighted_total)), 3)
        status = self._status(score, blockers)

        return {
            "status": status,
            "score": score,
            "deployment_target": deployment_target,
            "blockers": blockers,
            "warnings": warnings,
            "dimensions": [item.to_dict() for item in dimensions],
            "risk_register": self._risk_register(candidate, deployment_target),
            "recommendations": self._recommendations(candidate, blockers, warnings),
            "required_capabilities": self._required_capabilities(candidate, deployment_target),
        }

    def _score_dimensions(
        self,
        genome: Genome,
        deployment_target: str,
    ) -> List[ReadinessDimension]:
        security_score = calculate_security_score(genome)
        persistence_score = self._persistence_score(genome)
        operations_score = self._operations_score(genome, deployment_target)
        scalability_score = self._scalability_score(genome)
        compliance_score = self._compliance_score(genome)

        return [
            ReadinessDimension(
                "security",
                security_score,
                0.30,
                "Authentication strength, critical-service protection, CORS, and rate limiting.",
            ),
            ReadinessDimension(
                "persistence",
                persistence_score,
                0.20,
                "Database suitability and durability for the selected deployment target.",
            ),
            ReadinessDimension(
                "operations",
                operations_score,
                0.20,
                "Health checks, logging posture, metrics readiness, and runtime operability.",
            ),
            ReadinessDimension(
                "scalability",
                scalability_score,
                0.15,
                "Cache usage, service count, and ability to handle concurrent production load.",
            ),
            ReadinessDimension(
                "compliance",
                compliance_score,
                0.15,
                "Auditability and sensitivity controls for risky service domains.",
            ),
        ]

    def _find_blockers(self, genome: Genome, deployment_target: str) -> List[str]:
        blockers = []
        critical_services = {"admin", "payments", "users"}

        if genome.auth == "basic":
            blockers.append("Basic authentication is not acceptable for production APIs.")

        if critical_services.intersection(genome.services) and genome.auth in {"basic", "api_key"}:
            blockers.append(
                "Critical services require JWT or OAuth2 authentication before production rollout."
            )

        if deployment_target in {"kubernetes", "ecs", "enterprise"} and genome.database == "sqlite":
            blockers.append(
                f"SQLite is not suitable for the {deployment_target} deployment target."
            )

        if "payments" in genome.services and not genome.rate_limiting:
            blockers.append("Payment APIs must enable rate limiting before production.")

        return blockers

    def _find_warnings(self, genome: Genome, deployment_target: str) -> List[str]:
        warnings = []

        if genome.database == "sqlite":
            warnings.append("SQLite is acceptable for local prototypes but limits production concurrency.")

        if not genome.cache_enabled and len(genome.services) >= 4:
            warnings.append("Large service sets should enable caching or document why it is unnecessary.")

        if not genome.rate_limiting:
            warnings.append("Rate limiting is disabled, increasing abuse and cost risk.")

        if genome.cors_enabled:
            warnings.append("CORS must be restricted to explicit production origins at deploy time.")

        if genome.logging_level == "DEBUG":
            warnings.append("DEBUG logging can leak details and increase production cost.")

        if deployment_target == "docker_compose" and len(genome.services) > 4:
            warnings.append("Docker Compose may become hard to operate for this service count.")

        return warnings

    def _persistence_score(self, genome: Genome) -> float:
        scores = {
            "postgres": 1.0,
            "mysql": 0.9,
            "sqlite": 0.45,
        }
        return scores.get(genome.database, 0.4)

    def _operations_score(self, genome: Genome, deployment_target: str) -> float:
        score = 0.55

        if genome.logging_level in {"INFO", "WARNING"}:
            score += 0.20
        elif genome.logging_level == "ERROR":
            score += 0.10

        if genome.rate_limiting:
            score += 0.10

        if deployment_target in {"kubernetes", "ecs", "enterprise"}:
            score += 0.10

        if genome.auth in {"jwt", "oauth2"}:
            score += 0.05

        return min(score, 1.0)

    def _scalability_score(self, genome: Genome) -> float:
        score = 0.45

        if genome.cache_enabled:
            score += 0.25

        if genome.database in {"postgres", "mysql"}:
            score += 0.20

        if 2 <= len(genome.services) <= 5:
            score += 0.10

        return min(score, 1.0)

    def _compliance_score(self, genome: Genome) -> float:
        score = 0.75
        sensitive_services = {"payments", "users", "admin", "files"}

        if sensitive_services.intersection(genome.services):
            score -= 0.15

        if genome.auth in {"jwt", "oauth2"}:
            score += 0.15

        if genome.rate_limiting:
            score += 0.10

        if genome.logging_level == "DEBUG":
            score -= 0.15

        return max(0.0, min(score, 1.0))

    def _risk_register(self, genome: Genome, deployment_target: str) -> List[Dict[str, str]]:
        risks = []

        if genome.database == "sqlite":
            risks.append(
                {
                    "risk": "Database write contention",
                    "severity": "high" if deployment_target != "local" else "medium",
                    "mitigation": "Use Postgres or MySQL with migrations and managed backups.",
                }
            )

        if genome.auth in {"basic", "api_key"}:
            risks.append(
                {
                    "risk": "Weak authentication boundary",
                    "severity": "high",
                    "mitigation": "Use OAuth2 or JWT with key rotation and scoped permissions.",
                }
            )

        if not genome.rate_limiting:
            risks.append(
                {
                    "risk": "Abuse and runaway cost",
                    "severity": "medium",
                    "mitigation": "Enable rate limiting and back it with Redis in scaled deployments.",
                }
            )

        if "payments" in genome.services:
            risks.append(
                {
                    "risk": "Payment workflow compliance",
                    "severity": "high",
                    "mitigation": "Add audit logs, idempotency keys, webhook verification, and PCI review.",
                }
            )

        if genome.cors_enabled:
            risks.append(
                {
                    "risk": "Over-broad browser access",
                    "severity": "medium",
                    "mitigation": "Restrict CORS to approved frontend origins per environment.",
                }
            )

        return risks

    def _recommendations(
        self,
        genome: Genome,
        blockers: List[str],
        warnings: List[str],
    ) -> List[str]:
        recommendations = []

        if blockers:
            recommendations.append("Resolve all blockers before allowing this genome through the production gate.")

        if genome.database == "sqlite":
            recommendations.append("Promote persistence to Postgres and add schema migrations.")

        if genome.auth in {"basic", "api_key"}:
            recommendations.append("Switch authentication to OAuth2 or JWT for production candidates.")

        if not genome.rate_limiting:
            recommendations.append("Enable rate limiting and include limit headers in generated APIs.")

        if not genome.cache_enabled and len(genome.services) >= 4:
            recommendations.append("Enable caching for read-heavy services or lower the scalability score.")

        if warnings:
            recommendations.append("Convert warnings into explicit deployment checklist items.")

        return recommendations

    def _required_capabilities(
        self,
        genome: Genome,
        deployment_target: str,
    ) -> List[str]:
        capabilities = [
            "health_check",
            "structured_logging",
            "openapi_contract",
            "smoke_tests",
        ]

        if genome.rate_limiting:
            capabilities.append("rate_limit_policy")

        if genome.cache_enabled:
            capabilities.append("cache_backend")

        if genome.database in {"postgres", "mysql"}:
            capabilities.extend(["database_migrations", "managed_backups"])

        if deployment_target in {"kubernetes", "ecs", "enterprise"}:
            capabilities.extend(["readiness_probe", "metrics_export", "secret_management"])

        return capabilities

    def _status(self, score: float, blockers: List[str]) -> str:
        if blockers:
            return "blocked"
        if score >= 0.85:
            return "ready"
        if score >= 0.70:
            return "needs_review"
        return "not_ready"
