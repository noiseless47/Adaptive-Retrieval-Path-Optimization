from __future__ import annotations

import logging
import os
import re
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from arpo.ingestion import ingest_path
from arpo.ingestion.pipeline import SUPPORTED_SOURCE_EXTENSIONS
from arpo.models import QueryAnalysis, RetrievalStrategy
from arpo.pipeline import ARPOPipeline
from arpo.planning.strategy import RetrievalStrategyPlanner
from arpo.retrieval import Corpus

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from arpo.api.schemas import AblationRequest, EvaluateRequest, SearchRequest, SuggestRequest
    from arpo.evaluation.runner import evaluate_pipeline, load_query_records
except ImportError as exc:  # pragma: no cover
    FastAPI = None
    File = None
    Form = None
    HTTPException = None
    StaticFiles = None
    UploadFile = None
    CORSMiddleware = None
    SearchRequest = None
    EvaluateRequest = None
    AblationRequest = None
    SuggestRequest = None
    evaluate_pipeline = None
    load_query_records = None
    FASTAPI_IMPORT_ERROR = exc
else:
    FASTAPI_IMPORT_ERROR = None


LOGGER = logging.getLogger(__name__)
WORKSPACE_ROOT = Path(os.getenv("ARPO_WORKSPACE_ROOT", Path.cwd())).resolve()
DATA_DIR = Path(os.getenv("ARPO_DATA_DIR", WORKSPACE_ROOT / "data")).resolve()
EXAMPLES_DIR = Path(os.getenv("ARPO_EXAMPLES_DIR", WORKSPACE_ROOT / "examples")).resolve()
FRONTEND_DIST = Path(os.getenv("ARPO_FRONTEND_DIST", WORKSPACE_ROOT / "frontend" / "dist")).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("ARPO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.jsonl$")
SAFE_SOURCE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.[A-Za-z0-9]{1,12}$")
ALLOWED_ABLATION_VARIANTS = {
    "full": "Full ARPO",
    "no_pruning": "No Pruning",
    "no_query_graph": "No Query Graph",
    "sparse_only": "Sparse Only",
    "dense_only": "Dense Only",
    "fixed_hybrid": "Fixed Hybrid",
}


