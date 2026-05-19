from __future__ import annotations

from arpo.analysis import QueryComplexityAnalyzer
from arpo.evidence import EvidenceGraphBuilder
from arpo.generation import EvidenceGroundedAnswerGenerator
from arpo.graph import DynamicQueryGraphBuilder
from arpo.models import PipelineResult
from arpo.planning import RetrievalStrategyPlanner
from arpo.pruning import ConfidencePruner
from arpo.reranking import AdaptiveSemanticReranker
from arpo.retrieval import Corpus, HybridRetriever


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

    def run(self, query: str, *, top_k: int = 5) -> PipelineResult:
        analysis = self.analyzer.analyze(query)
        query_graph = self.graph_builder.build(query, analysis)
        strategy = self.planner.plan(analysis, top_k=top_k)
        candidates = self.retriever.retrieve(query_graph, strategy)
        evidence_graph = self.evidence_builder.build(candidates, query, query_graph)
        pruned_graph = self.pruner.prune(evidence_graph, strategy)
        ranked_evidence = self.reranker.rerank(pruned_graph, query, analysis, strategy)
        answer = self.generator.generate(query, analysis, ranked_evidence)

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
            },
        )

