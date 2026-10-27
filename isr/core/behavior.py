"""Typed, technology-neutral behavioral semantics carried by ISR nodes.

The graph remains the canonical, content-addressed source of truth. A node may
opt into this contract through its properties["behavior"] payload. Legacy
structural nodes without that key remain readable, but are not thereby proven
behaviorally complete.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValueType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    MONEY = "money"
    IDENTIFIER = "identifier"


class ConstraintOperator(str, Enum):
    MIN = "min"
    MAX = "max"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    ONE_OF = "one_of"
    UNIQUE = "unique"
    IMMUTABLE = "immutable"
    REFERENCES = "references"


class FieldConstraint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operator: ConstraintOperator
    value: Any = None


class FieldSpec(BaseModel):
    """A typed field; decimal/money precision and nullability are explicit."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,127}$")
    value_type: ValueType
    required: bool = True
    nullable: bool = False
    precision: int | None = Field(default=None, ge=0, le=18)
    scale: int | None = Field(default=None, ge=0, le=18)
    constraints: tuple[FieldConstraint, ...] = ()

    @model_validator(mode="after")
    def validate_numeric_shape(self) -> "FieldSpec":
        if self.nullable and self.required:
            raise ValueError("a nullable field cannot also be required")
        if self.value_type not in (ValueType.DECIMAL, ValueType.MONEY):
            if self.precision is not None or self.scale is not None:
                raise ValueError("precision/scale are valid only for decimal or money fields")
        if self.scale is not None and self.precision is not None and self.scale > self.precision:
            raise ValueError("scale cannot exceed precision")
        return self


class Expression(BaseModel):
    """A bounded expression tree; never source code and never eval()-ed."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    op: Literal[
        "literal", "field", "add", "subtract", "multiply", "divide",
        "equal", "not_equal", "less_than", "less_or_equal", "greater_than",
        "greater_or_equal", "and", "or", "not", "if_else",
    ]
    value: str | int | float | bool | None = None
    field_ref: str | None = None
    args: tuple["Expression", ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> "Expression":
        arity = {
            "literal": 0, "field": 0, "not": 1,
            "add": 2, "subtract": 2, "multiply": 2, "divide": 2,
            "equal": 2, "not_equal": 2, "less_than": 2,
            "less_or_equal": 2, "greater_than": 2, "greater_or_equal": 2,
            "and": 2, "or": 2, "if_else": 3,
        }[self.op]
        if len(self.args) != arity:
            raise ValueError(f"operator {self.op!r} requires {arity} argument(s)")
        if self.op == "field":
            if not self.field_ref or self.value is not None:
                raise ValueError("field expressions require field_ref and forbid value")
        elif self.field_ref is not None:
            raise ValueError("field_ref is valid only for field expressions")
        if self.op == "literal":
            if self.value is None:
                raise ValueError("null literals are not supported in v1 expressions")
        elif self.value is not None:
            raise ValueError("value is valid only for literal expressions")
        return self


Expression.model_rebuild()


class BusinessRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expression: Expression


class InvariantSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    invariant_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expression: Expression


class StateTransition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    transition_id: str = Field(min_length=1)
    source_state: str = Field(min_length=1)
    target_state: str = Field(min_length=1)
    guard: Expression | None = None


class FrontendRouteBehavior(BaseModel):
    """Technology-neutral route and page semantics for a generated UI."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str = Field(pattern=r"^/")
    title: str = Field(min_length=1)
    requires_auth: bool = False


class FrontendInteractionBehavior(BaseModel):
    """A named UI action connected to an API or service through ISR edges."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: str = Field(min_length=1)
    action: Literal["submit", "refresh", "delete", "toggle"]
    success_message: str | None = None


class AuthorizationRule(BaseModel):
    """Technology-neutral allow/deny rule; absent rules never imply access."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: str = Field(min_length=1)
    effect: Literal["allow", "deny"]
    roles: tuple[str, ...] = Field(min_length=1)
    actions: tuple[str, ...] = Field(min_length=1)
    resource: str = Field(min_length=1)
    conditions: dict[str, Any] = Field(default_factory=dict)


class DataModelBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    fields: tuple[FieldSpec, ...] = Field(min_length=1)
    invariants: tuple[InvariantSpec, ...] = ()


class EventBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    fields: tuple[FieldSpec, ...] = ()


class ServiceBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rules: tuple[BusinessRule, ...] = ()
    transitions: tuple[StateTransition, ...] = ()


class ApiBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation_id: str = Field(min_length=1)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(pattern=r"^/")
    request_fields: tuple[FieldSpec, ...] = ()
    response_fields: tuple[FieldSpec, ...] = ()
    authorization_policy_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_path_parameters(self) -> "ApiBehavior":
        placeholders = set(re.findall(r"\{([^{}]+)\}", self.path))
        field_names = {field.name for field in self.request_fields}
        missing = sorted(placeholders - field_names)
        if missing:
            raise ValueError(f"path parameters missing from request_fields: {missing}")
        return self


class EffectBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    effect_kind: str = Field(min_length=1)
    idempotent: bool = False
    idempotency_key_required: bool = False
    # Executable contract fields – all-or-nothing when set
    precondition: Expression | None = None
    authorized_operation: str | None = None
    permitted_side_effect: str | None = None
    failure_behavior: Literal["reject_without_commit"] | None = None
    postcondition: Expression | None = None

    @model_validator(mode="after")
    def validate_idempotency(self) -> "EffectBehavior":
        if self.idempotency_key_required and not self.idempotent:
            raise ValueError("idempotency key requirement requires an idempotent effect")
        # All-or-nothing executable contract enforcement
        has_exec = (
            self.precondition is not None or
            self.authorized_operation is not None or
            self.permitted_side_effect is not None or
            self.failure_behavior is not None or
            self.postcondition is not None
        )
        if has_exec:
            if not (
                self.precondition is not None and
                self.authorized_operation is not None and
                self.permitted_side_effect is not None and
                self.failure_behavior is not None and
                self.postcondition is not None and
                self.idempotent is True and
                self.idempotency_key_required is True
            ):
                raise ValueError(
                    "when any executable effect field is present, all fields "
                    "(precondition, authorized_operation, permitted_side_effect, "
                    "failure_behavior, postcondition, idempotent, idempotency_key_required) "
                    "must be set"
                )
        return self


class ConsequenceBehavior(BaseModel):
    """Observable consequence and failure contract declared by an ISR node."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    trigger: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    failure_policy: str = Field(min_length=1)
    effect_consequence: dict[str, Any] = Field(default_factory=dict)
    source_requirement_ids: tuple[str, ...] = ()


class SecurityBehavior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    roles: tuple[str, ...] = Field(min_length=1)
    rules: tuple[AuthorizationRule, ...] = ()

    @model_validator(mode="after")
    def validate_policy_ids(self) -> "SecurityBehavior":
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("authorization rule IDs must be unique")
        unknown_roles = sorted({role for rule in self.rules for role in rule.roles} - set(self.roles))
        if unknown_roles:
            raise ValueError(f"authorization rules reference undeclared roles: {unknown_roles}")
        return self


def validate_behavior_payload(node_type: str, payload: Any) -> BaseModel:
    """Parse behavior payload according to its owning ISR node kind."""
    schemas: dict[str, type[BaseModel]] = {
        "data_model": DataModelBehavior,
        "event": EventBehavior,
        "service": ServiceBehavior,
        "api": ApiBehavior,
        "effect": EffectBehavior,
        "security_policy": SecurityBehavior,
        "invariant": InvariantSpec,
        "frontend_route": FrontendRouteBehavior,
        "frontend_interaction": FrontendInteractionBehavior,
    }
    schema = schemas.get(node_type)
    if schema is None:
        raise ValueError(f"behavior payload is not supported on node type {node_type!r}")
    return schema.model_validate(payload)


def expression_field_refs(expression: Expression) -> set[str]:
    """Return all referenced field paths for binding validation."""
    refs = {expression.field_ref} if expression.op == "field" and expression.field_ref else set()
    for arg in expression.args:
        refs.update(expression_field_refs(arg))
    return refs
