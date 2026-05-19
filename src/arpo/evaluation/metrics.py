from __future__ import annotations

import math
from collections.abc import Iterable


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for document_id in top if document_id in relevant) / len(top)


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    return sum(1 for document_id in top if document_id in relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for index, document_id in enumerate(retrieved, start=1):
        if document_id in relevant:
            return 1.0 / index
    return 0.0


def mean_reciprocal_rank(rankings: Iterable[list[str]], relevant_sets: Iterable[set[str]]) -> float:
    scores = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in zip(rankings, relevant_sets)
    ]
    return sum(scores) / len(scores) if scores else 0.0


def ndcg_at_k(retrieved: list[str], graded_relevance: dict[str, float], k: int) -> float:
    def dcg(items: list[str]) -> float:
        return sum(
            (2 ** graded_relevance.get(document_id, 0.0) - 1) / math.log2(index + 1)
            for index, document_id in enumerate(items[:k], start=1)
        )

    ideal = sorted(graded_relevance, key=graded_relevance.get, reverse=True)
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(retrieved) / ideal_dcg

