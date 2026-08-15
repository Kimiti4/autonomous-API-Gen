from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


class ISRToGraphConverter:
    def convert(self, isr: ISR) -> TypedGraph:
        from constitutional_architecture.engine.isr_adapter import isr_to_graph as _convert
        return _convert(isr)
