from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arpo.models import Document
from arpo.retrieval.corpus import Corpus
from arpo.retrieval.dense import DenseRetriever
from arpo.retrieval.embeddings import HashEmbeddingBackend
from arpo.retrieval.vector_index import PersistentVectorIndex


class VectorIndexTests(unittest.TestCase):
    def test_persistent_vector_index_round_trips_from_cache(self) -> None:
        corpus = Corpus(
            [
                Document("d1", "Graph Retrieval", "Graph retrieval links evidence paths."),
                Document("d2", "Dense Retrieval", "Embeddings retrieve semantically similar text."),
            ]
        )
        backend = HashEmbeddingBackend(dimensions=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            first = PersistentVectorIndex.from_corpus(corpus, backend, index_dir=temp_dir)
            second = PersistentVectorIndex.from_corpus(corpus, backend, index_dir=temp_dir)

            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(len(second.records), 2)
            self.assertTrue(Path(second.index_path or "").is_file())

    def test_dense_retriever_uses_embedding_index(self) -> None:
        corpus = Corpus(
            [
                Document("d1", "Confidence Pruning", "Confidence pruning removes noisy retrieval branches."),
                Document("d2", "CNN Baseline", "CNN baselines classify radiology images."),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            retriever = DenseRetriever(
                corpus,
                backend=HashEmbeddingBackend(dimensions=64),
                index_dir=temp_dir,
            )
            hits = retriever.search(
                "retrieval confidence pruning",
                top_k=1,
                sub_query_id="query-root",
            )

            self.assertEqual(hits[0].document.id, "d1")
            self.assertEqual(retriever.diagnostics()["embedding_backend"], "hash")


if __name__ == "__main__":
    unittest.main()
