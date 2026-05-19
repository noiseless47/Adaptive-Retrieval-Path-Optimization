from __future__ import annotations

from arpo.models import QueryAnalysis, RetrievalStrategy


class RetrievalStrategyPlanner:
    """Map query analysis to retrieval controls."""

    def plan(self, analysis: QueryAnalysis, *, top_k: int = 8) -> RetrievalStrategy:
        mode = analysis.retrieval_mode
        hops = max(1, analysis.required_hops)

        if mode == "bm25_precision":
            weights = (0.72, 0.22, 0.06)
            per_hop_k = max(top_k, 8)
            pruning = 0.38
            diversity = 0.15
        elif mode == "hybrid_graph_dense":
            weights = (0.30, 0.45, 0.25)
            per_hop_k = max(top_k + 4, 10)
            pruning = 0.44
            diversity = 0.25
        elif mode == "staged_graph_retrieval":
            weights = (0.28, 0.36, 0.36)
            per_hop_k = max(top_k + 6, 12)
            pruning = 0.42
            diversity = 0.22
        elif mode == "diversified_hybrid":
            weights = (0.34, 0.38, 0.28)
            per_hop_k = max(top_k + 8, 14)
            pruning = 0.34
            diversity = 0.48
        else:
            weights = (0.44, 0.42, 0.14)
            per_hop_k = max(top_k + 2, 8)
            pruning = 0.40
            diversity = 0.20

        return RetrievalStrategy(
            strategy_id=mode,
            sparse_weight=weights[0],
            dense_weight=weights[1],
            graph_weight=weights[2],
            top_k=top_k,
            per_hop_k=per_hop_k,
            max_hops=hops,
            pruning_threshold=pruning,
            diversity_lambda=diversity,
            reranking_mode=analysis.reranking_policy,
        )

