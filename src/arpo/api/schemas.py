from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchRequest(_StrictRequest):
    query: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(5, ge=1, le=50)
    corpus_path: str = Field("data/arpo-openalex-corpus.jsonl", min_length=1, max_length=500)


class EvaluateRequest(_StrictRequest):
    corpus_path: str = Field("data/arpo-openalex-corpus.jsonl", min_length=1, max_length=500)
    queries_path: str = Field("data/arpo-openalex-queries.jsonl", min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=50)


class SuggestRequest(_StrictRequest):
    q: str = Field("", max_length=240)
    corpus_path: str = Field("data/arpo-openalex-corpus.jsonl", min_length=1, max_length=500)
    limit: int = Field(8, ge=1, le=12)


class IndexRequest(_StrictRequest):
    corpus_path: str = Field("data/arpo-openalex-corpus.jsonl", min_length=1, max_length=500)
    backend: str = Field("hash", min_length=1, max_length=80)
    model_id: str | None = Field(None, max_length=200)
    index_dir: str | None = Field(None, max_length=500)


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


BenchmarkFormat = Literal["auto", "native", "hotpotqa", "scifact", "beir"]


class ClaimStudyRequest(AblationRequest):
    benchmark: BenchmarkFormat = "auto"
    split: str = Field("test", min_length=1, max_length=80)
    output_dir: str | None = Field("data/experiments", max_length=500)
