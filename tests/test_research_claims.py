from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arpo.evaluation.benchmarks import load_benchmark_records
from arpo.evaluation.claim_study import run_claim_study
from arpo.evaluation.statistics import paired_metric_test
from arpo.retrieval import Corpus


class ResearchClaimTests(unittest.TestCase):
    def test_paired_metric_test_reports_wins_and_ci(self) -> None:
        report = paired_metric_test([0.9, 0.8, 0.7], [0.5, 0.8, 0.4], bootstrap_samples=100)

        self.assertEqual(report["wins"], 2)
        self.assertEqual(report["ties"], 1)
        self.assertGreater(report["mean_delta"], 0)
        self.assertIn("p_value", report)

    def test_hotpotqa_loader_maps_supporting_facts_to_relevance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hotpot.json"
            path.write_text(
                json.dumps([
                    {
                        "_id": "q1",
                        "question": "Which paper connects graph retrieval and pruning?",
                        "supporting_facts": [["Graph Retrieval Paper", 0], ["Pruning Paper", 1]],
                    }
                ]),
                encoding="utf-8",
            )

            records, report = load_benchmark_records(path, benchmark="hotpotqa")

        self.assertEqual(report.name, "hotpotqa")
        self.assertEqual(records[0].id, "q1")
        self.assertEqual(records[0].relevant_ids, {"Graph Retrieval Paper", "Pruning Paper"})

    def test_claim_study_compares_variants(self) -> None:
        corpus = Corpus.from_jsonl("examples/corpus.jsonl")
        records, benchmark = load_benchmark_records("examples/queries.jsonl", benchmark="native")

        report = run_claim_study(
            corpus,
            records,
            top_k=3,
            variants=["full", "no_query_graph"],
            benchmark=benchmark,
            artifact_dir=None,
            corpus_path="examples/corpus.jsonl",
            queries_path="examples/queries.jsonl",
        )

        self.assertEqual(report["benchmark"]["query_count"], 3)
        self.assertEqual(len(report["comparisons"]), 1)
        self.assertEqual(report["comparisons"][0]["baseline_key"], "no_query_graph")
        self.assertGreaterEqual(len(report["claim_verdicts"]), 3)


if __name__ == "__main__":
    unittest.main()
