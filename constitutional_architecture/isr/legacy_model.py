"""
ISR Meta-Model — The typed, directed, attributed graph specification.

This defines all node types, edge types, cardinalities, and invariants
that constitute the Intermediate Software Representation.

Per the Constitution:
- The ISR is the sole architectural source of truth.
- It is immutable; mutations produce new versions.
- No framework, language, or deployment technology shall become part of
  the platform's core reasoning model.
"""

from __future__ import annotations

import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class NodeType(Enum):
    """All valid ISR node types."""
    SYSTEM = "system"
    MODULE = "module"
    ENTITY = "entity"
    SERVICE = "service"
    WORKFLOW = "workflow"
    POLICY = "policy"
    INTERFACE = "interface"
    EVENT = "event"
    DEPLOYMENT = "deployment"
    CONSTRAINT = "constraint"


class EdgeType(Enum):
    """All valid ISR edge types and their semantics.

    Every edge carries semantic meaning about the relationship between
    two architectural elements.
    """
    OWNS = "owns"                    # Containment / responsibility
    DEPENDS_ON = "depends-on"        # Runtime or build dependency
    EMITS = "emits"                  # Produces an event
    CONSUMES = "consumes"            # Subscribes to an event
    REFERENCES = "references"        # Data relationship
    IMPLEMENTS = "implements"        # Realises an interface
    SECURED_BY = "secured-by"       # Protected by a policy
    DEPLOYS_TO = "deploys-to"       # Infrastructure binding
    ORCHESTRATES = "orchestrates"    # Workflow coordination
    CONSTRAINS = "constrains"        # Applies a rule


class Cardinality(Enum):
    """Cardinality constraints on edges."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_MANY = "M:N"


class CompletenessLevel(Enum):
    """Incremental specification levels for the ISR."""
    L0_SKELETON = 0       # System name, module names only
    L1_STRUCTURAL = 1     # Modules, entities, relationships
    L2_BEHAVIOURAL = 2    # Services, operations, events, workflows
    L3_POLICY = 3         # Security, governance, operational policies
    L4_INFRASTRUCTURE = 4 # Deployment, scaling, networking
    L5_COMPLETE = 5       # All layers specified


class Severity(Enum):
    """Validation result severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ──────────────────────────────────────────────
# Core Attribute Types
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Field:
    """A field/property on an Entity."""
    name: str
    field_type: str
    required: bool = True
    unique: bool = False
    indexed: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Operation:
    """An operation/method on a Service."""
    name: str
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: Optional[str] = None
    description: Optional[str] = None
    is_query: bool = False  # True = read-only, False = command
    event_triggers: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class State:
    """A state in a workflow state machine."""
    name: str
    description: Optional[str] = None
    is_initial: bool = False
    is_terminal: bool = False
    is_error: bool = False


@dataclass(frozen=True)
class Transition:
    """A transition between workflow states."""
    from_state: str
    to_state: str
    action: str
    guard_condition: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class Action:
    """An action performed during a workflow transition."""
    name: str
    service: Optional[str] = None
    operation: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class Rule:
    """A policy rule."""
    name: str
    description: str
    effect: str  # "allow" | "deny" | "audit"
    resource_pattern: Optional[str] = None
    condition: Optional[str] = None


@dataclass(frozen=True)
class Permission:
    """A permission definition."""
    resource: str
    action: str  # "create" | "read" | "update" | "delete" | "execute"
    roles: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Endpoint:
    """An API endpoint on an Interface."""
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    operation: Optional[str] = None
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    description: Optional[str] = None
    rate_limit: Optional[str] = None
    timeout_ms: Optional[int] = None


@dataclass(frozen=True)
class Contract:
    """A contract definition (request/response schema)."""
    name: str
    schema_type: str  # "object" | "array" | "enum" etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass(frozen=True)
