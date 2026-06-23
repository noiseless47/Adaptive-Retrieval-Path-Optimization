from __future__ import annotations

import hashlib
from collections import Counter
from statistics import mean
from typing import Any

from arpo.retrieval import Corpus
from arpo.text import tokenize


def corpus_quality_report(corpus: Corpus) -> dict[str, Any]:
    documents = corpus.documents
    text_lengths = [len(document.text) for document in documents]
    token_lengths = [len(tokenize(document.text)) for document in documents]
    title_counter = Counter(_fingerprint(document.title) for document in documents)
    text_counter = Counter(_fingerprint(document.text) for document in documents)
    metadata_keys = Counter(
        key for document in documents for key, value in document.metadata.items() if value not in (None, "", [])
    )

    duplicate_title_count = sum(count - 1 for count in title_counter.values() if count > 1)
    duplicate_text_count = sum(count - 1 for count in text_counter.values() if count > 1)
    citation_edges = sum(len(document.metadata.get("citations", [])) for document in documents)
    related_edges = sum(len(document.metadata.get("related_ids", [])) for document in documents)
    years = [
        int(document.metadata["year"])
        for document in documents
        if str(document.metadata.get("year", "")).isdigit()
    ]

    return {
        "document_count": len(documents),
        "average_text_chars": round(mean(text_lengths), 2) if text_lengths else 0.0,
        "average_text_tokens": round(mean(token_lengths), 2) if token_lengths else 0.0,
        "min_text_chars": min(text_lengths) if text_lengths else 0,
        "max_text_chars": max(text_lengths) if text_lengths else 0,
        "duplicate_title_count": duplicate_title_count,
        "duplicate_text_count": duplicate_text_count,
        "citation_edges": citation_edges,
        "related_edges": related_edges,
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "metadata_coverage": {
            key: round(count / len(documents), 4)
            for key, count in sorted(metadata_keys.items())
        } if documents else {},
        "top_domains": _top_metadata_values(corpus, "domain"),
        "top_sources": _top_metadata_values(corpus, "source"),
    }


def _top_metadata_values(corpus: Corpus, key: str, limit: int = 12) -> list[dict[str, Any]]:
    counts = Counter(
        str(document.metadata.get(key))
        for document in corpus.documents
        if document.metadata.get(key) not in (None, "", [])
    )
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def _fingerprint(value: str) -> str:
    normalized = " ".join(value.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
