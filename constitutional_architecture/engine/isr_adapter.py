"""
ISR Adapter — Bidirectional Bridge between ISR Model and TypedGraph.

Constitutional constraint: this module sits between isr.model and isr.graph.
It NEVER imports from compiler.*, backends.*, or verification.*.
"""

from __future__ import annotations

import uuid
from typing import Any

from constitutional_architecture.engine.fitness import FitnessVector as EngineFitnessVector
from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.eir.taxonomy import KNOWN_TRANSFORMATIONS, MutationCategory, MutationClass
from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.metrics.static_fitness import StaticFitnessEvaluator
from constitutional_architecture.isr.model.edges import EdgeAttributes, EdgeType
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.event import Event, EventPattern, EventGuarantee
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.interface import Endpoint, HttpMethod, Interface, InterfaceType
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service, ServiceDependency
from constitutional_architecture.isr.model.system import System


def isr_to_graph(isr: ISR) -> TypedGraph:
    """Convert an ISR model into a TypedGraph for evolution."""
    graph = TypedGraph()

    sys_id = f"sys:{isr.system.id}"
    graph.add_node(GraphNode(
        id=sys_id, node_type=NodeType.SYSTEM,
        label=isr.system.name,
        attributes={"name": isr.system.name, "description": isr.system.description, "isr_version": isr.version},
    ))

    for module in isr.system.modules:
        mod_id = f"mod:{module.id}"
        graph.add_node(GraphNode(
            id=mod_id, node_type=NodeType.MODULE, label=module.name,
            attributes={"name": module.name, "description": module.description},
            parent_id=sys_id,
        ))
        _add_edge(graph, sys_id, mod_id, EdgeType.OWNS)

        for entity in module.entities:
            eid = f"ent:{entity.id}"
            graph.add_node(GraphNode(
                id=eid, node_type=NodeType.ENTITY, label=entity.name,
                attributes={"name": entity.name, "id": entity.id},
                parent_id=mod_id,
            ))
            _add_edge(graph, mod_id, eid, EdgeType.OWNS)
            _fields_to_graph(graph, eid, entity.fields)

        for service in module.services:
            sid = f"svc:{service.id}"
            graph.add_node(GraphNode(
                id=sid, node_type=NodeType.SERVICE, label=service.name,
                attributes={"name": service.name, "is_stateless": service.is_stateless},
                parent_id=mod_id,
            ))
            _add_edge(graph, mod_id, sid, EdgeType.OWNS)

            for op in service.operations:
                oid = f"op:{op.id}"
                graph.add_node(GraphNode(
                    id=oid, node_type=NodeType.OPERATION, label=op.name,
                    attributes={"name": op.name, "operation_type": op.operation_type.value},
                    parent_id=sid,
                ))
                _add_edge(graph, sid, oid, EdgeType.OWNS)

            for dep in service.dependencies:
                did = f"svc:{dep.target_service_id}"
                if graph.get_node(did):
                    _add_edge(graph, sid, did, EdgeType.DEPENDS_ON,
                              attrs=EdgeAttributes(
                                  coupling_strength=_parse_coupling(dep.dependency_type),
                              ))

        for iface in module.interfaces:
            iid = f"iface:{iface.id}"
            graph.add_node(GraphNode(
                id=iid, node_type=NodeType.INTERFACE, label=iface.name,
                attributes={"name": iface.name, "interface_type": iface.interface_type.value,
                            "is_internal": iface.is_internal},
                parent_id=mod_id,
            ))
            _add_edge(graph, mod_id, iid, EdgeType.OWNS)

            for ep in iface.endpoints:
                epid = f"ep:{iface.id}:{ep.id}"
                graph.add_node(GraphNode(
                    id=epid, node_type=NodeType.ENDPOINT, label=f"{ep.method.value} {ep.path}",
                    attributes={"path": ep.path, "method": ep.method.value, "name": ep.name},
                    parent_id=iid,
                ))
                _add_edge(graph, iid, epid, EdgeType.OWNS)

            if iface.secured_by_policy_id:
                pid = f"pol:{iface.secured_by_policy_id}"
                if graph.get_node(pid):
                    _add_edge(graph, iid, pid, EdgeType.SECURED_BY)

        for policy in module.policies:
            pid = f"pol:{policy.id}"
            graph.add_node(GraphNode(
                id=pid, node_type=NodeType.POLICY, label=policy.name,
                attributes={"name": policy.name, "strategy": policy.strategy,
                            "policy_type": policy.policy_type.value},
                parent_id=mod_id,
            ))
            _add_edge(graph, mod_id, pid, EdgeType.OWNS)

        for event in module.events:
            evid = f"evt:{event.id}"
            graph.add_node(GraphNode(
                id=evid, node_type=NodeType.EVENT, label=event.name,
                attributes={"name": event.name, "pattern": event.pattern.value},
                parent_id=mod_id,
            ))
            _add_edge(graph, mod_id, evid, EdgeType.OWNS)

    return graph


