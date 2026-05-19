from __future__ import annotations

from arpo.models import RetrievalCandidate
from arpo.retrieval.corpus import Corpus
from arpo.text import cosine, hashed_vector


class HashDenseRetriever:
    """Dependency-free dense-like retriever using signed hashing over token n-grams."""

    def __init__(self, corpus: Corpus, *, dimensions: int = 512):
        self.corpus = corpus
        self.dimensions = dimensions
        self.doc_vectors = {
            document.id: hashed_vector(f"{document.title} {document.text}", dimensions=dimensions)
            for document in corpus.documents
        }

    def search(self, query: str, *, top_k: int, sub_query_id: str) -> list[RetrievalCandidate]:
        query_vector = hashed_vector(query, dimensions=self.dimensions)
        scored = []
        for document in self.corpus.documents:
            score = cosine(query_vector, self.doc_vectors[document.id])
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievalCandidate(
                document=document,
                score=score,
                source="hash_dense",
                rank=rank,
                sub_query_id=sub_query_id,
                explanation="Hashed dense semantic proxy",
                features={"dense": score},
            )
            for rank, (score, document) in enumerate(scored[:top_k], start=1)
        ]

