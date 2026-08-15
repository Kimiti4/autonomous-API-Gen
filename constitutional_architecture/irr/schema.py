"""
IRR Schema — Intermediate Requirement Representation

The IRR captures what the system must do, independently of how it is
architected. This separation allows requirements to remain stable while
architecture evolves freely.

The IRR is converted into a typed Requirement Graph, which becomes the
structured input to ISR construction. It is technology-neutral and
implementation-agnostic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class RequirementType(Enum):
    """Types of requirements in the IRR."""
    USER_STORY = "user_story"
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    DOMAIN_CONCEPT = "domain_concept"
    ACCEPTANCE_CRITERION = "acceptance_criterion"


class RequirementPriority(Enum):
    """Priority levels for requirements."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class RequirementStatus(Enum):
    """Status of a requirement in the pipeline."""
    DRAFT = "draft"
    ANALYSED = "analysed"
    SPECIFIED = "specified"
    VERIFIED = "verified"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


class RequirementRelationType(Enum):
    """Types of relationships between requirements."""
    REFINES = "refines"           # A refines B (A is more specific)
    DEPENDS_ON = "depends-on"    # A depends on B
    CONFLICTS_WITH = "conflicts-with"
    SATISFIES = "satisfies"      # A satisfies B (e.g., functional satisfies user story)
    CONSTRAINS = "constrains"    # A constrains B
    TRACES_TO = "traces-to"      # A traces to B (traceability link)
    DUPLICATES = "duplicates"    # A duplicates B
    RELATES_TO = "relates-to"    # General relationship


class NFRCategory(Enum):
    """Categories of non-functional requirements."""
    PERFORMANCE = "performance"
    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"
    USABILITY = "usability"
    AVAILABILITY = "availability"
    COMPLIANCE = "compliance"
    OBSERVABILITY = "observability"
    TESTABILITY = "testability"
    PORTABILITY = "portability"


# ──────────────────────────────────────────────
# IRR Data Classes
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class UserStory:
    """A user story expressing intent from a user's perspective."""
    id: str = field(default_factory=lambda: f"US-{uuid.uuid4().hex[:8]}")
    actor: str = ""
    action: str = ""
    benefit: str = ""
    narrative: str = ""
    priority: RequirementPriority = RequirementPriority.MEDIUM
    acceptance_criteria: List[str] = field(default_factory=list)
    status: RequirementStatus = RequirementStatus.DRAFT

    @property
    def formatted(self) -> str:
        """Return the standard user story format."""
        if self.narrative:
            return self.narrative
        return f"As a {self.actor}, I want to {self.action} so that {self.benefit}"


