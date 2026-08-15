"""
Capability Resolution — Maps abstract architectural capabilities to
backend-specific implementations.

The ISR declares capabilities, not implementations. The Capability
Resolver maps these to backend-specific implementations. The backend
never hardcodes architectural meaning — it maps required capabilities
to implementation-specific components.

This is a critical abstraction boundary: if we replace FastAPI with
Phoenix, only the capability-to-implementation mapping changes,
not the ISR or the evolution engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable


class Capability(Enum):
    """Abstract capabilities that can be declared in the ISR."""
    # Authentication
    OAUTH2 = "oauth2"
    JWT_AUTH = "jwt_auth"
    API_KEY_AUTH = "api_key_auth"
    MUTUAL_TLS = "mutual_tls"

    # Persistence
    SQL_RELATIONAL = "sql_relational"
    DOCUMENT_DB = "document_db"
    GRAPH_DB = "graph_db"
    KEY_VALUE = "key_value"
    CACHE = "cache"

    # API
    REST_API = "rest_api"
    GRAPHQL_API = "graphql_api"
    GRPC_API = "grpc_api"
    ASYNC_API = "async_api"

    # Messaging
    EVENT_BUS = "event_bus"
    MESSAGE_QUEUE = "message_queue"
    STREAM_PROCESSING = "stream_processing"

    # Observability
    STRUCTURED_LOGGING = "structured_logging"
    METRICS = "metrics"
    DISTRIBUTED_TRACING = "distributed_tracing"
    HEALTH_CHECKS = "health_checks"

    # Security
    INPUT_VALIDATION = "input_validation"
    RATE_LIMITING = "rate_limiting"
    CORS = "cors"
    ENCRYPTION = "encryption"

    # Data
    ORM = "orm"
    MIGRATIONS = "migrations"
    VALIDATION = "validation"
    SERIALIZATION = "serialization"

    # Infrastructure
    CONTAINERIZATION = "containerization"
    CI_CD = "ci_cd"
    SECRETS_MANAGEMENT = "secrets_management"


@dataclass(frozen=True)
class BackendCapabilities:
    """The capabilities supported by a specific backend."""
    name: str
    supported: Set[Capability]
    unsupported: Set[Capability] = field(default_factory=set)


@dataclass(frozen=True)
class CapabilityMap:
    """Maps abstract capabilities to backend-specific implementations.

    For example:
      Capability.OAUTH2 → {"library": "authlib", "package": "authlib"}
      Capability.ORM → {"library": "sqlalchemy", "package": "sqlalchemy"}
    """
    backend_name: str
    mappings: Dict[Capability, Dict[str, str]] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)


class CapabilityResolver:
    """Resolves abstract ISR capabilities to backend-specific implementations.

    The ISR declares what it needs (e.g., OAuth2 authentication).
    The resolver determines which libraries, frameworks, and patterns
    satisfy that need for the target backend.
    """

    # Default capability maps per backend family
    _CAPABILITY_MAPS: Dict[str, CapabilityMap] = {}

    @classmethod
    def register_backend(cls, name: str, capability_map: CapabilityMap):
        """Register a backend's capability map."""
        cls._CAPABILITY_MAPS[name] = capability_map

    @classmethod
    def get_backend(cls, name: str) -> Optional[CapabilityMap]:
        """Get a backend's capability map."""
        return cls._CAPABILITY_MAPS.get(name)

    @classmethod
    def resolve(cls, backend_name: str, capabilities: Set[Capability]) -> CapabilityMap:
        """Resolve capabilities for a specific backend.

        Args:
            backend_name: The target backend (e.g., "fastapi", "phoenix")
            capabilities: The set of required capabilities from the ISR

        Returns:
            A CapabilityMap with backend-specific implementation details

        Raises:
            ValueError: If a capability is not supported by the backend
        """
        backend_map = cls._CAPABILITY_MAPS.get(backend_name)
        if not backend_map:
            raise ValueError(f"Unknown backend: {backend_name}")

        resolved = {}
        for cap in capabilities:
            if cap in backend_map.mappings:
                resolved[cap] = backend_map.mappings[cap]
            else:
                # Use sensible defaults
                resolved[cap] = {"status": "manual", "note": f"No automatic mapping for {cap.value}"}

        return CapabilityMap(
            backend_name=backend_name,
            mappings=resolved,
            defaults=backend_map.defaults,
        )

    @classmethod
    def get_unsupported(cls, backend_name: str, capabilities: Set[Capability]) -> Set[Capability]:
        """Get capabilities not supported by a backend."""
        backend_map = cls._CAPABILITY_MAPS.get(backend_name)
        if not backend_map:
            return capabilities
        return {c for c in capabilities if c not in backend_map.mappings}


