from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


class GraphToISRConverter:
    def convert(self, graph: TypedGraph, parent: ISR) -> ISR:
        from constitutional_architecture.engine.isr_adapter import graph_to_isr as _convert
        return _convert(graph, parent)
