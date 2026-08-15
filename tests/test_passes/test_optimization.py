import pytest

from constitutional_architecture.compiler.compilation_config import CompilationConfig, OptimizationLevel
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.optimization_pass import OptimizationPass
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import ServiceDependency
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.workflow import StateType, Workflow, WorkflowState, WorkflowTransition


def _create_isr_with_unreachable_state() -> ISR:
    return ISR(
        system=System(
            id="shop", name="Shop",
            modules=(
                Module(
                    id="mod-orders", name="Orders",
                    workflows=(
                        Workflow(
                            id="wf-order", name="OrderLifecycle",
                            states=(
                                WorkflowState(id="s1", name="Pending", state_type=StateType.INITIAL),
                                WorkflowState(id="s2", name="Confirmed", state_type=StateType.INTERMEDIATE),
                                WorkflowState(id="s3", name="Orphaned", state_type=StateType.INTERMEDIATE),
                            ),
                            transitions=(
                                WorkflowTransition(id="t1", name="confirm", from_state_id="s1", to_state_id="s2"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _create_isr_with_duplicate_deps() -> ISR:
    return ISR(
        system=System(
            id="shop", name="Shop",
            modules=(
                Module(
                    id="mod-orders", name="Orders",
                    dependencies=("mod-auth", "mod-auth", "mod-payments"),
                    services=(
                        Service(id="svc-orders", name="OrderService",
                                operations=(),
                                dependencies=(
                                    ServiceDependency(target_service_id="svc-auth"),
                                    ServiceDependency(target_service_id="svc-auth"),
                                    ServiceDependency(target_service_id="svc-payments"),
                                )),
                    ),
                ),
            ),
        ),
    )


class TestOptimizationPass:
    def test_removes_unreachable_states(self):
        isr = _create_isr_with_unreachable_state()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",), optimization_level=OptimizationLevel.STANDARD)
        ctx = CompilerContext(_isr=isr, _config=config)
        OptimizationPass().execute(ctx)
        workflow = ctx.isr.system.modules[0].workflows[0]
        state_names = {s.name for s in workflow.states}
        assert "Orphaned" not in state_names
        assert "Pending" in state_names
        assert "Confirmed" in state_names

    def test_removes_duplicate_dependencies(self):
        isr = _create_isr_with_duplicate_deps()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",), optimization_level=OptimizationLevel.STANDARD)
        ctx = CompilerContext(_isr=isr, _config=config)
        OptimizationPass().execute(ctx)
        module = ctx.isr.system.modules[0]
        assert len(module.dependencies) == 2
        assert module.dependencies.count("mod-auth") == 1
        svc = module.services[0]
        assert len(svc.dependencies) == 2

    def test_no_optimization_at_level_none(self):
        isr = _create_isr_with_duplicate_deps()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",), optimization_level=OptimizationLevel.NONE)
        ctx = CompilerContext(_isr=isr, _config=config)
        result = OptimizationPass().execute(ctx)
        assert result.metrics["optimizations_applied"] == 0

    def test_preserves_semantics(self):
        isr = _create_isr_with_unreachable_state()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",), optimization_level=OptimizationLevel.STANDARD)
        ctx = CompilerContext(_isr=isr, _config=config)
        OptimizationPass().execute(ctx)
        workflow = ctx.isr.system.modules[0].workflows[0]
        initial = [s for s in workflow.states if s.state_type == StateType.INITIAL]
        assert len(initial) == 1
        assert len(workflow.transitions) == 1
