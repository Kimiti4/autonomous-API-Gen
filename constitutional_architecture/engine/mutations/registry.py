from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.engine.mutations.split_module import SplitModuleMutation
from constitutional_architecture.engine.mutations.merge_services import MergeServicesMutation
from constitutional_architecture.engine.mutations.extract_interface import ExtractInterfaceMutation
from constitutional_architecture.engine.mutations.add_cache import AddCacheMutation
from constitutional_architecture.engine.mutations.introduce_event_bus import IntroduceEventBusMutation
from constitutional_architecture.engine.mutations.replace_auth_strategy import ReplaceAuthStrategyMutation
from constitutional_architecture.isr.model.isr import ISR


class ConcreteMutationRegistry:
    def __init__(self) -> None:
        self._operators: dict[str, MutationOperator] = {}

    def register(self, operator: MutationOperator) -> None:
        self._operators[operator.identifier] = operator

    def get(self, identifier: str) -> MutationOperator | None:
        return self._operators.get(identifier)

    def apply(self, identifier: str, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        op = self.get(identifier)
        if op is None:
            raise KeyError(f"Unknown mutation operator: {identifier}")
        return op.apply(isr, target_id, params)

    @property
    def identifiers(self) -> list[str]:
        return list(self._operators.keys())

    @property
    def count(self) -> int:
        return len(self._operators)


def get_default_registry() -> ConcreteMutationRegistry:
    reg = ConcreteMutationRegistry()
    reg.register(SplitModuleMutation())
    reg.register(MergeServicesMutation())
    reg.register(ExtractInterfaceMutation())
    reg.register(AddCacheMutation())
    reg.register(IntroduceEventBusMutation())
    reg.register(ReplaceAuthStrategyMutation())
    return reg
