from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from time import perf_counter, time
from typing import Any
from uuid import uuid4

from arpo.api.runtime import ApiMetrics, JobManager, RunStore
from arpo.corpus_quality import corpus_quality_report
from arpo.evaluation.benchmarks import load_benchmark_records
from arpo.evaluation.claim_study import run_claim_study
from arpo.evaluation.variants import VARIANT_LABELS, validate_variants, variant_controls
from arpo.ingestion import ingest_path
from arpo.ingestion.pipeline import SUPPORTED_SOURCE_EXTENSIONS
from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus
from arpo.retrieval.embeddings import build_embedding_backend
from arpo.retrieval.vector_index import PersistentVectorIndex

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    from arpo.api.schemas import (
        AblationRequest,
        ClaimStudyRequest,
        EvaluateRequest,
        IndexRequest,
        SearchRequest,
        SuggestRequest,
    )
    from arpo.evaluation.runner import evaluate_pipeline, load_query_records
except ImportError as exc:  # pragma: no cover
    FastAPI = None
    File = None
    Form = None
    HTTPException = None
    JSONResponse = None
    StaticFiles = None
    UploadFile = None
    CORSMiddleware = None
    SearchRequest = None
    EvaluateRequest = None
    AblationRequest = None
    ClaimStudyRequest = None
    IndexRequest = None
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
RUN_STORE_PATH = Path(os.getenv("ARPO_RUN_STORE", DATA_DIR / "arpo-runs.sqlite")).resolve()
JOB_WORKERS = int(os.getenv("ARPO_JOB_WORKERS", "2"))
API_KEYS = {key.strip() for key in os.getenv("ARPO_API_KEYS", "").split(",") if key.strip()}
RATE_LIMIT_PER_MINUTE = int(os.getenv("ARPO_RATE_LIMIT_PER_MINUTE", "120"))
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.jsonl$")
SAFE_SOURCE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.[A-Za-z0-9]{1,12}$")
PUBLIC_API_PATHS = {"/health", "/api/health", "/healthz", "/api/healthz"}
ALLOWED_ABLATION_VARIANTS = VARIANT_LABELS
API_METRICS = ApiMetrics()
RUN_STORE = RunStore(RUN_STORE_PATH)
JOB_MANAGER = JobManager(max_workers=JOB_WORKERS, run_store=RUN_STORE)
RATE_LIMIT_LOCK = threading.Lock()
RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


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
        allow_headers=["Content-Type", "Authorization", "x-api-key"],
    )

    @app.middleware("http")
    async def production_middleware(request: Any, call_next: Any) -> Any:
        request_id = request.headers.get("x-request-id") or uuid4().hex[:16]
        start = perf_counter()
        response = None

        try:
            if not _is_authorized(request):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid API key.", "request_id": request_id},
                )
            elif not _rate_limit_allows(request):
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded.", "request_id": request_id},
                )
            else:
                response = await call_next(request)
        except Exception:
            API_METRICS.record(
                path=request.url.path,
                status_code=500,
                latency_ms=_elapsed_ms(start),
            )
            LOGGER.exception("Unhandled request error [request_id=%s]", request_id)
            raise

        latency_ms = _elapsed_ms(start)
        response.headers["x-request-id"] = request_id
        response.headers["x-arpo-latency-ms"] = str(latency_ms)
        API_METRICS.record(
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        LOGGER.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "workspace_root": WORKSPACE_ROOT.as_posix(),
            "data_dir": DATA_DIR.as_posix(),
            "frontend_dist_exists": FRONTEND_DIST.exists(),
            "run_store": _public_path(RUN_STORE_PATH),
            "auth_enabled": bool(API_KEYS),
            "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
        }

    @app.get("/metrics")
    def metrics() -> dict[str, Any]:
        return {
            "api": API_METRICS.snapshot(),
            "jobs": JOB_MANAGER.list(limit=10),
            "recent_runs": RUN_STORE.list_runs(limit=10),
        }

    @app.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        try:
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            pipeline = ARPOPipeline.from_corpus(corpus)
            result = pipeline.run(request.query, top_k=request.top_k).to_dict()
            run = RUN_STORE.save_run(
                run_type="search",
                status="completed",
                request=request.model_dump(),
                response=result,
                latency_ms=float(result["diagnostics"].get("latency_ms", 0.0)),
            )
            result["diagnostics"]["run_id"] = run["id"]
            return result
        except Exception as exc:
            _raise_http_error("search", exc)

    @app.post("/evaluate")
    def evaluate(request: EvaluateRequest) -> dict[str, Any]:
        try:
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
            report = evaluate_pipeline(corpus, records, top_k=request.top_k)
            run = RUN_STORE.save_run(
                run_type="evaluation",
                status="completed",
                request=request.model_dump(),
                response=report,
                latency_ms=float(report.get("latency_ms", 0.0)),
            )
            report["run_id"] = run["id"]
            return report
        except Exception as exc:
            _raise_http_error("evaluate", exc)

    @app.post("/ablation")
    def ablation(request: AblationRequest) -> dict[str, Any]:
        try:
            validate_variants(request.variants)

            corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
            records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
            results: list[dict[str, Any]] = []

            for variant in request.variants:
                strategy_factory, disable_query_graph = variant_controls(variant)
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

            report = {"top_k": request.top_k, "query_count": len(records), "results": results}
            run = RUN_STORE.save_run(
                run_type="ablation",
                status="completed",
                request=request.model_dump(),
                response=report,
                latency_ms=_mean(item["latency_ms"] for item in results),
            )
            report["run_id"] = run["id"]
            return report
        except Exception as exc:
            _raise_http_error("ablation", exc)

    @app.post("/claim-study")
    def claim_study(request: ClaimStudyRequest) -> dict[str, Any]:
        try:
            report = _run_claim_study(request)
            run = RUN_STORE.save_run(
                run_type="claim_study",
                status="completed",
                request=request.model_dump(),
                response=report,
                latency_ms=float(_mean(item["summary"]["latency_ms"] for item in report["variants"])),
            )
            report["run_id"] = run["id"]
            return report
        except Exception as exc:
            _raise_http_error("claim_study", exc)

    @app.post("/jobs/evaluate")
    def evaluate_job(request: EvaluateRequest) -> dict[str, Any]:
        return JOB_MANAGER.submit(
            job_type="evaluation",
            request=request.model_dump(),
            fn=lambda: _run_evaluation(request),
        )

    @app.post("/jobs/ablation")
    def ablation_job(request: AblationRequest) -> dict[str, Any]:
        return JOB_MANAGER.submit(
            job_type="ablation",
            request=request.model_dump(),
            fn=lambda: _run_ablation(request),
        )

    @app.post("/jobs/claim-study")
    def claim_study_job(request: ClaimStudyRequest) -> dict[str, Any]:
        return JOB_MANAGER.submit(
            job_type="claim_study",
            request=request.model_dump(),
            fn=lambda: _run_claim_study(request),
        )

    @app.post("/jobs/index")
    def index_job(request: IndexRequest) -> dict[str, Any]:
        return JOB_MANAGER.submit(
            job_type="index",
            request=request.model_dump(),
            fn=lambda: _run_index(request),
        )

    @app.get("/jobs")
    def list_jobs(limit: int = 25) -> dict[str, Any]:
        return {"jobs": JOB_MANAGER.list(limit=limit)}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = JOB_MANAGER.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job was not found.")
        return job

    @app.get("/runs")
    def list_runs(limit: int = 25, run_type: str | None = None) -> dict[str, Any]:
        return {"runs": RUN_STORE.list_runs(limit=limit, run_type=run_type)}

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = RUN_STORE.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run was not found.")
        return run

    @app.get("/corpora")
    def list_corpora() -> dict[str, Any]:
        return {"corpora": [*_list_corpora(EXAMPLES_DIR, "example"), *_list_corpora(DATA_DIR, "uploaded")]}

    @app.get("/corpora/stats")
    def corpus_stats(corpus_path: str = "data/arpo-openalex-corpus.jsonl") -> dict[str, Any]:
        try:
            corpus = Corpus.from_jsonl(_resolve_jsonl_path(corpus_path, must_exist=True))
            return {"corpus_path": corpus_path, "quality": corpus_quality_report(corpus)}
        except Exception as exc:
            _raise_http_error("corpus_stats", exc)

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
    app.get("/api/healthz", include_in_schema=False)(healthz)
    app.get("/api/metrics", include_in_schema=False)(metrics)
    app.post("/api/search", include_in_schema=False)(search)
    app.post("/api/evaluate", include_in_schema=False)(evaluate)
    app.post("/api/ablation", include_in_schema=False)(ablation)
    app.post("/api/claim-study", include_in_schema=False)(claim_study)
    app.post("/api/research/claim-study", include_in_schema=False)(claim_study)
    app.post("/api/jobs/evaluate", include_in_schema=False)(evaluate_job)
    app.post("/api/jobs/ablation", include_in_schema=False)(ablation_job)
    app.post("/api/jobs/claim-study", include_in_schema=False)(claim_study_job)
    app.post("/api/jobs/index", include_in_schema=False)(index_job)
    app.get("/api/jobs", include_in_schema=False)(list_jobs)
    app.get("/api/jobs/{job_id}", include_in_schema=False)(get_job)
    app.get("/api/runs", include_in_schema=False)(list_runs)
    app.get("/api/runs/{run_id}", include_in_schema=False)(get_run)
    app.get("/api/corpora", include_in_schema=False)(list_corpora)
    app.get("/api/corpora/stats", include_in_schema=False)(corpus_stats)
    app.get("/api/suggest", include_in_schema=False)(suggest)
    app.post("/api/corpora/upload", include_in_schema=False)(upload_corpus)
    app.post("/api/corpora/ingest", include_in_schema=False)(ingest_corpus)

    if FRONTEND_DIST.exists() and StaticFiles is not None:
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