# Register the FastAPI capability map
def _register_fastapi():
    """Register the FastAPI capability map."""
    fastapi_map = CapabilityMap(
        backend_name="fastapi",
        mappings={
            Capability.OAUTH2: {"library": "authlib", "package": "authlib", "integration": "fastapi-security"},
            Capability.JWT_AUTH: {"library": "python-jose", "package": "python-jose[cryptography]", "integration": "fastapi-security"},
            Capability.API_KEY_AUTH: {"library": "fastapi-security", "package": "fastapi-security"},
            Capability.SQL_RELATIONAL: {"library": "sqlalchemy", "package": "sqlalchemy", "async_support": "sqlalchemy[asyncio]"},
            Capability.DOCUMENT_DB: {"library": "motor", "package": "motor", "driver": "pymongo"},
            Capability.CACHE: {"library": "redis", "package": "redis", "integration": "fastapi-cache"},
            Capability.REST_API: {"library": "fastapi", "package": "fastapi", "server": "uvicorn"},
            Capability.EVENT_BUS: {"library": "redis", "package": "redis", "pattern": "pub-sub"},
            Capability.MESSAGE_QUEUE: {"library": "aio-pika", "package": "aio-pika", "protocol": "AMQP"},
            Capability.STRUCTURED_LOGGING: {"library": "loguru", "package": "loguru"},
            Capability.METRICS: {"library": "prometheus-fastapi-instrumentator", "package": "prometheus-fastapi-instrumentator"},
            Capability.DISTRIBUTED_TRACING: {"library": "opentelemetry", "package": "opentelemetry-api"},
            Capability.HEALTH_CHECKS: {"library": "fastapi", "package": "fastapi", "pattern": "built-in"},
            Capability.INPUT_VALIDATION: {"library": "pydantic", "package": "pydantic"},
            Capability.RATE_LIMITING: {"library": "slowapi", "package": "slowapi"},
            Capability.CORS: {"library": "fastapi", "package": "fastapi", "middleware": "CORSMiddleware"},
            Capability.ENCRYPTION: {"library": "cryptography", "package": "cryptography"},
            Capability.ORM: {"library": "sqlalchemy", "package": "sqlalchemy", "pattern": "repository"},
            Capability.MIGRATIONS: {"library": "alembic", "package": "alembic"},
            Capability.VALIDATION: {"library": "pydantic", "package": "pydantic"},
            Capability.SERIALIZATION: {"library": "pydantic", "package": "pydantic"},
            Capability.CONTAINERIZATION: {"tool": "docker", "file": "Dockerfile"},
            Capability.CI_CD: {"tool": "github-actions", "file": ".github/workflows"},
            Capability.SECRETS_MANAGEMENT: {"tool": "python-dotenv", "package": "python-dotenv"},
        },
        defaults={
            "python_version": ">=3.11",
            "server": "uvicorn",
            "port": 8000,
            "framework_version": ">=0.100.0",
        },
    )
    CapabilityResolver.register_backend("fastapi", fastapi_map)


