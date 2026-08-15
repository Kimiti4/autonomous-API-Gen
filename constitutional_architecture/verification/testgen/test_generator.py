from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class GeneratedTest:
    test_id: str
    name: str
    category: str
    description: str = ""
    target_isr_node_id: str = ""
    test_code: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class TestGenerator:
    def generate(self, isr: ISR) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        tests.extend(self._generate_entity_tests(isr))
        tests.extend(self._generate_service_tests(isr))
        tests.extend(self._generate_interface_tests(isr))
        tests.extend(self._generate_workflow_tests(isr))
        return tests

    def _generate_entity_tests(self, isr: ISR) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        for module in isr.system.modules:
            for entity in module.entities:
                tests.append(GeneratedTest(
                    test_id=f"test-entity-{entity.id}",
                    name=f"test_{entity.name.lower()}_creation",
                    category="unit",
                    description=f"Verify {entity.name} can be created with required fields",
                    target_isr_node_id=entity.id,
                    test_code=self._entity_test_template(entity.name, entity.fields),
                ))
        return tests

    def _generate_service_tests(self, isr: ISR) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        for module in isr.system.modules:
            for service in module.services:
                for op in service.operations:
                    tests.append(GeneratedTest(
                        test_id=f"test-op-{op.id}",
                        name=f"test_{op.name}",
                        category="integration",
                        description=f"Verify {service.name}.{op.name} operation",
                        target_isr_node_id=op.id,
                    ))
        return tests

    def _generate_interface_tests(self, isr: ISR) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        for module in isr.system.modules:
            for iface in module.interfaces:
                for endpoint in iface.endpoints:
                    tests.append(GeneratedTest(
                        test_id=f"test-ep-{endpoint.id}",
                        name=f"test_{endpoint.method.value}_{endpoint.path.replace('/', '_')}",
                        category="contract",
                        description=f"Verify {endpoint.method.value} {endpoint.path}",
                        target_isr_node_id=endpoint.id,
                    ))
        return tests

    def _generate_workflow_tests(self, isr: ISR) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        for module in isr.system.modules:
            for workflow in module.workflows:
                tests.append(GeneratedTest(
                    test_id=f"test-wf-{workflow.id}",
                    name=f"test_{workflow.name.lower()}_transitions",
                    category="integration",
                    description=f"Verify {workflow.name} state transitions",
                    target_isr_node_id=workflow.id,
                ))
        return tests

    def _entity_test_template(self, name: str, fields) -> str:
        field_names = [f.name for f in fields[:5]]
        return f'''
def test_{name.lower()}_creation():
    """Verify {name} entity creation."""
    # Generated verification test
    # Fields: {", ".join(field_names)}
    pass
'''
