from __future__ import annotations

from arpo.models import EvidenceGraph, RetrievalStrategy


class ConfidencePruner:
    """Remove weak evidence branches while keeping a minimum viable context."""

    def prune(self, graph: EvidenceGraph, strategy: RetrievalStrategy) -> EvidenceGraph:
        if not graph.nodes:
            return graph

        sorted_nodes = sorted(graph.nodes, key=lambda node: node.confidence, reverse=True)
        minimum_keep = min(len(sorted_nodes), 2)
        kept = [node for node in sorted_nodes if node.confidence >= strategy.pruning_threshold]

        if len(kept) < minimum_keep:
            kept = sorted_nodes[:minimum_keep]

        kept_ids = {node.id for node in kept}
        kept_edges = [
            edge for edge in graph.edges if edge.source in kept_ids and edge.target in kept_ids
        ]
        return EvidenceGraph(nodes=tuple(kept), edges=tuple(kept_edges))