class SecurityBinding:
    """Security binding for an Interface."""
    policy_name: str
    auth_strategy: Optional[str] = None  # "oauth2" | "jwt" | "mtls" | "api_key"
    scopes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Relationship:
    """A data relationship between entities."""
    target_entity: str
    target_module: Optional[str] = None
    type: str = "reference"  # "reference" | "composition" | "aggregation"
    cardinality: Cardinality = Cardinality.ONE_TO_MANY
    foreign_key_field: Optional[str] = None
    inverse_field: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class Dependency:
    """A dependency on another service."""
    target_service: str
    target_module: Optional[str] = None
    coupling_strength: str = "loose"  # "tight" | "loose"
    sync_or_async: str = "sync"       # "sync" | "async"
    criticality: str = "normal"       # "critical" | "normal" | "low"
    latency_budget_ms: Optional[int] = None
    circuit_breaker: bool = False
    retry_policy: Optional[str] = None


@dataclass(frozen=True)
class Scaling:
    """Scaling configuration."""
    min_instances: int = 1
    max_instances: int = 3
    target_cpu_utilization: float = 0.7
    target_memory_utilization: float = 0.8
    scaling_policy: str = "horizontal"  # "horizontal" | "vertical"
    cooldown_seconds: int = 60


@dataclass(frozen=True)
class Networking:
    """Networking configuration."""
    dns_name: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    ingress_type: str = "load_balancer"  # "load_balancer" | "ingress" | "none"
    tls_enabled: bool = True
    network_policy: Optional[str] = None
    allowed_cidrs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Storage:
    """Storage configuration."""
    type: str = "persistent"  # "persistent" | "ephemeral" | "object"
    size_gb: int = 10
    performance_tier: str = "standard"  # "standard" | "premium"
    backup_enabled: bool = True
    encryption_at_rest: bool = True


@dataclass(frozen=True)
class Secrets:
    """Secrets management configuration."""
    provider: str = "environment"  # "environment" | "vault" | "aws_secrets" | "gcp_secrets"
    secret_names: List[str] = field(default_factory=list)
    rotation_days: int = 90


@dataclass(frozen=True)
class Monitoring:
    """Monitoring and observability configuration."""
    metrics_enabled: bool = True
    logging_enabled: bool = True
    tracing_enabled: bool = True
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    metrics_port: int = 9090
    alert_endpoints: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Metadata:
    """ISR metadata — versioning, lineage, provenance."""
    version: int
    parent_hash: Optional[str] = None
    lineage: List[str] = field(default_factory=list)
    fitness_annotations: Dict[str, float] = field(default_factory=dict)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    provenance: List[str] = field(default_factory=list)
    owner_agent: Optional[str] = None


# ──────────────────────────────────────────────
# ISR Node Types
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Entity:
    """Domain object with fields, constraints, and relationships."""
    name: str
    fields: List[Field] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    description: Optional[str] = None
    is_aggregate_root: bool = False
    id_field: str = "id"
    node_type: NodeType = NodeType.ENTITY

    def __post_init__(self):
        # Validate that every entity has a unique identifier field
        id_fields = [f for f in self.fields if f.name == self.id_field]
        if not id_fields and self.id_field:
            object.__setattr__(self, 'fields',
                               [Field(name=self.id_field, field_type="uuid", required=True, unique=True)] + list(self.fields))


@dataclass(frozen=True)
class Service:
    """Operational unit with operations, dependencies, and events."""
    name: str
    operations: List[Operation] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    events: List[str] = field(default_factory=list)  # event names
    consumes: List[str] = field(default_factory=list)  # event names
    description: Optional[str] = None
    node_type: NodeType = NodeType.SERVICE


@dataclass(frozen=True)
class Workflow:
    """State machine with states, transitions, and actions."""
    name: str
    states: List[State] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    description: Optional[str] = None
    node_type: NodeType = NodeType.WORKFLOW

    def __post_init__(self):
        # Validate reachability: all states must be reachable from initial
        initial_states = [s for s in self.states if s.is_initial]
        if not initial_states:
            object.__setattr__(self, 'states',
                               [State(name="initial", is_initial=True)] + list(self.states))


