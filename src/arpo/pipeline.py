from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from arpo.analysis import QueryComplexityAnalyzer
from arpo.evidence import EvidenceGraphBuilder
from arpo.evaluation.metrics import evidence_audit
from arpo.generation import EvidenceGroundedAnswerGenerator
from arpo.graph import DynamicQueryGraphBuilder
from arpo.models import PipelineResult, QueryAnalysis, QueryGraph, QueryGraphNode, RetrievalStrategy
from arpo.planning import RetrievalStrategyPlanner
from arpo.pruning import ConfidencePruner
from arpo.reranking import AdaptiveSemanticReranker
from arpo.retrieval import Corpus, HybridRetriever
from arpo.text import tokenize


StrategyFactory = Callable[[QueryAnalysis, int], RetrievalStrategy]


class ARPOPipeline:
    def __init__(
        self,
        *,
        analyzer: QueryComplexityAnalyzer,
        graph_builder: DynamicQueryGraphBuilder,
        planner: RetrievalStrategyPlanner,
        retriever: HybridRetriever,
        evidence_builder: EvidenceGraphBuilder,
        pruner: ConfidencePruner,
        reranker: AdaptiveSemanticReranker,
        generator: EvidenceGroundedAnswerGenerator,
    ):
        self.analyzer = analyzer
        self.graph_builder = graph_builder
        self.planner = planner
        self.retriever = retriever
        self.evidence_builder = evidence_builder
        self.pruner = pruner
        self.reranker = reranker
        self.generator = generator

    @classmethod
    def from_corpus(cls, corpus: Corpus) -> "ARPOPipeline":
        return cls(
            analyzer=QueryComplexityAnalyzer(),
            graph_builder=DynamicQueryGraphBuilder(),
            planner=RetrievalStrategyPlanner(),
            retriever=HybridRetriever(corpus),
            evidence_builder=EvidenceGraphBuilder(),
            pruner=ConfidencePruner(),
            reranker=AdaptiveSemanticReranker(),
            generator=EvidenceGroundedAnswerGenerator(),
        )

    def run(
        self,
        query: str,
        *,
        top_k: int = 5,
        strategy_override: RetrievalStrategy | None = None,
        strategy_factory: StrategyFactory | None = None,
        disable_query_graph: bool = False,
    ) -> PipelineResult:
        if strategy_override is not None and strategy_factory is not None:
            raise ValueError("Use either strategy_override or strategy_factory, not both.")

        total_start = perf_counter()
        timings: dict[str, float] = {}

        stage_start = perf_counter()
        analysis = self.analyzer.analyze(query)
        timings["analysis_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        query_graph = (
            _root_only_query_graph(query)
            if disable_query_graph
            else self.graph_builder.build(query, analysis)
        )
        timings["query_graph_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        if strategy_override is not None:
            strategy = strategy_override
        elif strategy_factory is not None:
            strategy = strategy_factory(analysis, top_k)
        else:
            strategy = self.planner.plan(analysis, top_k=top_k)
        timings["strategy_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        candidates = self.retriever.retrieve(query_graph, strategy)
        timings["retrieval_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        evidence_graph = self.evidence_builder.build(candidates, query, query_graph)
        timings["evidence_graph_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        pruned_graph = self.pruner.prune(evidence_graph, strategy)
        timings["pruning_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        ranked_evidence = self.reranker.rerank(pruned_graph, query, analysis, strategy)
        timings["reranking_ms"] = _elapsed_ms(stage_start)

        stage_start = perf_counter()
        answer = self.generator.generate(query, analysis, ranked_evidence)
        timings["generation_ms"] = _elapsed_ms(stage_start)

        return PipelineResult(
            query=query,
            analysis=analysis,
            query_graph=query_graph,
            strategy=strategy,
            evidence_graph=pruned_graph,
            ranked_evidence=ranked_evidence,
            answer=answer,
            diagnostics={
                "candidate_count": len(candidates),
                "evidence_nodes_before_pruning": len(evidence_graph.nodes),
                "evidence_nodes_after_pruning": len(pruned_graph.nodes),
                "evidence_edges_after_pruning": len(pruned_graph.edges),
                "latency_ms": _elapsed_ms(total_start),
                "stage_timings_ms": timings,
                "query_graph_enabled": not disable_query_graph,
                "retriever": self.retriever.diagnostics(),
                "evidence_audit": evidence_audit(ranked_evidence),
            },
        )


def _root_only_query_graph(query: str) -> QueryGraph:
    return QueryGraph(
        nodes=(
            QueryGraphNode(
                id="query-root",
                label=query,
                kind="root",
                weight=1.0,
                terms=tuple(tokenize(query)),
            ),
        ),
        edges=(),
        root_id="query-root",
    )


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)
