from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arpo.evaluation.runner import QueryRecord, load_query_records


@dataclass(frozen=True)
class BenchmarkLoadReport:
    name: str
    source_path: str
    query_count: int
    relevant_judgement_count: int
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_path": self.source_path,
            "query_count": self.query_count,
            "relevant_judgement_count": self.relevant_judgement_count,
            "warnings": list(self.warnings),
        }


def load_benchmark_records(
    path: str | Path,
    *,
    benchmark: str = "auto",
    split: str = "test",
) -> tuple[list[QueryRecord], BenchmarkLoadReport]:
    source = Path(path)
    benchmark = benchmark.lower().strip()

    if benchmark == "auto":
        benchmark = infer_benchmark_format(source)

    if benchmark in {"native", "arpo", "jsonl"}:
        records = load_query_records(source)
        return records, _report("native", source, records)

    if benchmark == "hotpotqa":
        records = _load_hotpotqa(source)
        return records, _report("hotpotqa", source, records)

    if benchmark == "scifact":
        records = _load_scifact_claims(source)
        return records, _report("scifact", source, records)

    if benchmark == "beir":
        records = _load_beir(source, split=split)
        return records, _report("beir", source, records)

    raise ValueError(
        "Unsupported benchmark format. Use one of: auto, native, hotpotqa, scifact, beir."
    )


def infer_benchmark_format(path: Path) -> str:
    if path.is_dir():
        return "beir"

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        first = _first_json_record(path)
        if "query" in first and "relevant_ids" in first:
            return "native"
        if "claim" in first and ("cited_doc_ids" in first or "evidence" in first):
            return "scifact"
        if "question" in first and "supporting_facts" in first:
            return "hotpotqa"
        return "native"

    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        first = raw[0] if isinstance(raw, list) and raw else raw
        if isinstance(first, dict) and "question" in first and "supporting_facts" in first:
            return "hotpotqa"
        if isinstance(first, dict) and "query" in first and "relevant_ids" in first:
            return "native"

    return "native"


def _load_hotpotqa(path: Path) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    for index, raw in enumerate(_iter_json_records(path), start=1):
        question = str(raw.get("question", "")).strip()
        if not question:
            continue

        relevant = _hotpot_supporting_titles(raw.get("supporting_facts", []))
        if not relevant:
            relevant = {str(item) for item in raw.get("relevant_ids", [])}

        records.append(
            QueryRecord(
                id=str(raw.get("_id") or raw.get("id") or f"hotpotqa-{index}"),
                query=question,
                relevant_ids=relevant,
                graded_relevance={document_id: 1.0 for document_id in relevant},
            )
        )
    return records


def _hotpot_supporting_titles(value: Any) -> set[str]:
    relevant: set[str] = set()
    if not isinstance(value, list):
        return relevant

    for item in value:
        if isinstance(item, list | tuple) and item:
            relevant.add(str(item[0]))
        elif isinstance(item, dict):
            title = item.get("title") or item.get("document_id") or item.get("doc_id")
            if title:
                relevant.add(str(title))
    return relevant


def _load_scifact_claims(path: Path) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    for index, raw in enumerate(_iter_json_records(path), start=1):
        claim = str(raw.get("claim", "")).strip()
        if not claim:
            continue

        relevant = {str(document_id) for document_id in raw.get("cited_doc_ids", [])}
        evidence = raw.get("evidence", {})
        if isinstance(evidence, dict):
            relevant.update(str(document_id) for document_id in evidence)
        elif isinstance(evidence, list):
            relevant.update(_scifact_evidence_list_ids(evidence))

        records.append(
            QueryRecord(
                id=str(raw.get("id") or f"scifact-{index}"),
                query=claim,
                relevant_ids=relevant,
                graded_relevance={document_id: 1.0 for document_id in relevant},
            )
        )
    return records


def _scifact_evidence_list_ids(value: list[Any]) -> set[str]:
    relevant: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            document_id = item.get("doc_id") or item.get("document_id") or item.get("cited_doc_id")
            if document_id:
                relevant.add(str(document_id))
    return relevant


def _load_beir(path: Path, *, split: str) -> list[QueryRecord]:
    if not path.is_dir():
        raise ValueError("BEIR loading expects a dataset directory.")

    queries = _read_beir_queries(path / "queries.jsonl")
    qrels_path = _find_beir_qrels(path, split)
    records_by_query: dict[str, dict[str, float]] = {}

    with qrels_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            if line_number == 1 and "query-id" in line.lower():
                continue
            parts = line.strip().replace("\t", " ").split()
            if len(parts) < 3:
                continue
            query_id, document_id, score = parts[0], parts[1], parts[-1]
            try:
                relevance = float(score)
            except ValueError:
                relevance = 1.0
            if relevance <= 0:
                continue
            records_by_query.setdefault(query_id, {})[document_id] = relevance

    records: list[QueryRecord] = []
    for query_id, graded in sorted(records_by_query.items()):
        query = queries.get(query_id)
        if not query:
            continue
        records.append(
            QueryRecord(
                id=query_id,
                query=query,
                relevant_ids=set(graded),
                graded_relevance=graded,
            )
        )
    return records


def _read_beir_queries(path: Path) -> dict[str, str]:
    queries: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            query_id = str(raw.get("_id") or raw.get("id"))
            text = str(raw.get("text") or raw.get("query") or "").strip()
            if query_id and text:
                queries[query_id] = text
    return queries


def _find_beir_qrels(path: Path, split: str) -> Path:
    candidates = [
        path / "qrels" / f"{split}.tsv",
        path / "qrels" / f"{split}.txt",
        path / f"qrels.{split}.tsv",
        path / "qrels.tsv",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find BEIR qrels for split '{split}' in {path}.")


def _iter_json_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [record for record in raw if isinstance(record, dict)]
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)]
    raise ValueError(f"Unsupported JSON benchmark structure in {path}.")


def _first_json_record(path: Path) -> dict[str, Any]:
    for record in _iter_json_records(path):
        return record
    return {}


def _report(name: str, path: Path, records: list[QueryRecord]) -> BenchmarkLoadReport:
    warnings: list[str] = []
    missing_qrels = sum(1 for record in records if not record.relevant_ids)
    if missing_qrels:
        warnings.append(f"{missing_qrels} queries have no relevant document judgements.")

    return BenchmarkLoadReport(
        name=name,
        source_path=path.as_posix(),
        query_count=len(records),
        relevant_judgement_count=sum(len(record.relevant_ids) for record in records),
        warnings=tuple(warnings),
    )
