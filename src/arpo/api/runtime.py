from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterator
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ApiMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started_at = utc_now()
        self._request_count = 0
        self._error_count = 0
        self._latency_total_ms = 0.0
        self._status_counts: dict[str, int] = {}
        self._path_counts: dict[str, int] = {}

    def record(self, *, path: str, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self._request_count += 1
            if status_code >= 500:
                self._error_count += 1
            self._latency_total_ms += latency_ms
            self._status_counts[str(status_code)] = self._status_counts.get(str(status_code), 0) + 1
            self._path_counts[path] = self._path_counts.get(path, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            average_latency = (
                self._latency_total_ms / self._request_count
                if self._request_count
                else 0.0
            )
            return {
                "started_at": self._started_at,
                "request_count": self._request_count,
                "error_count": self._error_count,
                "average_latency_ms": round(average_latency, 3),
                "status_counts": dict(sorted(self._status_counts.items())),
                "path_counts": dict(sorted(self._path_counts.items())),
            }


class RunStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save_run(
        self,
        *,
        run_type: str,
        status: str,
        request: dict[str, Any],
        response: dict[str, Any] | None = None,
        error: str | None = None,
        run_id: str | None = None,
        latency_ms: float | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        run_id = run_id or uuid4().hex
        with self._lock, self._connection() as connection:
            existing = connection.execute(
                "select created_at from runs where id = ?",
                (run_id,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                insert into runs (
                    id, run_type, status, request_json, response_json, error,
                    latency_ms, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    run_type = excluded.run_type,
                    status = excluded.status,
                    request_json = excluded.request_json,
                    response_json = excluded.response_json,
                    error = excluded.error,
                    latency_ms = excluded.latency_ms,
                    updated_at = excluded.updated_at
                """,
                (
                    run_id,
                    run_type,
                    status,
                    _json_dump(request),
                    _json_dump(response) if response is not None else None,
                    error,
                    latency_ms,
                    created_at,
                    now,
                ),
            )
        return self.get_run(run_id) or {}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            row = connection.execute("select * from runs where id = ?", (run_id,)).fetchone()
        return _run_row_to_dict(row) if row else None

    def list_runs(self, *, limit: int = 25, run_type: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        sql = "select * from runs"
        params: list[Any] = []
        if run_type:
            sql += " where run_type = ?"
            params.append(run_type)
        sql += " order by updated_at desc limit ?"
        params.append(limit)

        with self._lock, self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_run_row_to_dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                create table if not exists runs (
                    id text primary key,
                    run_type text not null,
                    status text not null,
                    request_json text not null,
                    response_json text,
                    error text,
                    latency_ms real,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            connection.execute(
                "create index if not exists idx_runs_updated_at on runs(updated_at desc)"
            )
            connection.execute(
                "create index if not exists idx_runs_type on runs(run_type)"
            )


@dataclass
class JobRecord:
    id: str
    job_type: str
    status: str
    request: dict[str, Any]
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    result: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "request": self.request,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "run_id": self.run_id,
        }


class JobManager:
    def __init__(self, *, max_workers: int, run_store: RunStore) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="arpo-job")
        self._run_store = run_store
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}

    def submit(
        self,
        *,
        job_type: str,
        request: dict[str, Any],
        fn: Callable[[], dict[str, Any]],
        persist_run: bool = True,
    ) -> dict[str, Any]:
        job = JobRecord(id=uuid4().hex, job_type=job_type, status="queued", request=request)
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run_job, job.id, fn, persist_run)
        return job.to_dict()

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def list(self, *, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda job: job.updated_at, reverse=True)
            return [job.to_dict() for job in jobs[: max(1, min(limit, 100))]]

    def _run_job(
        self,
        job_id: str,
        fn: Callable[[], dict[str, Any]],
        persist_run: bool,
    ) -> None:
        self._update(job_id, status="running")
        start = perf_counter()
        try:
            result = fn()
            latency_ms = round((perf_counter() - start) * 1000, 3)
            run_id = None
            if persist_run:
                run = self._run_store.save_run(
                    run_type=self._jobs[job_id].job_type,
                    status="completed",
                    request=self._jobs[job_id].request,
                    response=result,
                    latency_ms=latency_ms,
                )
                run_id = run.get("id")
            self._update(
                job_id,
                status="completed",
                result=result,
                latency_ms=latency_ms,
                run_id=run_id,
            )
        except Exception as exc:  # pragma: no cover - exercised through API integration
            latency_ms = round((perf_counter() - start) * 1000, 3)
            self._run_store.save_run(
                run_type=self._jobs[job_id].job_type,
                status="failed",
                request=self._jobs[job_id].request,
                error=str(exc),
                latency_ms=latency_ms,
            )
            self._update(job_id, status="failed", error=str(exc), latency_ms=latency_ms)

    def _update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = utc_now()


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _json_load(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return json.loads(value)


def _run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "run_type": row["run_type"],
        "status": row["status"],
        "request": _json_load(row["request_json"]) or {},
        "response": _json_load(row["response_json"]),
        "error": row["error"],
        "latency_ms": row["latency_ms"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