@dataclass(frozen=True)
class Policy:
    """Security, governance, or operational rule set."""
    name: str
    strategy: Optional[str] = None  # "oauth2" | "jwt" | "rbac" | "opa" etc.
    rules: List[Rule] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    description: Optional[str] = None
    node_type: NodeType = NodeType.POLICY


@dataclass(frozen=True)
class Interface:
    """API contract (REST, gRPC, GraphQL, event subscription)."""
    name: str
    interface_type: str = "REST"  # "REST" | "gRPC" | "GraphQL" | "asyncapi"
    endpoints: List[Endpoint] = field(default_factory=list)
    contracts: List[Contract] = field(default_factory=list)
    security_bindings: List[SecurityBinding] = field(default_factory=list)
    internal: bool = False
    version: str = "1.0.0"
    description: Optional[str] = None
    node_type: NodeType = NodeType.INTERFACE


@dataclass(frozen=True)
class Event:
    """Domain event with schema and routing."""
    name: str
    schema_type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    routing_key: Optional[str] = None
    delivery_mode: str = "at_least_once"  # "at_most_once" | "at_least_once" | "exactly_once"
    retention_days: int = 7
    description: Optional[str] = None
    node_type: NodeType = NodeType.EVENT


@dataclass(frozen=True)
class Deployment:
    """Infrastructure, scaling, networking, and monitoring."""
    name: str = "default"
    scaling: Scaling = field(default_factory=Scaling)
    networking: Networking = field(default_factory=Networking)
    storage: Storage = field(default_factory=Storage)
    secrets: Secrets = field(default_factory=Secrets)
    monitoring: Monitoring = field(default_factory=Monitoring)
    description: Optional[str] = None
    node_type: NodeType = NodeType.DEPLOYMENT


@dataclass(frozen=True)
class Constraint:
    """Hard architectural rule or boundary."""
    name: str
    description: str
    constraint_type: str = "architectural"  # "architectural" | "regulatory" | "technical"
    severity: Severity = Severity.ERROR
    affected_nodes: List[str] = field(default_factory=list)
    rule_expression: Optional[str] = None
    node_type: NodeType = NodeType.CONSTRAINT


@dataclass(frozen=True)
class Module:
    """Bounded context owning entities, services, and interfaces."""
    name: str
    entities: List[Entity] = field(default_factory=list)
    services: List[Service] = field(default_factory=list)
    workflows: List[Workflow] = field(default_factory=list)
    policies: List[Policy] = field(default_factory=list)
    interfaces: List[Interface] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    deployment: Optional[Deployment] = None
    description: Optional[str] = None
    node_type: NodeType = NodeType.MODULE


@dataclass(frozen=True)
class System:
    """Root container — the complete software system.

    This is the top-level ISR node. It contains all modules and
    cross-cutting concerns.
    """
    name: str
    modules: List[Module] = field(default_factory=list)
    deployment: Optional[Deployment] = None
    constraints: List[Constraint] = field(default_factory=list)
    metadata: Metadata = field(default_factory=lambda: Metadata(version=1))
    description: Optional[str] = None
    node_type: NodeType = NodeType.SYSTEM


# ──────────────────────────────────────────────
# Ecommerce Example Factory
# ──────────────────────────────────────────────


