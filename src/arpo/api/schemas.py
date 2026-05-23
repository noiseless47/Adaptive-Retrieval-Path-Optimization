from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchRequest(_StrictRequest):
    query: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(5, ge=1, le=50)
    corpus_path: str = Field("examples/corpus.jsonl", min_length=1, max_length=500)


class EvaluateRequest(_StrictRequest):
    corpus_path: str = Field("examples/corpus.jsonl", min_length=1, max_length=500)
    queries_path: str = Field("examples/queries.jsonl", min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=50)


AblationVariant = Literal[
    "full",
    "no_pruning",
    "no_query_graph",
    "sparse_only",
    "dense_only",
    "fixed_hybrid",
]


class AblationRequest(EvaluateRequest):
    variants: list[AblationVariant] = Field(
        default_factory=lambda: [
            "full",
            "no_pruning",
            "no_query_graph",
            "sparse_only",
            "dense_only",
            "fixed_hybrid",
        ],
        min_length=1,
        max_length=6,
    )
