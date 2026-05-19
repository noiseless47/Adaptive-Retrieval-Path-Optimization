from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arpo.evaluation.metrics import mean_reciprocal_rank, ndcg_at_k, precision_at_k, recall_at_k
from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus


@dataclass(frozen=True)
class QueryRecord:
    id: str
    query: str
    relevant_ids: set[str]
    graded_relevance: dict[str, float]


def load_query_records(path: str | Path) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            try:
                records.append(
                    QueryRecord(
                        id=str(raw["id"]),
                        query=str(raw["query"]),
                        relevant_ids={str(item) for item in raw.get("relevant_ids", [])},
                        graded_relevance={
                            str(document_id): float(score)
                            for document_id, score in raw.get("graded_relevance", {}).items()
                        },
                    )
                )
            except KeyError as exc:
                raise ValueError(f"Missing {exc} in {path} line {line_number}") from exc
    return records


def evaluate_pipeline(corpus: Corpus, records: list[QueryRecord], *, top_k: int = 5) -> dict[str, Any]:
    pipeline = ARPOPipeline.from_corpus(corpus)
    per_query: list[dict[str, Any]] = []
    rankings: list[list[str]] = []
    relevant_sets: list[set[str]] = []

    for record in records:
        result = pipeline.run(record.query, top_k=top_k)
        ranking = [node.document.id for node in result.ranked_evidence]
        rankings.append(ranking)
        relevant_sets.append(record.relevant_ids)
        per_query.append(
            {
                "id": record.id,
                "query": record.query,
                "query_type": result.analysis.query_type,
                "ranking": ranking,
                "precision_at_k": precision_at_k(ranking, record.relevant_ids, top_k),
                "recall_at_k": recall_at_k(ranking, record.relevant_ids, top_k),
                "ndcg_at_k": ndcg_at_k(ranking, record.graded_relevance, top_k),
                "diagnostics": result.diagnostics,
            }
        )

    return {
        "top_k": top_k,
        "query_count": len(records),
        "precision_at_k": _mean(item["precision_at_k"] for item in per_query),
        "recall_at_k": _mean(item["recall_at_k"] for item in per_query),
        "ndcg_at_k": _mean(item["ndcg_at_k"] for item in per_query),
        "mrr": mean_reciprocal_rank(rankings, relevant_sets),
        "queries": per_query,
    }


def _mean(values: Any) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0