def create_ecommerce_isr() -> System:
    """Create the canonical ecommerce example ISR from the specification."""
    return System(
        name="Shop",
        metadata=Metadata(
            version=3,
            parent_hash="sha256:a1b2c3d4e5f6...",
            provenance=["Initial construction via constitutional specification"]
        ),
        modules=[
            Module(
                name="Authentication",
                entities=[
                    Entity(
                        name="User",
                        fields=[
                            Field(name="id", field_type="uuid"),
                            Field(name="email", field_type="string", unique=True),
                            Field(name="credentials", field_type="string"),
                            Field(name="roles", field_type="list[string]"),
                        ],
                        relationships=[
                            Relationship(
                                target_entity="Order",
                                target_module="Orders",
                                type="reference",
                                cardinality=Cardinality.ONE_TO_MANY,
                            )
                        ],
                    )
                ],
                services=[
                    Service(
                        name="AuthService",
                        operations=[
                            Operation(name="login", parameters=[{"name": "email", "type": "string"}, {"name": "password", "type": "string"}], return_type="Token"),
                            Operation(name="logout", parameters=[]),
                            Operation(name="refresh", parameters=[{"name": "token", "type": "string"}], return_type="Token"),
                            Operation(name="register", parameters=[{"name": "email", "type": "string"}, {"name": "password", "type": "string"}], return_type="User"),
                        ],
                        events=["UserRegistered", "UserAuthenticated"],
                    )
                ],
                policies=[
                    Policy(
                        name="AuthPolicy",
                        strategy="OAuth2",
                        roles=["Admin", "User", "Auditor"],
                        rules=[
                            Rule(name="least-privilege", description="Grant minimal required permissions", effect="allow"),
                            Rule(name="mfa-optional", description="MFA is optional for standard operations", effect="allow"),
                        ],
                    )
                ],
                interfaces=[
                    Interface(
                        name="AuthAPI",
                        interface_type="REST",
                        endpoints=[
                            Endpoint(path="/auth/login", method="POST", operation="login"),
                            Endpoint(path="/auth/register", method="POST", operation="register"),
                            Endpoint(path="/auth/refresh", method="POST", operation="refresh"),
                        ],
                        security_bindings=[
                            SecurityBinding(policy_name="AuthPolicy", auth_strategy="oauth2"),
                        ],
                    )
                ],
            ),
            Module(
                name="Orders",
                entities=[
                    Entity(
                        name="Order",
                        fields=[
                            Field(name="id", field_type="uuid"),
                            Field(name="user_id", field_type="uuid"),
                            Field(name="status", field_type="string"),
                            Field(name="total", field_type="decimal"),
                            Field(name="created_at", field_type="datetime"),
                        ],
                    ),
                    Entity(
                        name="OrderItem",
                        fields=[
                            Field(name="id", field_type="uuid"),
                            Field(name="order_id", field_type="uuid"),
                            Field(name="product_id", field_type="uuid"),
                            Field(name="quantity", field_type="integer"),
                            Field(name="price", field_type="decimal"),
                        ],
                    ),
                ],
                services=[
                    Service(
                        name="OrderService",
                        operations=[
                            Operation(name="create", parameters=[{"name": "order_data", "type": "CreateOrderRequest"}], return_type="Order"),
                            Operation(name="cancel", parameters=[{"name": "order_id", "type": "uuid"}], return_type="Order"),
                            Operation(name="get", parameters=[{"name": "order_id", "type": "uuid"}], return_type="Order"),
                            Operation(name="list", parameters=[{"name": "user_id", "type": "uuid"}], return_type="List[Order]"),
                        ],
                        dependencies=[
                            Dependency(target_service="PaymentService", target_module="Payments", criticality="critical"),
                            Dependency(target_service="InventoryService", target_module="Inventory", criticality="critical"),
                            Dependency(target_service="NotificationService", target_module="Notifications", criticality="low"),
                        ],
                        events=["OrderCreated", "OrderCancelled"],
                    )
                ],
                workflows=[
                    Workflow(
                        name="OrderLifecycle",
                        states=[
                            State(name="Pending", is_initial=True),
                            State(name="Confirmed"),
                            State(name="Shipped"),
                            State(name="Delivered", is_terminal=True),
                            State(name="Cancelled", is_terminal=True),
                        ],
                        transitions=[
                            Transition(from_state="Pending", to_state="Confirmed", action="PaymentConfirmed"),
                            Transition(from_state="Pending", to_state="Cancelled", action="PaymentFailed"),
                            Transition(from_state="Confirmed", to_state="Shipped", action="Shipped"),
                            Transition(from_state="Shipped", to_state="Delivered", action="Delivered"),
                        ],
                    )
                ],
                interfaces=[
                    Interface(
                        name="OrderAPI",
                        interface_type="REST",
                        endpoints=[
                            Endpoint(path="/orders", method="POST", operation="create"),
                            Endpoint(path="/orders", method="GET", operation="list"),
                            Endpoint(path="/orders/{id}", method="GET", operation="get"),
                        ],
                        security_bindings=[SecurityBinding(policy_name="AuthPolicy")],
                    )
                ],
            ),
            Module(
                name="Catalogue",
                entities=[
                    Entity(
                        name="Product",
                        fields=[
                            Field(name="id", field_type="uuid"),
                            Field(name="name", field_type="string"),
                            Field(name="description", field_type="string"),
                            Field(name="price", field_type="decimal"),
                            Field(name="sku", field_type="string", unique=True),
                        ],
                    ),
                ],
                services=[
                    Service(
                        name="CatalogueService",
                        operations=[
                            Operation(name="create", parameters=[{"name": "product_data", "type": "CreateProductRequest"}], return_type="Product"),
                            Operation(name="update", parameters=[{"name": "product_id", "type": "uuid"}, {"name": "product_data", "type": "UpdateProductRequest"}], return_type="Product"),
                            Operation(name="get", parameters=[{"name": "product_id", "type": "uuid"}], return_type="Product"),
                            Operation(name="search", parameters=[{"name": "query", "type": "string"}], return_type="List[Product]"),
                            Operation(name="list", parameters=[]),
                        ],
                    )
                ],
                interfaces=[
                    Interface(
                        name="CatalogueAPI",
                        interface_type="REST",
                        endpoints=[
                            Endpoint(path="/products", method="GET", operation="list"),
                            Endpoint(path="/products/{id}", method="GET", operation="get"),
                            Endpoint(path="/products", method="POST", operation="create"),
                        ],
                        security_bindings=[SecurityBinding(policy_name="AuthPolicy")],
                    )
                ],
            ),
            Module(
                name="Payments",
                services=[
                    Service(
                        name="PaymentService",
                        operations=[
                            Operation(name="charge", parameters=[{"name": "payment_data", "type": "ChargeRequest"}], return_type="PaymentResult"),
                            Operation(name="refund", parameters=[{"name": "payment_id", "type": "uuid"}], return_type="PaymentResult"),
                            Operation(name="verify", parameters=[{"name": "payment_id", "type": "uuid"}], return_type="bool"),
                        ],
                        events=["PaymentConfirmed", "PaymentFailed"],
                    )
                ],
                interfaces=[
                    Interface(
                        name="PaymentAPI",
                        interface_type="REST",
                        internal=True,
                        endpoints=[
                            Endpoint(path="/internal/payments/charge", method="POST", operation="charge"),
                        ],
                    )
                ],
            ),
            Module(
                name="Inventory",
                services=[
                    Service(
                        name="InventoryService",
                        operations=[
                            Operation(name="reserve", parameters=[{"name": "product_id", "type": "uuid"}, {"name": "quantity", "type": "integer"}]),
                            Operation(name="release", parameters=[{"name": "product_id", "type": "uuid"}, {"name": "quantity", "type": "integer"}]),
                            Operation(name="check", parameters=[{"name": "product_id", "type": "uuid"}], return_type="int"),
                        ],
                        events=["StockDepleted", "StockReserved"],
                    )
                ],
            ),
            Module(
                name="Notifications",
                services=[
                    Service(
                        name="NotificationService",
                        operations=[
                            Operation(name="send_email", parameters=[{"name": "to", "type": "string"}, {"name": "subject", "type": "string"}, {"name": "body", "type": "string"}]),
                            Operation(name="send_sms", parameters=[{"name": "to", "type": "string"}, {"name": "message", "type": "string"}]),
                            Operation(name="send_push", parameters=[{"name": "device_token", "type": "string"}, {"name": "message", "type": "string"}]),
                        ],
                        consumes=["OrderCreated", "OrderCancelled", "PaymentConfirmed"],
                    )
                ],
            ),
        ],
    )