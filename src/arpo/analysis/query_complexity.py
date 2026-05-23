from __future__ import annotations

from arpo.models import QueryAnalysis
from arpo.text import clamp, tokenize


class QueryComplexityAnalyzer:
    """Deterministic query router with the same contract as a future ML classifier."""

    COMPARATIVE = {
        "compare",
        "compared",
        "versus",
        "vs",
        "replace",
        "replaced",
        "better",
        "worse",
        "lower",
        "higher",
        "while",
    }
    CAUSAL = {
        "because",
        "cause",
        "caused",
        "effect",
        "impact",
        "lead",
        "leads",
        "reduce",
        "reduced",
        "reduces",
        "why",
    }
    TEMPORAL = {"before", "after", "during", "when", "timeline", "trend", "evolution"}
    AMBIGUOUS = {"best", "recent", "latest", "strong", "important", "efficient", "robust"}
    MULTI_HOP = {
        "and",
        "while",
        "where",
        "with",
        "through",
        "linked",
        "between",
        "both",
        "multi-hop",
        "multihop",
    }

    def analyze(self, query: str) -> QueryAnalysis:
        all_tokens = tokenize(query, keep_stopwords=True)
        content_tokens = tokenize(query)
        token_count = max(1, len(content_tokens))

        comparative = self._ratio(all_tokens, self.COMPARATIVE)
        causal = self._ratio(all_tokens, self.CAUSAL)
        temporal = self._ratio(all_tokens, self.TEMPORAL)
        ambiguous = self._ratio(all_tokens, self.AMBIGUOUS)
        multi_hop = self._ratio(all_tokens, self.MULTI_HOP)

        connector_count = sum(1 for token in all_tokens if token in self.MULTI_HOP)
        entity_pressure = sum(1 for token in content_tokens if token.isupper())
        length_factor = clamp((token_count - 5) / 18)

        complexity = clamp(
            0.24
            + (0.25 * length_factor)
            + (0.20 * min(1.0, connector_count / 3))
            + (0.22 * comparative)
            + (0.15 * causal)
            + (0.10 * temporal)
        )
        ambiguity_score = clamp(0.12 + ambiguous + (0.08 if token_count < 4 else 0.0))

        required_hops = 1
        if complexity > 0.45 or connector_count:
            required_hops += 1
        if complexity > 0.72 or comparative > 0.15 or causal > 0.12:
            required_hops += 1
        if token_count > 16:
            required_hops += 1
        required_hops = min(4, required_hops)

        query_type = self._query_type(
            comparative=comparative,
            causal=causal,
            temporal=temporal,
            ambiguity=ambiguity_score,
            hops=required_hops,
        )
        retrieval_mode, reranking_policy = self._routing(query_type, required_hops, ambiguity_score)

        return QueryAnalysis(
            query_type=query_type,
            complexity_score=round(complexity, 3),
            ambiguity_score=round(ambiguity_score, 3),
            required_hops=required_hops,
            retrieval_mode=retrieval_mode,
            reranking_policy=reranking_policy,
            signals={
                "comparative": round(comparative, 3),
                "causal": round(causal, 3),
                "temporal": round(temporal, 3),
                "multi_hop": round(multi_hop, 3),
                "multi_hop_markers": connector_count,
                "entity_pressure": entity_pressure,
                "content_token_count": token_count,
            },
        )

    @staticmethod
    def _ratio(tokens: list[str], vocabulary: set[str]) -> float:
        if not tokens:
            return 0.0
        hits = sum(1 for token in tokens if token in vocabulary)
        return hits / max(1, len(tokens))

    @staticmethod
    def _query_type(
        *,
        comparative: float,
        causal: float,
        temporal: float,
        ambiguity: float,
        hops: int,
    ) -> str:
        suffix = "_multi_hop" if hops >= 2 else ""
        if comparative > 0.06:
            return f"comparative{suffix}"
        if causal > 0.05:
            return f"causal{suffix}"
        if temporal > 0.05:
            return f"temporal{suffix}"
        if ambiguity > 0.28:
            return f"ambiguous{suffix or '_semantic'}"
        if hops >= 2:
            return "multi_hop"
        return "factual"

    @staticmethod
    def _routing(query_type: str, hops: int, ambiguity: float) -> tuple[str, str]:
        if "comparative" in query_type:
            return "hybrid_graph_dense", "contradiction_aware"
        if "causal" in query_type or "multi_hop" in query_type:
            return "staged_graph_retrieval", "dependency_aware"
        if "ambiguous" in query_type or ambiguity > 0.35:
            return "diversified_hybrid", "diversity"
        if hops <= 1:
            return "bm25_precision", "precision"
        return "hybrid_balanced", "precision"
