from __future__ import annotations

from constitutional_architecture.compiler.bir.model import BIR, BIRModule, BIRNode, BIRNodeType
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult


class LoweringPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "lowering"

    @property
    def description(self) -> str:
        return "Lower ISR to Backend Intermediate Representation (BIR)"

    @property
    def dependencies(self) -> list[str]:
        return ["capability_resolution"]

    @property
    def input_requirements(self) -> set[str]:
        return {"capabilities_resolved"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"bir_available"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        isr = ctx.isr
        modules = []

        for module in isr.system.modules:
            nodes = []
            for entity in module.entities:
                nodes.append(BIRNode(
                    id=f"ent:{entity.id}", node_type=BIRNodeType.ENTITY,
                    name=entity.name,
                    attributes={"fields": [f.name for f in entity.fields]},
                ))
            for service in module.services:
                handler_nodes = []
                for op in service.operations:
                    handler_nodes.append(BIRNode(
                        id=f"handler:{op.id}", node_type=BIRNodeType.HANDLER,
                        name=op.name, attributes={"operation_type": op.operation_type.value},
                    ))
                nodes.append(BIRNode(
                    id=f"svc:{service.id}", node_type=BIRNodeType.SERVICE,
                    name=service.name, children=tuple(handler_nodes),
                ))
            modules.append(BIRModule(id=module.id, name=module.name, nodes=tuple(nodes)))

        bir = BIR(project_name=isr.system.name, modules=tuple(modules))
        ctx.bir = bir

        ctx.diagnostics.info("COMP-LOW-001", f"Lowered {len(modules)} module(s) to BIR")
        return PassResult(success=True, description=f"Lowered {len(modules)} modules to BIR",
                          metrics={"modules": len(modules), "bir_nodes": sum(len(m.nodes) for m in modules)})
