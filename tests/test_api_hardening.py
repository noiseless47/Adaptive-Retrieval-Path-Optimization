from __future__ import annotations

import unittest
from pathlib import Path

from arpo.api.main import (
    ALLOWED_ABLATION_VARIANTS,
    _ablation_controls,
    _resolve_jsonl_path,
    _safe_source_filename,
    _safe_upload_filename,
)
from arpo.analysis import QueryComplexityAnalyzer
from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus


ROOT = Path(__file__).resolve().parents[1]


class ApiHardeningTests(unittest.TestCase):
    def test_resolve_jsonl_path_allows_project_data_roots_only(self) -> None:
        resolved = _resolve_jsonl_path("examples/corpus.jsonl", must_exist=True)

        self.assertEqual(resolved, (ROOT / "examples" / "corpus.jsonl").resolve())

        with self.assertRaisesRegex(ValueError, "examples or data"):
            _resolve_jsonl_path("../outside.jsonl", must_exist=False)

        with self.assertRaisesRegex(ValueError, "Only .jsonl"):
            _resolve_jsonl_path("examples/corpus.txt", must_exist=False)

    def test_safe_upload_filename_rejects_traversal_and_invalid_types(self) -> None:
        self.assertEqual(_safe_upload_filename("research-corpus_01.jsonl"), "research-corpus_01.jsonl")

        for filename in ("../evil.jsonl", "..\\evil.jsonl", "corpus.txt", ".hidden.jsonl", ""):
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    _safe_upload_filename(filename)

    def test_safe_source_filename_allows_ingestion_sources_only(self) -> None:
        self.assertEqual(_safe_source_filename("research-notes.md"), "research-notes.md")
        self.assertEqual(_safe_source_filename("papers.json"), "papers.json")

        for filename in ("../evil.md", "source.exe", ".hidden.md", ""):
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    _safe_source_filename(filename)

    def test_ablation_controls_cover_declared_variants(self) -> None:
        analysis = QueryComplexityAnalyzer().analyze("Compare sparse and dense retrieval for multi-hop QA")

        for variant in ALLOWED_ABLATION_VARIANTS:
            with self.subTest(variant=variant):
                strategy_factory, disable_query_graph = _ablation_controls(variant)
                strategy = strategy_factory(analysis, 5)
                self.assertGreaterEqual(strategy.top_k, 1)
                self.assertIsInstance(disable_query_graph, bool)


class PipelineDiagnosticsTests(unittest.TestCase):
    def test_pipeline_reports_latency_and_query_graph_mode(self) -> None:
        corpus = Corpus.from_jsonl(ROOT / "examples" / "corpus.jsonl")
        pipeline = ARPOPipeline.from_corpus(corpus)

        result = pipeline.run("How do graph retrieval systems reduce hallucination?", top_k=3)

        self.assertIn("latency_ms", result.diagnostics)
        self.assertIn("stage_timings_ms", result.diagnostics)
        self.assertGreaterEqual(result.diagnostics["latency_ms"], 0)
        self.assertTrue(result.diagnostics["query_graph_enabled"])


if __name__ == "__main__":
    unittest.main()
