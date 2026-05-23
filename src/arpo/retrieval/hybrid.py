from __future__ import annotations

from collections import defaultdict

from arpo.models import QueryGraph, RetrievalCandidate, RetrievalStrategy
from arpo.retrieval.corpus import Corpus
from arpo.retrieval.dense import DenseRetriever
from arpo.retrieval.sparse import BM25Retriever
from arpo.text import lexical_overlap, normalize_score, tokenize


class HybridRetriever:
    """Hybrid sparse+dense retriever with metadata graph expansion."""

    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.sparse = BM25Retriever(corpus)
        self.dense = DenseRetriever(corpus)

    def retrieve(self, graph: QueryGraph, strategy: RetrievalStrategy) -> list[RetrievalCandidate]:
        fused: dict[tuple[str, str], dict[str, object]] = {}
        query_terms = graph.terms()

        for intent in graph.intent_nodes():
            sub_query = intent.label
            sparse_hits = self.sparse.search(
                sub_query,
                top_k=strategy.per_hop_k,
                sub_query_id=intent.id,
            )
            dense_hits = self.dense.search(
                sub_query,
                top_k=strategy.per_hop_k,
                sub_query_id=intent.id,
            )
            for candidate in sparse_hits:
                self._accumulate(
                    fused,
                    candidate,
                    contribution=strategy.sparse_weight / (60 + candidate.rank),
                    feature_name="sparse_rrf",
                )
            for candidate in dense_hits:
                self._accumulate(
                    fused,
                    candidate,
                    contribution=strategy.dense_weight / (60 + candidate.rank),
                    feature_name="dense_rrf",
                )

        initial = self._materialize(fused)
        expanded = self._graph_expand(initial, graph, strategy, query_terms=query_terms)
        merged = self._merge_candidates([*initial, *expanded])
        return merged[: max(strategy.top_k * 4, strategy.per_hop_k)]

    def _graph_expand(
        self,
        candidates: list[RetrievalCandidate],
        graph: QueryGraph,
        strategy: RetrievalStrategy,
        *,
        query_terms: set[str],
    ) -> list[RetrievalCandidate]:
        expanded: list[RetrievalCandidate] = []
        seen = {candidate.document.id for candidate in candidates}
        frontier = candidates[: strategy.per_hop_k]

        for hop in range(1, strategy.max_hops):
            next_frontier: list[RetrievalCandidate] = []
            for candidate in frontier:
                for related in self.corpus.related(candidate.document):
                    if related.id in seen:
                        continue
                    overlap = lexical_overlap(query_terms, tokenize(f"{related.title} {related.text}"))
                    if overlap <= 0:
                        continue
                    score = candidate.score * (0.78**hop) + strategy.graph_weight * overlap
                    graph_candidate = RetrievalCandidate(
                        document=related,
                        score=score,
                        source="metadata_graph",
                        rank=len(expanded) + 1,
                        sub_query_id=candidate.sub_query_id,
                        explanation=f"Graph expansion from {candidate.document.id}",
                        features={
                            "graph_hop": hop,
                            "graph_overlap": overlap,
                            "parent_score": candidate.score,
                            "parent_id": candidate.document.id,
                        },
                    )
                    expanded.append(graph_candidate)
                    next_frontier.append(graph_candidate)
                    seen.add(related.id)
            frontier = next_frontier
            if not frontier:
                break

        return expanded

    @staticmethod
    def _accumulate(
        fused: dict[tuple[str, str], dict[str, object]],
        candidate: RetrievalCandidate,
        *,
        contribution: float,
        feature_name: str,
    ) -> None:
        key = (candidate.sub_query_id, candidate.document.id)
        record = fused.setdefault(
            key,
            {
                "candidate": candidate,
                "score": 0.0,
                "features": defaultdict(float),
                "sources": set(),
            },
        )
        record["score"] = float(record["score"]) + contribution
        features = record["features"]
        assert isinstance(features, defaultdict)
        features[feature_name] += contribution
        sources = record["sources"]
        assert isinstance(sources, set)
        sources.add(candidate.source)

    @staticmethod
    def _materialize(fused: dict[tuple[str, str], dict[str, object]]) -> list[RetrievalCandidate]:
        if not fused:
            return []
        scores = [float(record["score"]) for record in fused.values()]
        minimum, maximum = min(scores), max(scores)
        materialized = []
        for index, record in enumerate(fused.values(), start=1):
            base = record["candidate"]
            assert isinstance(base, RetrievalCandidate)
            features = dict(record["features"])
            sources = sorted(record["sources"])
            normalized = normalize_score(float(record["score"]), minimum, maximum)
            materialized.append(
                RetrievalCandidate(
                    document=base.document,
                    score=normalized,
                    source="+".join(sources),
                    rank=index,
                    sub_query_id=base.sub_query_id,
                    explanation="Reciprocal-rank fusion across sparse and dense retrievers",
                    features={**features, "fusion_score": float(record["score"])},
                )
            )
        materialized.sort(key=lambda candidate: candidate.score, reverse=True)
        return [
            RetrievalCandidate(
                document=candidate.document,
                score=candidate.score,
                source=candidate.source,
                rank=rank,
                sub_query_id=candidate.sub_query_id,
                explanation=candidate.explanation,
                features=candidate.features,
            )
            for rank, candidate in enumerate(materialized, start=1)
        ]

    @staticmethod
    def _merge_candidates(candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        by_doc: dict[str, RetrievalCandidate] = {}
        for candidate in candidates:
            current = by_doc.get(candidate.document.id)
            if current is None or candidate.score > current.score:
                by_doc[candidate.document.id] = candidate
        merged = list(by_doc.values())
        merged.sort(key=lambda candidate: candidate.score, reverse=True)
        return [
            RetrievalCandidate(
                document=candidate.document,
                score=candidate.score,
                source=candidate.source,
                rank=rank,
                sub_query_id=candidate.sub_query_id,
                explanation=candidate.explanation,
                features=candidate.features,
            )
            for rank, candidate in enumerate(merged, start=1)
        ]

    def diagnostics(self) -> dict[str, object]:
        return {
            "dense": self.dense.diagnostics(),
        }