def graph_to_isr(graph: TypedGraph, parent: ISR) -> ISR:
    """Convert a TypedGraph back to a new immutable ISR version."""
    sys_nodes = graph.get_nodes_by_type(NodeType.SYSTEM)
    if not sys_nodes:
        raise ValueError("Graph has no System node")

    root = sys_nodes[0]
    mod_nodes = [n for n in graph.get_nodes_by_type(NodeType.MODULE) if n.parent_id == root.id]
    modules = []

    for mnode in mod_nodes:
        entities = _graph_to_entities(graph, mnode)
        services = _graph_to_services(graph, mnode)
        interfaces = _graph_to_interfaces(graph, mnode)
        policies = _graph_to_policies(graph, mnode)
        events = _graph_to_events(graph, mnode)
        workflows = _graph_to_workflows(graph, mnode)

        modules.append(Module(
            id=mnode.id.replace("mod:", ""),
            name=mnode.label,
            description=mnode.attributes.get("description", ""),
            entities=tuple(entities),
            services=tuple(services),
            interfaces=tuple(interfaces),
            policies=tuple(policies),
            events=tuple(events),
            workflows=tuple(workflows),
        ))

    new_system = System(
        id=parent.system.id,
        name=root.attributes.get("name", parent.system.name),
        modules=tuple(modules),
    )

    return ISR(
        system=new_system,
        version=parent.version + 1,
        provenance=ISRProvenance(
            parent_hash=parent.content_hash,
            mutation_description=f"Graph-to-ISR conversion from v{parent.version}",
        ),
    )


def evaluate_fitness(isr: ISR) -> EngineFitnessVector:
    """Evaluate static fitness from ISR using the graph-based evaluator."""
    graph = isr_to_graph(isr)
    evaluator = StaticFitnessEvaluator()
    sf = evaluator.evaluate(graph)
    return EngineFitnessVector(values=sf.to_dict())


def eir_from_transformations(
    source_isr: ISR, target_isr: ISR,
    transformations: list[Transformation],
    proposed_by: str = "evolution_adapter", generation: int = 0,
) -> EIR:
    return EIR(
        id=f"eir-{uuid.uuid4().hex[:12]}",
        source_isr_hash=source_isr.content_hash,
        target_isr_hash=target_isr.content_hash,
        transformations=tuple(transformations),
        proposed_by=proposed_by, generation=generation,
    )


def build_transformation(
    transform_type: str, target_node_id: str,
    parameters: dict[str, Any] | None = None, description: str = "",
) -> Transformation:
    cat, cls, default_desc = KNOWN_TRANSFORMATIONS.get(
        transform_type,
        (MutationCategory.STRUCTURAL, MutationClass.ADDITIVE, "Architectural transformation"),
    )
    return Transformation(
        id=f"t-{uuid.uuid4().hex[:8]}",
        transformation_type=transform_type, category=cat, mutation_class=cls,
        target_node_id=target_node_id, description=description or default_desc,
        parameters=parameters or {}, reversible=True,
    )


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _add_edge(graph: TypedGraph, src: str, tgt: str, etype: EdgeType, attrs: EdgeAttributes | None = None) -> None:
    eid = f"e:{src}->{tgt}:{uuid.uuid4().hex[:4]}"
    graph.add_edge(GraphEdge(id=eid, source_id=src, target_id=tgt, edge_type=etype, attributes=attrs or EdgeAttributes()))


def _fields_to_graph(graph: TypedGraph, parent_id: str, fields: tuple[Field, ...]) -> None:
    for f in fields:
        fid = f"fld:{parent_id}.{f.name}"
        graph.add_node(GraphNode(
            id=fid, node_type=NodeType.FIELD, label=f.name,
            attributes={
                "name": f.name, "field_type": f.field_type.value,
                "cardinality": f.cardinality.value,
                "description": f.description,
            },
            parent_id=parent_id,
        ))
        _add_edge(graph, parent_id, fid, EdgeType.OWNS)


def _graph_to_fields(graph: TypedGraph, parent_id: str) -> list[Field]:
    fld_nodes = [n for n in graph.get_nodes_by_type(NodeType.FIELD) if n.parent_id == parent_id]
    return [
        Field(
            name=n.attributes.get("name", n.label),
            field_type=_parse_field_type(n.attributes.get("field_type", "string")),
            cardinality=_parse_cardinality(n.attributes.get("cardinality", "required")),
        )
        for n in fld_nodes
    ]