# Register Phoenix capability map
def _register_phoenix():
    """Register the Phoenix (Elixir) capability map."""
    phoenix_map = CapabilityMap(
        backend_name="phoenix",
        mappings={
            Capability.OAUTH2: {"library": "ueberauth", "package": "ueberauth", "strategies": "ueberauth_google"},
            Capability.JWT_AUTH: {"library": "guardian", "package": "guardian"},
            Capability.SQL_RELATIONAL: {"library": "ecto", "package": "ecto_sql", "adapter": "postgres"},
            Capability.REST_API: {"library": "phoenix", "package": "phoenix", "server": "bandit"},
            Capability.EVENT_BUS: {"library": "phoenix-pubsub", "package": "phoenix_pubsub", "adapter": "redis"},
            Capability.MESSAGE_QUEUE: {"library": "broadway", "package": "broadway", "adapter": "broadway_rabbitmq"},
            Capability.STRUCTURED_LOGGING: {"library": "logger", "package": "built-in"},
            Capability.METRICS: {"library": "telemetry", "package": "telemetry", "exporter": "telemetry_metrics_prometheus"},
            Capability.HEALTH_CHECKS: {"library": "phoenix", "package": "phoenix", "pattern": "built-in"},
            Capability.INPUT_VALIDATION: {"library": "changesets", "package": "ecto"},
            Capability.CORS: {"library": "corsica", "package": "corsica"},
            Capability.ORM: {"library": "ecto", "package": "ecto", "pattern": "repository"},
            Capability.MIGRATIONS: {"library": "ecto", "package": "ecto_sql", "pattern": "mix"},
            Capability.VALIDATION: {"library": "changesets", "package": "ecto"},
            Capability.SERIALIZATION: {"library": "jason", "package": "jason"},
            Capability.CONTAINERIZATION: {"tool": "docker", "file": "Dockerfile"},
        },
        defaults={
            "elixir_version": ">=1.15",
            "server": "bandit",
            "port": 4000,
        },
    )
    CapabilityResolver.register_backend("phoenix", phoenix_map)


# Register Spring Boot capability map
def _register_spring_boot():
    """Register the Spring Boot (Java) capability map."""
    spring_map = CapabilityMap(
        backend_name="spring-boot",
        mappings={
            Capability.OAUTH2: {"library": "spring-security-oauth2", "package": "org.springframework.boot:spring-boot-starter-oauth2"},
            Capability.JWT_AUTH: {"library": "spring-security", "package": "org.springframework.boot:spring-boot-starter-security"},
            Capability.SQL_RELATIONAL: {"library": "spring-data-jpa", "package": "org.springframework.boot:spring-boot-starter-data-jpa"},
            Capability.REST_API: {"library": "spring-web", "package": "org.springframework.boot:spring-boot-starter-web"},
            Capability.EVENT_BUS: {"library": "spring-events", "package": "org.springframework.boot:spring-boot-starter"},
            Capability.MESSAGE_QUEUE: {"library": "spring-kafka", "package": "org.springframework.kafka:spring-kafka"},
            Capability.STRUCTURED_LOGGING: {"library": "logback", "package": "ch.qos.logback:logback-classic"},
            Capability.METRICS: {"library": "micrometer", "package": "io.micrometer:micrometer-registry-prometheus"},
            Capability.DISTRIBUTED_TRACING: {"library": "spring-cloud-sleuth", "package": "org.springframework.cloud:spring-cloud-starter-sleuth"},
            Capability.HEALTH_CHECKS: {"library": "spring-actuator", "package": "org.springframework.boot:spring-boot-starter-actuator"},
            Capability.INPUT_VALIDATION: {"library": "jakarta-validation", "package": "org.springframework.boot:spring-boot-starter-validation"},
            Capability.CORS: {"library": "spring-web", "package": "org.springframework.boot:spring-boot-starter-web"},
            Capability.ORM: {"library": "spring-data-jpa", "package": "org.springframework.boot:spring-boot-starter-data-jpa"},
            Capability.MIGRATIONS: {"library": "flyway", "package": "org.flywaydb:flyway-core"},
            Capability.VALIDATION: {"library": "jakarta-validation", "package": "org.springframework.boot:spring-boot-starter-validation"},
            Capability.SERIALIZATION: {"library": "jackson", "package": "com.fasterxml.jackson.core:jackson-databind"},
            Capability.CONTAINERIZATION: {"tool": "docker", "file": "Dockerfile"},
        },
        defaults={
            "java_version": ">=17",
            "server": "tomcat",
            "port": 8080,
            "framework_version": ">=3.0.0",
        },
    )
    CapabilityResolver.register_backend("spring-boot", spring_map)


# Register all default backend capability maps
_register_fastapi()
_register_phoenix()
_register_spring_boot()