def create_app() -> Any:
    if FastAPI is None:
        raise RuntimeError("Install API dependencies with: pip install -e .[api]") from FASTAPI_IMPORT_ERROR

    app = FastAPI(
        title="Adaptive Retrieval Path Optimization",
        description="Adaptive multi-hop retrieval with dynamic query graphs and confidence pruning.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        try:
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            pipeline = ARPOPipeline.from_corpus(corpus)
            return pipeline.run(request.query, top_k=request.top_k).to_dict()
        except Exception as exc:
            _raise_http_error("search", exc)

    @app.post("/evaluate")
    def evaluate(request: EvaluateRequest) -> dict[str, Any]:
        try:
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
            return evaluate_pipeline(corpus, records, top_k=request.top_k)
        except Exception as exc:
            _raise_http_error("evaluate", exc)

    @app.post("/ablation")
    def ablation(request: AblationRequest) -> dict[str, Any]:
        try:
            invalid = [variant for variant in request.variants if variant not in ALLOWED_ABLATION_VARIANTS]
            if invalid:
                allowed = ", ".join(sorted(ALLOWED_ABLATION_VARIANTS))
                raise ValueError(f"Unsupported ablation variant(s): {', '.join(invalid)}. Allowed: {allowed}")

            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
            results: list[dict[str, Any]] = []

            for variant in request.variants:
                strategy_factory, disable_query_graph = _ablation_controls(variant)
                report = evaluate_pipeline(
                    corpus,
                    records,
                    top_k=request.top_k,
                    strategy_factory=strategy_factory,
                    disable_query_graph=disable_query_graph,
                )
                results.append(
                    {
                        "variant": ALLOWED_ABLATION_VARIANTS[variant],
                        "recall_at_k": report["recall_at_k"],
                        "ndcg_at_k": report["ndcg_at_k"],
                        "mrr": report["mrr"],
                        "latency_ms": report["latency_ms"],
                    }
                )

            return {"top_k": request.top_k, "query_count": len(records), "results": results}
        except Exception as exc:
            _raise_http_error("ablation", exc)

    @app.get("/corpora")
    def list_corpora() -> dict[str, Any]:
        return {"corpora": [*_list_corpora(EXAMPLES_DIR, "example"), *_list_corpora(DATA_DIR, "uploaded")]}

    @app.get("/suggest")
    def suggest(
        q: str = "",
        corpus_path: str = "data/arpo-openalex-corpus.jsonl",
        limit: int = 8,
    ) -> dict[str, Any]:
        try:
            request = SuggestRequest(q=q, corpus_path=corpus_path, limit=limit)
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            return {"suggestions": _query_suggestions(corpus, request.q, request.limit)}
        except Exception as exc:
            _raise_http_error("suggest", exc)

    @app.post("/corpora/upload")
    async def upload_corpus(file: UploadFile = File(...)) -> dict[str, Any]:
        safe_name = _safe_upload_filename(file.filename)
        destination = _dedupe_path(DATA_DIR / safe_name)
        temp_path = DATA_DIR / f".{uuid4().hex}.upload.tmp"

        try:
            total_bytes = await _write_upload_limited(file, temp_path)
            corpus = Corpus.from_jsonl(temp_path)
            if len(corpus) == 0:
                raise ValueError("Uploaded corpus must contain at least one JSONL document.")
            temp_path.replace(destination)
            return {
                "message": "Upload successful",
                "path": _public_path(destination),
                "documents": len(corpus),
                "bytes": total_bytes,
            }
        except Exception as exc:
            _unlink_quietly(temp_path)
            _raise_http_error("upload_corpus", exc)
        finally:
            await file.close()

    @app.post("/corpora/ingest")
    async def ingest_corpus(
        file: UploadFile = File(...),
        chunk_words: int = Form(220),
        overlap_words: int = Form(45),
        min_chunk_chars: int = Form(120),
    ) -> dict[str, Any]:
        safe_name = _safe_source_filename(file.filename)
        source_suffix = Path(safe_name).suffix.lower()
        temp_path = DATA_DIR / f".{uuid4().hex}.source{source_suffix}"
        destination = _dedupe_path(DATA_DIR / f"{Path(safe_name).stem}.jsonl")

        try:
            total_bytes = await _write_upload_limited(file, temp_path)
            report = ingest_path(
                temp_path,
                destination,
                chunk_words=chunk_words,
                overlap_words=overlap_words,
                min_chunk_chars=min_chunk_chars,
            )
            corpus = Corpus.from_jsonl(destination)
            return {
                "message": "Ingestion successful",
                "path": _public_path(destination),
                "documents": len(corpus),
                "bytes": total_bytes,
                "source_filename": safe_name,
                **report.to_dict(),
                "input_path": safe_name,
                "output_path": _public_path(destination),
            }
        except Exception as exc:
            _unlink_quietly(destination)
            _raise_http_error("ingest_corpus", exc)
        finally:
            _unlink_quietly(temp_path)
            await file.close()

    app.get("/api/health", include_in_schema=False)(health)
    app.post("/api/search", include_in_schema=False)(search)
    app.post("/api/evaluate", include_in_schema=False)(evaluate)
    app.post("/api/ablation", include_in_schema=False)(ablation)
    app.get("/api/corpora", include_in_schema=False)(list_corpora)
    app.get("/api/suggest", include_in_schema=False)(suggest)
    app.post("/api/corpora/upload", include_in_schema=False)(upload_corpus)
    app.post("/api/corpora/ingest", include_in_schema=False)(ingest_corpus)

    if FRONTEND_DIST.exists() and StaticFiles is not None:
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


def _ablation_controls(variant: str) -> tuple[Any, bool]:
    planner = RetrievalStrategyPlanner()

    def planned(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
        return planner.plan(analysis, top_k=top_k)

    if variant == "full":
        return planned, False

    if variant == "no_pruning":
        def no_pruning_strategy(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
            strategy = planned(analysis, top_k)
            return replace(
                strategy,
                strategy_id=f"{strategy.strategy_id}_no_pruning",
                pruning_threshold=0.0,
            )

        return (
            no_pruning_strategy,
            False,
        )

    if variant == "no_query_graph":
        def no_query_graph_strategy(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
            return replace(
                planned(analysis, top_k),
                strategy_id="no_query_graph",
                graph_weight=0.0,
                max_hops=1,
            )

        return (
            no_query_graph_strategy,
            True,
        )

    if variant == "sparse_only":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="sparse_only",
                sparse_weight=1.0,
                dense_weight=0.0,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k, 8),
                max_hops=1,
                pruning_threshold=0.0,
                diversity_lambda=0.0,
                reranking_mode="precision",
            ),
            True,
        )

    if variant == "dense_only":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="dense_only",
                sparse_weight=0.0,
                dense_weight=1.0,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k, 8),
                max_hops=1,
                pruning_threshold=0.0,
                diversity_lambda=0.0,
                reranking_mode="semantic",
            ),
            True,
        )

    if variant == "fixed_hybrid":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="fixed_hybrid",
                sparse_weight=0.5,
                dense_weight=0.5,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k + 2, 8),
                max_hops=1,
                pruning_threshold=0.4,
                diversity_lambda=0.2,
                reranking_mode="fixed",
            ),
            False,
        )

    raise ValueError(f"Unsupported ablation variant: {variant}")


