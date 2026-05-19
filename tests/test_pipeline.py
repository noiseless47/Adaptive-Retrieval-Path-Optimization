from __future__ import annotations

import unittest
from pathlib import Path

from arpo.analysis import QueryComplexityAnalyzer
from arpo.evaluation import evaluate_pipeline, load_query_records, ndcg_at_k, precision_at_k, recall_at_k
from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus


ROOT = Path(__file__).resolve().parents[1]


class QueryAnalyzerTests(unittest.TestCase):
    def test_comparative_query_routes_to_graph_dense(self) -> None:
        analysis = QueryComplexityAnalyzer().analyze(
            "Papers where transformers replaced CNNs in medical imaging while reducing inference cost"
        )

        self.assertIn("comparative", analysis.query_type)
        self.assertGreaterEqual(analysis.required_hops, 2)
        self.assertEqual(analysis.retrieval_mode, "hybrid_graph_dense")


class PipelineTests(unittest.TestCase):
    def test_pipeline_returns_grounded_evidence(self) -> None:
        corpus = Corpus.from_jsonl(ROOT / "examples" / "corpus.jsonl")
        pipeline = ARPOPipeline.from_corpus(corpus)

        result = pipeline.run(
            "Papers where transformers replaced CNNs in medical imaging while reducing inference cost",
            top_k=3,
        )

        self.assertGreaterEqual(len(result.ranked_evidence), 2)
        retrieved_ids = {node.document.id for node in result.ranked_evidence}
        self.assertTrue({"paper-001", "paper-002"} & retrieved_ids)
        self.assertIn("Grounded answer", result.answer)
        self.assertGreaterEqual(result.diagnostics["evidence_nodes_after_pruning"], 2)

    def test_evaluation_metrics(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = {"b", "d"}

        self.assertAlmostEqual(precision_at_k(retrieved, relevant, 2), 0.5)
        self.assertAlmostEqual(recall_at_k(retrieved, relevant, 3), 0.5)
        self.assertGreater(ndcg_at_k(retrieved, {"a": 1.0, "b": 2.0}, 2), 0.0)

    def test_evaluation_runner(self) -> None:
        corpus = Corpus.from_jsonl(ROOT / "examples" / "corpus.jsonl")
        records = load_query_records(ROOT / "examples" / "queries.jsonl")

        report = evaluate_pipeline(corpus, records, top_k=3)

        self.assertEqual(report["query_count"], 3)
        self.assertGreaterEqual(report["recall_at_k"], 0.8)


if __name__ == "__main__":
    unittest.main()