@dataclass(frozen=True)
class FunctionalRequirement:
    """A specific functional requirement — what the system must do."""
    id: str = field(default_factory=lambda: f"FR-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    priority: RequirementPriority = RequirementPriority.MEDIUM
    status: RequirementStatus = RequirementStatus.DRAFT
    user_story_ids: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class NonFunctionalRequirement:
    """A quality attribute requirement."""
    id: str = field(default_factory=lambda: f"NFR-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    category: NFRCategory = NFRCategory.PERFORMANCE
    metric: Optional[str] = None  # e.g., "p99 latency < 200ms"
    target_value: Optional[str] = None  # e.g., "200ms"
    priority: RequirementPriority = RequirementPriority.MEDIUM
    status: RequirementStatus = RequirementStatus.DRAFT


@dataclass(frozen=True)
class Constraint:
    """A hard boundary — regulatory, technological, or organisational."""
    id: str = field(default_factory=lambda: f"CON-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    constraint_type: str = "regulatory"  # "regulatory" | "technological" | "organisational"
    is_hard: bool = True  # Hard constraints cannot be violated
    priority: RequirementPriority = RequirementPriority.CRITICAL
    status: RequirementStatus = RequirementStatus.DRAFT


@dataclass(frozen=True)
class DomainConcept:
    """A domain concept identified from requirements."""
    id: str = field(default_factory=lambda: f"DC-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    attributes: List[str] = field(default_factory=list)
    relationships: List[Tuple[str, str, str]] = field(default_factory=list)  # (target, type, description)
    is_entity: bool = True
    is_value_object: bool = False
    is_aggregate: bool = False
    status: RequirementStatus = RequirementStatus.DRAFT


@dataclass(frozen=True)
class AcceptanceCriterion:
    """A measurable condition for satisfaction."""
    id: str = field(default_factory=lambda: f"AC-{uuid.uuid4().hex[:8]}")
    description: str = ""
    scenario: str = ""  # Given/When/Then format
    is_automated: bool = False
    status: RequirementStatus = RequirementStatus.DRAFT


@dataclass(frozen=True)
class IRR:
    """The complete Intermediate Requirement Representation.

    This is the output of requirement extraction from natural language.
    It is stable across architectural evolution — changes to the ISR
    do not change the IRR.
    """
    id: str = field(default_factory=lambda: f"IRR-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    user_stories: List[UserStory] = field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    domain_concepts: List[DomainConcept] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1
    status: RequirementStatus = RequirementStatus.DRAFT


# ──────────────────────────────────────────────
# Requirement Graph
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class RequirementNode:
    """A node in the requirement graph."""
    node_id: str
    requirement_type: RequirementType
    label: str
    data: Any  # The actual requirement object
    priority: RequirementPriority = RequirementPriority.MEDIUM


@dataclass(frozen=True)
class RequirementEdge:
    """A typed edge in the requirement graph."""
    source_id: str
    target_id: str
    relation_type: RequirementRelationType
    attributes: Dict[str, Any] = field(default_factory=dict)


class RequirementGraph:
    """A typed graph of requirement relationships.

    This graph becomes the structured input to ISR construction.
    It is technology-neutral and implementation-agnostic.
    """

    def __init__(self, irr: IRR):
        self._irr = irr
        self._nodes: Dict[str, RequirementNode] = {}
        self._edges: List[RequirementEdge] = []
        self._build_graph()

    def _add_node(self, node: RequirementNode):
        self._nodes[node.node_id] = node

    def _add_edge(self, edge: RequirementEdge):
        self._edges.append(edge)

    def _build_graph(self):
        """Build the requirement graph from the IRR."""
        # Add user stories
        for us in self._irr.user_stories:
            self._add_node(RequirementNode(
                node_id=us.id,
                requirement_type=RequirementType.USER_STORY,
                label=us.formatted[:100],
                data=us,
                priority=us.priority,
            ))

        # Add functional requirements
        for fr in self._irr.functional_requirements:
            self._add_node(RequirementNode(
                node_id=fr.id,
                requirement_type=RequirementType.FUNCTIONAL,
                label=fr.name or fr.description[:100],
                data=fr,
                priority=fr.priority,
            ))

            # Link to user stories
            for us_id in fr.user_story_ids:
                if us_id in self._nodes:
                    self._add_edge(RequirementEdge(
                        source_id=fr.id,
                        target_id=us_id,
                        relation_type=RequirementRelationType.SATISFIES,
                    ))

        # Add non-functional requirements
        for nfr in self._irr.non_functional_requirements:
            self._add_node(RequirementNode(
                node_id=nfr.id,
                requirement_type=RequirementType.NON_FUNCTIONAL,
                label=nfr.name or nfr.description[:100],
                data=nfr,
                priority=nfr.priority,
            ))

        # Add constraints
        for con in self._irr.constraints:
            self._add_node(RequirementNode(
                node_id=con.id,
                requirement_type=RequirementType.CONSTRAINT,
                label=con.name or con.description[:100],
                data=con,
                priority=con.priority,
            ))

        # Add domain concepts
        for dc in self._irr.domain_concepts:
            self._add_node(RequirementNode(
                node_id=dc.id,
                requirement_type=RequirementType.DOMAIN_CONCEPT,
                label=dc.name,
                data=dc,
            ))

            # Add domain concept relationships
            for target_name, rel_type, desc in dc.relationships:
                # Find target concept by name
                for other_dc in self._irr.domain_concepts:
                    if other_dc.name == target_name:
                        self._add_edge(RequirementEdge(
                            source_id=dc.id,
                            target_id=other_dc.id,
                            relation_type=RequirementRelationType.RELATES_TO,
                            attributes={"type": rel_type, "description": desc},
                        ))

        # Add acceptance criteria
        for ac in self._irr.acceptance_criteria:
            self._add_node(RequirementNode(
                node_id=ac.id,
                requirement_type=RequirementType.ACCEPTANCE_CRITERION,
                label=ac.description[:100],
                data=ac,
            ))

    @property
    def nodes(self) -> Dict[str, RequirementNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> List[RequirementEdge]:
        return list(self._edges)

    def get_nodes_by_type(self, req_type: RequirementType) -> List[RequirementNode]:
        return [n for n in self._nodes.values() if n.requirement_type == req_type]

    def get_edges_from(self, node_id: str) -> List[RequirementEdge]:
        return [e for e in self._edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[RequirementEdge]:
        return [e for e in self._edges if e.target_id == node_id]

    def get_traceability_chain(self, node_id: str) -> Dict[str, List[str]]:
        """Get the full traceability chain for a requirement."""
        upstream = []
        downstream = []
        stack = [node_id]
        visited = set()

        # Upstream (what this satisfies/refines)
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for edge in self.get_edges_to(current):
                upstream.append(edge.source_id)
                stack.append(edge.source_id)

        # Downstream (what satisfies/refines this)
        stack = [node_id]
        visited = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for edge in self.get_edges_from(current):
                downstream.append(edge.target_id)
                stack.append(edge.target_id)

        return {
            "upstream": list(set(upstream)),
            "downstream": list(set(downstream)),
        }

    @property
    def irr(self) -> IRR:
        return self._irr


# ──────────────────────────────────────────────
# Builder Functions
# ──────────────────────────────────────────────


def build_requirement_graph(irr: IRR) -> RequirementGraph:
    """Build a requirement graph from an IRR."""
    return RequirementGraph(irr)


def capture_ecommerce_requirements() -> IRR:
    """Capture the canonical ecommerce example as an IRR.

    This demonstrates the IRR → Requirement Graph → ISR pipeline
    using the ecommerce example from the specification.
    """
    return IRR(
        name="Ecommerce Platform",
        description="An ecommerce platform supporting user authentication, "
                    "order management, product catalogue, payments, inventory, "
                    "and notifications.",
        user_stories=[
            UserStory(
                id="US-001",
                actor="User",
                action="register an account with email and password",
                benefit="I can access the platform",
                priority=RequirementPriority.CRITICAL,
            ),
            UserStory(
                id="US-002",
                actor="User",
                action="log in with my credentials",
                benefit="I can access my account securely",
                priority=RequirementPriority.CRITICAL,
            ),
            UserStory(
                id="US-003",
                actor="User",
                action="browse products in the catalogue",
                benefit="I can see what's available to purchase",
                priority=RequirementPriority.HIGH,
            ),
            UserStory(
                id="US-004",
                actor="User",
                action="place an order for products",
                benefit="I can purchase items",
                priority=RequirementPriority.CRITICAL,
            ),
            UserStory(
                id="US-005",
                actor="User",
                action="view my order history",
                benefit="I can track my purchases",
                priority=RequirementPriority.MEDIUM,
            ),
            UserStory(
                id="US-006",
                actor="User",
                action="receive notifications about my orders",
                benefit="I stay informed about order status",
                priority=RequirementPriority.MEDIUM,
            ),
            UserStory(
                id="US-007",
                actor="Admin",
                action="manage the product catalogue",
                benefit="I can add, update, and remove products",
                priority=RequirementPriority.HIGH,
            ),
            UserStory(
                id="US-008",
                actor="Admin",
                action="view and manage orders",
                benefit="I can process customer orders",
                priority=RequirementPriority.HIGH,
            ),
        ],
        functional_requirements=[
            FunctionalRequirement(
                id="FR-001", name="User Registration",
                description="The system shall allow users to register with email and password",
                priority=RequirementPriority.CRITICAL,
                user_story_ids=["US-001"],
            ),
            FunctionalRequirement(
                id="FR-002", name="User Authentication",
                description="The system shall authenticate users with email and password",
                priority=RequirementPriority.CRITICAL,
                user_story_ids=["US-002"],
            ),
            FunctionalRequirement(
                id="FR-003", name="Product Catalogue",
                description="The system shall maintain a catalogue of products with CRUD operations",
                priority=RequirementPriority.HIGH,
                user_story_ids=["US-003", "US-007"],
            ),
            FunctionalRequirement(
                id="FR-004", name="Order Management",
                description="The system shall allow users to create, view, and cancel orders",
                priority=RequirementPriority.CRITICAL,
                user_story_ids=["US-004", "US-005", "US-008"],
            ),
            FunctionalRequirement(
                id="FR-005", name="Payment Processing",
                description="The system shall process payments for orders",
                priority=RequirementPriority.CRITICAL,
                user_story_ids=["US-004"],
            ),
            FunctionalRequirement(
                id="FR-006", name="Inventory Management",
                description="The system shall track product inventory and reserve stock on order",
                priority=RequirementPriority.HIGH,
                user_story_ids=["US-004"],
            ),
            FunctionalRequirement(
                id="FR-007", name="Notification Delivery",
                description="The system shall send notifications for order events",
                priority=RequirementPriority.MEDIUM,
                user_story_ids=["US-006"],
            ),
        ],
        non_functional_requirements=[
            NonFunctionalRequirement(
                id="NFR-001", name="API Response Time",
                description="API responses should be fast",
                category=NFRCategory.PERFORMANCE,
                metric="p95 latency < 500ms",
                target_value="500ms",
                priority=RequirementPriority.HIGH,
            ),
            NonFunctionalRequirement(
                id="NFR-002", name="Authentication Security",
                description="Authentication must use industry-standard protocols",
                category=NFRCategory.SECURITY,
                metric="OAuth2/OIDC compliance",
                priority=RequirementPriority.CRITICAL,
            ),
            NonFunctionalRequirement(
                id="NFR-003", name="System Availability",
                description="The system should be highly available",
                category=NFRCategory.AVAILABILITY,
                metric="99.9% uptime",
                target_value="99.9%",
                priority=RequirementPriority.HIGH,
            ),
            NonFunctionalRequirement(
                id="NFR-004", name="Order Processing Scalability",
                description="The system should handle peak order volumes",
                category=NFRCategory.SCALABILITY,
                metric="1000 orders/minute",
                target_value="1000",
                priority=RequirementPriority.MEDIUM,
            ),
        ],
        constraints=[
            Constraint(
                id="CON-001", name="Data Privacy",
                description="User data must be encrypted at rest and in transit",
                constraint_type="regulatory",
                is_hard=True,
            ),
            Constraint(
                id="CON-002", name="Audit Trail",
                description="All financial transactions must be auditable",
                constraint_type="regulatory",
                is_hard=True,
            ),
        ],
        domain_concepts=[
            DomainConcept(
                id="DC-001", name="User",
                description="A registered user of the platform",
                attributes=["id", "email", "password", "roles"],
                relationships=[("Order", "places", "A user places orders")],
                is_entity=True,
                is_aggregate=True,
            ),
            DomainConcept(
                id="DC-002", name="Product",
                description="An item available for purchase",
                attributes=["id", "name", "description", "price", "sku"],
                is_entity=True,
            ),
            DomainConcept(
                id="DC-003", name="Order",
                description="A purchase order containing items",
                attributes=["id", "user_id", "status", "total", "created_at"],
                relationships=[
                    ("User", "belongs-to", "An order belongs to a user"),
                    ("OrderItem", "contains", "An order contains items"),
                ],
                is_entity=True,
                is_aggregate=True,
            ),
            DomainConcept(
                id="DC-004", name="OrderItem",
                description="A line item within an order",
                attributes=["id", "order_id", "product_id", "quantity", "price"],
                is_entity=True,
            ),
            DomainConcept(
                id="DC-005", name="Payment",
                description="A payment transaction for an order",
                attributes=["id", "order_id", "amount", "status", "method"],
                is_entity=True,
            ),
            DomainConcept(
                id="DC-006", name="Inventory",
                description="Product stock levels",
                attributes=["product_id", "quantity_available", "reserved_quantity"],
                is_entity=False,
                is_value_object=True,
            ),
            DomainConcept(
                id="DC-007", name="Notification",
                description="A message sent to a user about an event",
                attributes=["id", "user_id", "type", "content", "status"],
                is_entity=True,
            ),
        ],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-001",
                description="User can register with valid email and password",
                scenario="Given a new user with valid email and password, When they register, Then an account is created",
            ),
            AcceptanceCriterion(
                id="AC-002",
                description="User can place an order with available products",
                scenario="Given a logged-in user with products in cart, When they place an order, Then the order is created and inventory is reserved",
            ),
            AcceptanceCriterion(
                id="AC-003",
                description="Order status transitions follow the defined lifecycle",
                scenario="Given a confirmed order, When payment is processed, Then the order moves to Confirmed state",
            ),
        ],
    )