def _run_evaluation(request: Any) -> dict[str, Any]:
    corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
    records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
    return evaluate_pipeline(corpus, records, top_k=request.top_k)


def _run_ablation(request: Any) -> dict[str, Any]:
    validate_variants(request.variants)

    corpus = Corpus.from_jsonl(_resolve_jsonl_path(request.corpus_path, must_exist=True))
    records = load_query_records(_resolve_jsonl_path(request.queries_path, must_exist=True))
    results: list[dict[str, Any]] = []

    for variant in request.variants:
        strategy_factory, disable_query_graph = variant_controls(variant)
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


def _run_claim_study(request: Any) -> dict[str, Any]:
    corpus_path = _resolve_jsonl_path(request.corpus_path, must_exist=True)
    queries_path = _resolve_benchmark_path(request.queries_path, benchmark=request.benchmark)
    output_dir = _resolve_output_dir(request.output_dir) if request.output_dir else None
    corpus = Corpus.from_jsonl(corpus_path)
    records, benchmark = load_benchmark_records(
        queries_path,
        benchmark=request.benchmark,
        split=request.split,
    )
    return run_claim_study(
        corpus,
        records,
        top_k=request.top_k,
        variants=request.variants,
        benchmark=benchmark,
        artifact_dir=output_dir,
        corpus_path=_public_path(corpus_path),
        queries_path=_public_path(queries_path),
    )


