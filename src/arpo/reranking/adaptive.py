from __future__ import annotations

from arpo.models import EvidenceGraph, EvidenceNode, QueryAnalysis, RetrievalStrategy
from arpo.text import lexical_overlap, tokenize


class AdaptiveSemanticReranker:
    def rerank(
        self,
        graph: EvidenceGraph,
        query: str,
        analysis: QueryAnalysis,
        strategy: RetrievalStrategy,
    ) -> tuple[EvidenceNode, ...]:
        if strategy.reranking_mode == "diversity":
            return tuple(self._diverse(graph.nodes, query, strategy.top_k, strategy.diversity_lambda))

        scored = []
        for node in graph.nodes:
            score = self._score(node, query, analysis, graph)
            scored.append((score, node))
        scored.sort(key=lambda item: item[0], reverse=True)
        return tuple(node for _, node in scored[: strategy.top_k])

    def _score(
        self,
        node: EvidenceNode,
        query: str,
        analysis: QueryAnalysis,
        graph: EvidenceGraph,
    ) -> float:
        base = 0.48 * node.score + 0.38 * node.confidence
        overlap = lexical_overlap(tokenize(query), tokenize(f"{node.document.title} {node.document.text}"))
        graph_support = self._support_degree(node, graph)
        score = base + 0.08 * overlap + 0.06 * graph_support

        if "comparative" in analysis.query_type:
            score += 0.08 * self._comparative_signal(node)
            score -= 0.12 * float(node.features.get("contradiction_risk", 0.0))
        elif "causal" in analysis.query_type or "multi_hop" in analysis.query_type:
            score += 0.10 * graph_support
        elif analysis.reranking_policy == "precision":
            score += 0.05 * overlap

        return score

    @staticmethod
    def _support_degree(node: EvidenceNode, graph: EvidenceGraph) -> float:
        if not graph.edges:
            return 0.0
        connected = sum(1 for edge in graph.edges if edge.source == node.id or edge.target == node.id)
        return min(1.0, connected / max(1, len(graph.nodes) - 1))

    @staticmethod
    def _comparative_signal(node: EvidenceNode) -> float:
        terms = tokenize(f"{node.document.title} {node.document.text}", keep_stopwords=True)
        markers = {"compare", "compared", "versus", "replace", "replaced", "lower", "higher", "reduced"}
        return min(1.0, sum(1 for term in terms if term in markers) / 3)

    def _diverse(
        self,
        nodes: tuple[EvidenceNode, ...],
        query: str,
        top_k: int,
        diversity_lambda: float,
    ) -> list[EvidenceNode]:
        selected: list[EvidenceNode] = []
        remaining = list(nodes)
        query_terms = tokenize(query)

        while remaining and len(selected) < top_k:
            best_index = 0
            best_score = float("-inf")
            for index, node in enumerate(remaining):
                relevance = node.score + node.confidence + lexical_overlap(
                    query_terms,
                    tokenize(f"{node.document.title} {node.document.text}"),
                )
                redundancy = 0.0
                if selected:
                    redundancy = max(
                        lexical_overlap(
                            tokenize(f"{node.document.title} {node.document.text}"),
                            tokenize(f"{chosen.document.title} {chosen.document.text}"),
                        )
                        for chosen in selected
                    )
                score = (1 - diversity_lambda) * relevance - diversity_lambda * redundancy
                if score > best_score:
                    best_score = score
                    best_index = index
            selected.append(remaining.pop(best_index))
        return selected

