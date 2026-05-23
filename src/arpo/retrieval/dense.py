from __future__ import annotations

from pathlib import Path

from arpo.models import RetrievalCandidate
from arpo.retrieval.corpus import Corpus
from arpo.retrieval.embeddings import EmbeddingBackend, HashEmbeddingBackend, build_embedding_backend, cosine_similarity
from arpo.retrieval.vector_index import PersistentVectorIndex


class DenseRetriever:
    """Embedding-based retriever backed by a persistent local vector index."""

    def __init__(
        self,
        corpus: Corpus,
        *,
        backend: EmbeddingBackend | None = None,
        index_dir: str | Path | None = None,
        use_cache: bool | None = None,
    ):
        self.corpus = corpus
        self.backend = backend or build_embedding_backend()
        self.index = PersistentVectorIndex.from_corpus(
            corpus,
            self.backend,
            index_dir=index_dir,
            use_cache=use_cache,
        )

    def search(self, query: str, *, top_k: int, sub_query_id: str) -> list[RetrievalCandidate]:
        query_vector = self.backend.embed_query(query)
        scored = []
        for record in self.index.records:
            score = cosine_similarity(query_vector, record.vector)
            if score > 0:
                scored.append((score, record.document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievalCandidate(
                document=document,
                score=score,
                source=f"{self.backend.name}_dense",
                rank=rank,
                sub_query_id=sub_query_id,
                explanation=f"Embedding similarity using {self.backend.model_id}",
                features={
                    "dense": score,
                    "embedding_backend": self.backend.name,
                    "embedding_model": self.backend.model_id,
                },
            )
            for rank, (score, document) in enumerate(scored[:top_k], start=1)
        ]

    def diagnostics(self) -> dict[str, object]:
        return {
            "embedding_backend": self.backend.name,
            "embedding_model": self.backend.model_id,
            "embedding_dimensions": self.backend.dimensions,
            "vector_index_documents": len(self.index.records),
            "vector_index_cache_hit": self.index.cache_hit,
            "vector_index_path": str(self.index.index_path) if self.index.index_path else None,
        }


class HashDenseRetriever(DenseRetriever):
    """Backward-compatible alias for the deterministic hash embedding backend."""

    def __init__(self, corpus: Corpus, *, dimensions: int = 512):
        super().__init__(
            corpus,
            backend=HashEmbeddingBackend(dimensions=dimensions),
        )
