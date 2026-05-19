from __future__ import annotations

from pathlib import Path
from typing import Any

from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - exercised only without optional API deps
    FastAPI = None
    BaseModel = object
    Field = None
    FASTAPI_IMPORT_ERROR = exc
else:
    FASTAPI_IMPORT_ERROR = None


if Field is not None:

    class SearchRequest(BaseModel):
        query: str = Field(..., min_length=3)
        top_k: int = Field(5, ge=1, le=20)
        corpus_path: str = "examples/corpus.jsonl"

else:

    class SearchRequest:  # type: ignore[no-redef]
        pass


def create_app() -> Any:
    if FastAPI is None:
        raise RuntimeError("Install API dependencies with: pip install -e .[api]") from FASTAPI_IMPORT_ERROR

    app = FastAPI(
        title="Adaptive Retrieval Path Optimization",
        description="Adaptive multi-hop retrieval with dynamic query graphs and confidence pruning.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        corpus = Corpus.from_jsonl(Path(request.corpus_path))
        pipeline = ARPOPipeline.from_corpus(corpus)
        return pipeline.run(request.query, top_k=request.top_k).to_dict()

    return app


app = create_app() if FastAPI is not None else None