def _cors_origins() -> list[str]:
    raw = os.getenv("ARPO_CORS_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def _resolve_jsonl_path(path_value: str, *, must_exist: bool) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else WORKSPACE_ROOT / raw_path
    resolved = candidate.resolve()

    if resolved.suffix.lower() != ".jsonl":
        raise ValueError("Only .jsonl files are supported.")

    if not any(_is_relative_to(resolved, root) for root in (EXAMPLES_DIR, DATA_DIR)):
        raise ValueError("Path must be inside the configured examples or data directory.")

    if must_exist and not resolved.is_file():
        raise FileNotFoundError("Requested JSONL file was not found.")

    return resolved


def _safe_upload_filename(filename: str | None) -> str:
    raw = filename or ""
    if "/" in raw or "\\" in raw:
        raise ValueError("Upload filename must not contain path separators.")
    normalized = raw.strip()
    if not SAFE_FILENAME_RE.fullmatch(normalized):
        raise ValueError(
            "Upload filename must be a .jsonl file using only letters, numbers, dots, dashes, and underscores."
        )
    return normalized


def _safe_source_filename(filename: str | None) -> str:
    raw = filename or ""
    if "/" in raw or "\\" in raw:
        raise ValueError("Upload filename must not contain path separators.")

    normalized = raw.strip()
    if not SAFE_SOURCE_FILENAME_RE.fullmatch(normalized):
        raise ValueError(
            "Source filename must use only letters, numbers, dots, dashes, and underscores."
        )

    suffix = Path(normalized).suffix.lower()
    if suffix not in SUPPORTED_SOURCE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_EXTENSIONS))
        raise ValueError(f"Unsupported source type '{suffix}'. Supported extensions: {allowed}")

    return normalized


async def _write_upload_limited(file: Any, path: Path) -> int:
    total = 0
    with path.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise ValueError(f"Upload exceeds maximum size of {MAX_UPLOAD_BYTES} bytes.")
            handle.write(chunk)
    return total


def _dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate

    raise ValueError("Too many files with this corpus name already exist.")


