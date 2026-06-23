from __future__ import annotations

import importlib.util
import time
import unittest
from pathlib import Path

import arpo.api.main as api_main
from arpo.api.main import app


HAS_TEST_CLIENT = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(app is not None and HAS_TEST_CLIENT, "FastAPI test dependencies are not installed")
class ApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from fastapi.testclient import TestClient

        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("x-request-id", response.headers)

        prefixed = self.client.get("/api/health")
        self.assertEqual(prefixed.status_code, 200)
        self.assertEqual(prefixed.json(), {"status": "ok"})

        healthz = self.client.get("/api/healthz")
        self.assertEqual(healthz.status_code, 200)
        self.assertTrue(healthz.json()["data_dir"].endswith("data"))

    def test_search_returns_pipeline_contract(self) -> None:
        response = self.client.post(
            "/api/search",
            json={
                "query": "Papers where transformers replaced CNNs in medical imaging",
                "top_k": 3,
                "corpus_path": "examples/corpus.jsonl",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("analysis", payload)
        self.assertIn("query_graph", payload)
        self.assertIn("evidence_graph", payload)
        self.assertIn("latency_ms", payload["diagnostics"])
        self.assertIn("run_id", payload["diagnostics"])
        self.assertIn("evidence_audit", payload["diagnostics"])

        run_response = self.client.get(f"/api/runs/{payload['diagnostics']['run_id']}")
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(run_response.json()["run_type"], "search")

    def test_search_rejects_paths_outside_allowed_roots(self) -> None:
        response = self.client.post(
            "/search",
            json={
                "query": "valid query text",
                "corpus_path": "../outside.jsonl",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("examples or data", response.json()["detail"])

    def test_corpora_endpoint_lists_only_searchable_corpora(self) -> None:
        response = self.client.get("/api/corpora")

        self.assertEqual(response.status_code, 200)
        corpora = response.json()["corpora"]
        ids = {item["id"] for item in corpora}
        paths = {item["path"] for item in corpora}

        self.assertIn("corpus.jsonl", ids)
        self.assertIn("arpo-openalex-corpus.jsonl", ids)
        self.assertNotIn("queries.jsonl", ids)
        self.assertNotIn("arpo-openalex-queries.jsonl", ids)
        self.assertNotIn("examples/queries.jsonl", paths)
        self.assertTrue(all(item["documents"] > 0 for item in corpora))

        stats_response = self.client.get(
            "/api/corpora/stats",
            params={"corpus_path": "data/arpo-openalex-corpus.jsonl"},
        )
        self.assertEqual(stats_response.status_code, 200)
        self.assertGreater(stats_response.json()["quality"]["document_count"], 100)

    def test_suggest_returns_corpus_derived_retrieval_briefs(self) -> None:
        response = self.client.get(
            "/api/suggest",
            params={
                "q": "hallucination",
                "corpus_path": "data/arpo-openalex-corpus.jsonl",
                "limit": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        suggestions = response.json()["suggestions"]
        self.assertGreaterEqual(len(suggestions), 1)
        self.assertTrue(any("hallucination" in item["text"].lower() for item in suggestions))
        self.assertTrue(all(item["text"][0].isupper() for item in suggestions))
        self.assertTrue(all("_" not in item["text"] for item in suggestions))

    def test_ablation_returns_real_variant_metrics(self) -> None:
        response = self.client.post(
            "/api/ablation",
            json={
                "corpus_path": "examples/corpus.jsonl",
                "queries_path": "examples/queries.jsonl",
                "top_k": 3,
                "variants": ["full", "no_query_graph", "sparse_only"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["query_count"], 3)
        self.assertEqual([item["variant"] for item in payload["results"]], ["Full ARPO", "No Query Graph", "Sparse Only"])
        self.assertTrue(all("latency_ms" in item for item in payload["results"]))

    def test_claim_study_returns_research_comparisons_and_artifacts(self) -> None:
        response = self.client.post(
            "/api/research/claim-study",
            json={
                "corpus_path": "examples/corpus.jsonl",
                "queries_path": "examples/queries.jsonl",
                "top_k": 3,
                "benchmark": "native",
                "variants": ["full", "no_query_graph", "fixed_hybrid"],
                "output_dir": "data/experiments",
            },
        )

        try:
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["benchmark"]["name"], "native")
            self.assertEqual(payload["benchmark"]["query_count"], 3)
            self.assertEqual(len(payload["comparisons"]), 2)
            self.assertGreaterEqual(len(payload["claim_verdicts"]), 3)
            self.assertIn("paired_significance", payload["comparisons"][0])
            self.assertIn("markdown", payload["artifacts"])
            self.assertIn("run_id", payload)
        finally:
            if response.status_code == 200:
                for artifact_path in response.json().get("artifacts", {}).values():
                    path = Path(artifact_path)
                    if path.exists():
                        path.unlink()

    def test_evaluation_job_completes_and_persists_run(self) -> None:
        response = self.client.post(
            "/api/jobs/evaluate",
            json={
                "corpus_path": "examples/corpus.jsonl",
                "queries_path": "examples/queries.jsonl",
                "top_k": 3,
            },
        )

        self.assertEqual(response.status_code, 200)
        job_id = response.json()["id"]
        job = None
        for _ in range(30):
            job_response = self.client.get(f"/api/jobs/{job_id}")
            self.assertEqual(job_response.status_code, 200)
            job = job_response.json()
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["query_count"], 3)
        self.assertIsNotNone(job["run_id"])

    def test_optional_api_key_protects_api_routes(self) -> None:
        original_keys = set(api_main.API_KEYS)
        api_main.API_KEYS.clear()
        api_main.API_KEYS.add("test-key")
        try:
            blocked = self.client.get("/api/corpora")
            self.assertEqual(blocked.status_code, 401)

            allowed = self.client.get("/api/corpora", headers={"x-api-key": "test-key"})
            self.assertEqual(allowed.status_code, 200)
        finally:
            api_main.API_KEYS.clear()
            api_main.API_KEYS.update(original_keys)

    def test_ingest_corpus_endpoint_creates_searchable_jsonl(self) -> None:
        source = (
            "# Retrieval Notes\n\n"
            + "Graph retrieval connects claims with confidence pruning and adaptive reranking. " * 80
        )
        response = self.client.post(
            "/api/corpora/ingest",
            files={"file": ("api-ingest-test.md", source.encode("utf-8"), "text/markdown")},
            data={"chunk_words": "50", "overlap_words": "10", "min_chunk_chars": "0"},
        )

        try:
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertGreater(payload["documents"], 1)
            self.assertTrue(payload["path"].startswith("data/"))

            search_response = self.client.post(
                "/api/search",
                json={
                    "query": "graph retrieval confidence pruning",
                    "top_k": 3,
                    "corpus_path": payload["path"],
                },
            )
            self.assertEqual(search_response.status_code, 200)
            self.assertGreaterEqual(len(search_response.json()["ranked_evidence"]), 1)
        finally:
            if response.status_code == 200:
                generated = Path(response.json()["path"])
                if generated.exists():
                    generated.unlink()


if __name__ == "__main__":
    unittest.main()
