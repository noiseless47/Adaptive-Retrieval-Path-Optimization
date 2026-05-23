from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arpo.ingestion import ingest_path
from arpo.retrieval import Corpus


class IngestionTests(unittest.TestCase):
    def test_markdown_ingestion_creates_chunk_corpus_with_relations(self) -> None:
        body = " ".join(
            [
                "Transformer retrieval systems connect evidence graphs with confidence pruning."
                if index % 2 == 0
                else "Adaptive reranking improves multi hop question answering for scientific corpora."
                for index in range(70)
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "retrieval-notes.md"
            output = Path(temp_dir) / "corpus.jsonl"
            source.write_text(f"# Retrieval Notes\n\n{body}", encoding="utf-8")

            report = ingest_path(source, output, chunk_words=45, overlap_words=10, min_chunk_chars=0)
            corpus = Corpus.from_jsonl(output)

            self.assertEqual(report.source_documents, 1)
            self.assertGreater(len(corpus), 2)
            self.assertTrue(all(document.metadata["source_document_id"] == "retrieval-notes" for document in corpus.documents))
            self.assertTrue(any(document.metadata["related_ids"] for document in corpus.documents))

    def test_jsonl_ingestion_preserves_metadata_and_keywords(self) -> None:
        text = "Graph retrieval reduces hallucination by linking claims citations and confidence signals. " * 30

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "papers.jsonl"
            output = Path(temp_dir) / "ingested.jsonl"
            source.write_text(
                json.dumps(
                    {
                        "id": "paper-graph",
                        "title": "Graph Retrieval Study",
                        "text": text,
                        "metadata": {
                            "domain": "information retrieval",
                            "keywords": ["graph retrieval", "hallucination"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            ingest_path(source, output, chunk_words=50, overlap_words=10, min_chunk_chars=0)
            first = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

            self.assertEqual(first["metadata"]["domain"], "information retrieval")
            self.assertIn("graph retrieval", first["metadata"]["keywords"])
            self.assertEqual(first["metadata"]["source_document_id"], "paper-graph")


if __name__ == "__main__":
    unittest.main()