def _query_suggestions(corpus: Corpus, query: str, limit: int) -> list[dict[str, Any]]:
    normalized_query = _normalize_suggestion_text(query)
    candidates: dict[str, dict[str, Any]] = {}
    topic_stats: dict[str, dict[str, Any]] = {}

    def add_candidate(
        text: str,
        *,
        kind: str,
        source: str,
        priority: float,
        metadata: dict[str, Any] | None = None,
        match_text: str = "",
    ) -> None:
        suggestion_text = _clean_suggestion(text)
        if len(suggestion_text) < 12:
            return

        match_score = _suggestion_match_score(normalized_query, f"{suggestion_text} {match_text}")
        if normalized_query and match_score is None:
            return

        metadata = metadata or {}
        score = priority + (match_score or 0.0)
        key = suggestion_text.casefold()
        current = candidates.get(key)
        if current is None or score > current["score"]:
            candidates[key] = {
                "text": suggestion_text,
                "kind": kind,
                "source": source,
                "score": round(score, 4),
                "metadata": metadata,
            }

    for document in corpus.documents:
        metadata = document.metadata
        source = str(metadata.get("source", "Corpus"))
        citations = _safe_number(metadata.get("cited_by_count"))

        for raw_topic in (metadata.get("domain"), metadata.get("harvest_query")):
            topic = _human_topic(raw_topic)
            if not topic:
                continue

            topic_record = topic_stats.setdefault(topic, {"count": 0, "citations": 0.0})
            topic_record["count"] += 1
            topic_record["citations"] += citations

        for concept in _iter_metadata_terms(metadata, "concepts", limit=5):
            topic = _human_topic(concept)
            if topic:
                add_candidate(
                    f"Surface high-confidence papers about {topic}",
                    kind="concept",
                    source=source,
                    priority=18.0 + min(citations / 400.0, 6.0),
                    metadata={"document_id": document.id},
                    match_text=f"{document.title} {metadata.get('domain', '')}",
                )

        title = _clean_suggestion(document.title)
        if title:
            add_candidate(
                f"Retrieve papers related to {title}",
                kind="paper",
                source=source,
                priority=16.0 + min(citations / 300.0, 8.0),
                metadata={"document_id": document.id, "year": metadata.get("year")},
                match_text=f"{title} {metadata.get('domain', '')} {' '.join(_iter_metadata_terms(metadata, 'concepts', 6))}",
            )

    for topic, stats in topic_stats.items():
        priority = 30.0 + min(float(stats["count"]), 18.0) + min(float(stats["citations"]) / 1200.0, 10.0)
        add_candidate(
            f"Trace evidence paths for {topic}",
            kind="brief",
            source="Corpus Topic",
            priority=priority,
            metadata={"documents": stats["count"]},
            match_text=topic,
        )
        add_candidate(
            f"Compare retrieval strategies around {topic}",
            kind="brief",
            source="Corpus Topic",
            priority=priority - 2.0,
            metadata={"documents": stats["count"]},
            match_text=topic,
        )

    ranked = sorted(candidates.values(), key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def _iter_metadata_terms(metadata: dict[str, Any], key: str, limit: int) -> list[str]:
    value = metadata.get(key, [])
    if not isinstance(value, list):
        return []

    terms: list[str] = []
    for item in value:
        term = _clean_suggestion(str(item))
        if term:
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def _suggestion_match_score(normalized_query: str, candidate_text: str) -> float | None:
    if not normalized_query:
        return 0.0

    haystack = _normalize_suggestion_text(candidate_text)
    query_variants = _suggestion_query_variants(normalized_query)
    scores = [_single_suggestion_match_score(query_variant, haystack) for query_variant in query_variants]
    valid_scores = [score for score in scores if score is not None]
    if not valid_scores:
        return None

    return max(valid_scores)


def _single_suggestion_match_score(normalized_query: str, haystack: str) -> float | None:
    tokens = normalized_query.split()
    matched = sum(1 for token in tokens if token in haystack)
    if matched == 0:
        return None

    score = 8.0 * matched / max(len(tokens), 1)
    if haystack.startswith(normalized_query):
        score += 48.0
    elif normalized_query in haystack:
        score += 24.0

    haystack_words = haystack.split()
    if any(word.startswith(normalized_query) for word in haystack_words):
        score += 18.0
    if all(any(word.startswith(token) for word in haystack_words) for token in tokens):
        score += 12.0

    return score


def _suggestion_query_variants(normalized_query: str) -> list[str]:
    aliases = {
        "cnn": "convolutional neural network",
        "cnns": "convolutional neural networks",
        "llm": "large language model",
        "llms": "large language models",
        "qa": "question answering",
        "rag": "retrieval augmented generation",
    }
    tokens = normalized_query.split()
    expanded = " ".join(aliases.get(token, token) for token in tokens)

    if expanded == normalized_query:
        return [normalized_query]

    return [normalized_query, expanded]


def _human_topic(value: Any) -> str:
    text = _clean_suggestion(str(value or ""))
    if not text:
        return ""

    replacements = {
        r"\bretrieval augmented generation\b": "retrieval-augmented generation",
        r"\bmulti hop\b": "multi-hop",
        r"\bquestion answering\b": "question answering",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    acronyms = {
        "ai": "AI",
        "api": "API",
        "bm25": "BM25",
        "cnn": "CNN",
        "cnns": "CNNs",
        "ir": "IR",
        "llm": "LLM",
        "llms": "LLMs",
        "nlp": "NLP",
        "qa": "QA",
        "rag": "RAG",
    }
    return " ".join(acronyms.get(word.lower(), word) for word in text.split())


def _clean_suggestion(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip().rstrip(".")


def _normalize_suggestion_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _safe_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _list_corpora(directory: Path, source_type: str) -> list[dict[str, Any]]:
    if not directory.exists():
        return []

    corpora: list[dict[str, Any]] = []
    for file_path in sorted(directory.glob("*.jsonl")):
        if not file_path.is_file():
            continue

        try:
            corpus = Corpus.from_jsonl(file_path)
        except (OSError, ValueError) as exc:
            LOGGER.debug("Skipping non-corpus JSONL %s: %s", file_path, exc)
            continue

        if len(corpus) == 0:
            LOGGER.debug("Skipping empty corpus JSONL %s", file_path)
            continue

        corpora.append(
            {
                "id": file_path.name,
                "path": _public_path(file_path),
                "type": source_type,
                "documents": len(corpus),
            }
        )

    return corpora


def _public_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _unlink_quietly(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        LOGGER.warning("Failed to delete temporary upload file: %s", path)


def _raise_http_error(action: str, exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    error_id = uuid4().hex[:12]
    LOGGER.exception("Unhandled ARPO API error during %s [error_id=%s]", action, error_id)
    raise HTTPException(status_code=500, detail=f"Internal server error. Reference: {error_id}") from exc


app = create_app() if FastAPI is not None else None