def _graph_to_entities(graph: TypedGraph, mnode: GraphNode) -> list[Entity]:
    enodes = [n for n in graph.get_nodes_by_type(NodeType.ENTITY) if n.parent_id == mnode.id]
    result = []
    for en in enodes:
        fields = _graph_to_fields(graph, en.id)
        result.append(Entity(
            id=en.attributes.get("id", en.id.replace("ent:", "")),
            name=en.label,
            fields=tuple(fields),
        ))
    return result


def _graph_to_services(graph: TypedGraph, mnode: GraphNode) -> list[Service]:
    snodes = [n for n in graph.get_nodes_by_type(NodeType.SERVICE) if n.parent_id == mnode.id]
    result = []
    for sn in snodes:
        onodes = [n for n in graph.get_nodes_by_type(NodeType.OPERATION) if n.parent_id == sn.id]
        ops = tuple(
            Operation(
                id=n.id.replace("op:", ""),
                name=n.attributes.get("name", n.label),
                operation_type=OperationType(n.attributes.get("operation_type", "command")),
            )
            for n in onodes
        )
        deps: list[ServiceDependency] = []
        for edge in graph.get_outgoing_edges(sn.id):
            if edge.edge_type == EdgeType.DEPENDS_ON:
                target = graph.get_node(edge.target_id)
                if target:
                    deps.append(ServiceDependency(
                        target_service_id=target.id.replace("svc:", ""),
                    ))
        result.append(Service(
            id=sn.id.replace("svc:", ""),
            name=sn.label,
            operations=ops,
            dependencies=tuple(deps),
            is_stateless=sn.attributes.get("is_stateless", True),
        ))
    return result


def _graph_to_interfaces(graph: TypedGraph, mnode: GraphNode) -> list[Interface]:
    inodes = [n for n in graph.get_nodes_by_type(NodeType.INTERFACE) if n.parent_id == mnode.id]
    result = []
    for inn in inodes:
        epnodes = [n for n in graph.get_nodes_by_type(NodeType.ENDPOINT) if n.parent_id == inn.id]
        eps = tuple(
            Endpoint(
                id=f"ep-{i}",
                name=n.attributes.get("name", n.label),
                path=n.attributes.get("path", "/"),
                method=HttpMethod(n.attributes.get("method", "GET")),
            )
            for i, n in enumerate(epnodes)
        )
        secured_by = ""
        for edge in graph.get_outgoing_edges(inn.id):
            if edge.edge_type == EdgeType.SECURED_BY:
                target = graph.get_node(edge.target_id)
                if target:
                    secured_by = target.id.replace("pol:", "")
        result.append(Interface(
            id=inn.id.replace("iface:", ""),
            name=inn.label,
            interface_type=InterfaceType(inn.attributes.get("interface_type", "rest")),
            endpoints=eps,
            secured_by_policy_id=secured_by or None,
            is_internal=inn.attributes.get("is_internal", False),
        ))
    return result


def _graph_to_policies(graph: TypedGraph, mnode: GraphNode) -> list[Policy]:
    pnodes = [n for n in graph.get_nodes_by_type(NodeType.POLICY) if n.parent_id == mnode.id]
    return [
        Policy(
            id=n.id.replace("pol:", ""),
            name=n.label,
            policy_type=PolicyType(n.attributes.get("policy_type", "authentication")),
            strategy=n.attributes.get("strategy", ""),
        )
        for n in pnodes
    ]


def _graph_to_events(graph: TypedGraph, mnode: GraphNode) -> list[Event]:
    enodes = [n for n in graph.get_nodes_by_type(NodeType.EVENT) if n.parent_id == mnode.id]
    return [
        Event(
            id=n.id.replace("evt:", ""),
            name=n.label,
            pattern=EventPattern(n.attributes.get("pattern", "publish_subscribe")),
        )
        for n in enodes
    ]


def _graph_to_workflows(graph: TypedGraph, mnode: GraphNode) -> tuple:
    return ()


def _parse_field_type(raw: str) -> FieldType:
    mapping = {
        "uuid": FieldType.UUID, "string": FieldType.STRING, "text": FieldType.TEXT,
        "integer": FieldType.INTEGER, "int": FieldType.INTEGER, "float": FieldType.FLOAT,
        "decimal": FieldType.DECIMAL, "bool": FieldType.BOOLEAN, "boolean": FieldType.BOOLEAN,
        "datetime": FieldType.DATETIME, "date": FieldType.DATE, "email": FieldType.EMAIL,
        "json": FieldType.JSON,
    }
    return mapping.get(raw.lower(), FieldType.STRING)


def _parse_cardinality(raw: str) -> FieldCardinality:
    mapping = {"required": FieldCardinality.REQUIRED, "optional": FieldCardinality.OPTIONAL, "list": FieldCardinality.LIST}
    return mapping.get(raw.lower(), FieldCardinality.REQUIRED)


def _parse_coupling(dep_type: str):
    from constitutional_architecture.isr.model.edges import CouplingStrength
    return CouplingStrength.MODERATE
