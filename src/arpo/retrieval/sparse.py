from __future__ import annotations

import math
from collections import Counter, defaultdict

from arpo.models import RetrievalCandidate
from arpo.retrieval.corpus import Corpus
from arpo.text import tokenize


class BM25Retriever:
    def __init__(self, corpus: Corpus, *, k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.doc_tokens = {document.id: tokenize(f"{document.title} {document.text}") for document in corpus.documents}
        self.doc_lengths = {document_id: len(tokens) for document_id, tokens in self.doc_tokens.items()}
        self.avg_doc_length = sum(self.doc_lengths.values()) / max(1, len(self.doc_lengths))
        self.term_frequencies = {
            document_id: Counter(tokens) for document_id, tokens in self.doc_tokens.items()
        }
        self.document_frequency: dict[str, int] = defaultdict(int)
        for tokens in self.doc_tokens.values():
            for token in set(tokens):
                self.document_frequency[token] += 1

    def search(self, query: str, *, top_k: int, sub_query_id: str) -> list[RetrievalCandidate]:
        query_terms = tokenize(query)
        scored = []
        for document in self.corpus.documents:
            score = self._score(query_terms, document.id)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievalCandidate(
                document=document,
                score=score,
                source="bm25",
                rank=rank,
                sub_query_id=sub_query_id,
                explanation="BM25 sparse lexical match",
                features={"bm25": score},
            )
            for rank, (score, document) in enumerate(scored[:top_k], start=1)
        ]

    def _score(self, query_terms: list[str], document_id: str) -> float:
        score = 0.0
        term_frequency = self.term_frequencies[document_id]
        doc_length = self.doc_lengths[document_id]
        total_docs = max(1, len(self.corpus))
        for term in query_terms:
            if term not in term_frequency:
                continue
            df = self.document_frequency.get(term, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            frequency = term_frequency[term]
            numerator = frequency * (self.k1 + 1)
            denominator = frequency + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            score += idf * numerator / denominator
        return score