def _run_index(request: Any) -> dict[str, Any]:
    corpus_path = _resolve_jsonl_path(request.corpus_path, must_exist=True)
    corpus = Corpus.from_jsonl(corpus_path)
    backend = build_embedding_backend(request.backend, model_id=request.model_id)
    index = PersistentVectorIndex.from_corpus(
        corpus,
        backend,
        index_dir=request.index_dir or os.getenv("ARPO_VECTOR_INDEX_DIR"),
    )
    return {
        "corpus_path": _public_path(corpus_path),
        "documents": len(corpus),
        "embedding_backend": index.backend_name,
        "embedding_model": index.model_id,
        "dimensions": index.dimensions,
        "cache_hit": index.cache_hit,
        "index_path": _public_path(index.index_path) if index.index_path else None,
    }


def _ablation_controls(variant: str) -> tuple[Any, bool]:
    return variant_controls(variant)


def _cors_origins() -> list[str]:
    raw = os.getenv("ARPO_CORS_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def _is_authorized(request: Any) -> bool:
    if not API_KEYS:
        return True

    path = request.url.path
    if request.method == "OPTIONS" or path in PUBLIC_API_PATHS:
        return True
    protected_prefixes = (
        "/api/",
        "/search",
        "/evaluate",
        "/ablation",
        "/claim-study",
        "/research",
        "/corpora",
        "/suggest",
        "/jobs",
        "/runs",
        "/metrics",
    )
    if not path.startswith(protected_prefixes):
        return True

    provided = request.headers.get("x-api-key") or _bearer_token(request.headers.get("authorization", ""))
    return provided in API_KEYS


def _bearer_token(value: str) -> str:
    prefix = "bearer "
    return value[len(prefix):].strip() if value.lower().startswith(prefix) else ""


def _rate_limit_allows(request: Any) -> bool:
    if RATE_LIMIT_PER_MINUTE <= 0:
        return True

    path = request.url.path
    if path in PUBLIC_API_PATHS:
        return True

    client = request.client.host if request.client else "unknown"
    key = f"{client}:{path}"
    now = time()
    window_start = now - 60

    with RATE_LIMIT_LOCK:
        bucket = [timestamp for timestamp in RATE_LIMIT_BUCKETS.get(key, []) if timestamp >= window_start]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            RATE_LIMIT_BUCKETS[key] = bucket
            return False
        bucket.append(now)
        RATE_LIMIT_BUCKETS[key] = bucket
        return True


def _mean(values: Any) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


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


def _resolve_benchmark_path(path_value: str, *, benchmark: str) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else WORKSPACE_ROOT / raw_path
    resolved = candidate.resolve()

    if not any(_is_relative_to(resolved, root) for root in (EXAMPLES_DIR, DATA_DIR)):
        raise ValueError("Benchmark path must be inside the configured examples or data directory.")

    if benchmark == "beir" or resolved.is_dir():
        if not resolved.is_dir():
            raise FileNotFoundError("Requested BEIR benchmark directory was not found.")
        return resolved

    if resolved.suffix.lower() not in {".jsonl", ".json"}:
        raise ValueError("Benchmark query files must be .jsonl or .json unless using BEIR directories.")

    if not resolved.is_file():
        raise FileNotFoundError("Requested benchmark query file was not found.")

    return resolved


def _resolve_output_dir(path_value: str) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else WORKSPACE_ROOT / raw_path
    resolved = candidate.resolve()

    if not _is_relative_to(resolved, DATA_DIR):
        raise ValueError("Experiment output directory must be inside the configured data directory.")

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
