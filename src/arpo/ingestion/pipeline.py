from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from arpo.models import Document
from arpo.text import STOPWORDS, tokenize


SUPPORTED_SOURCE_EXTENSIONS = {".jsonl", ".json", ".txt", ".md", ".markdown", ".pdf"}
HEADING_RE = re.compile(r"^\s*#{1,3}\s+(.+?)\s*$", re.MULTILINE)
ENTITY_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9+-]+)(?:\s+(?:[A-Z][A-Za-z0-9+-]+|of|and|for|in)){0,4}")
WHITESPACE_RE = re.compile(r"\s+")
SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class IngestionReport:
    input_path: str
    output_path: str
    source_documents: int
    chunks: int
    chunk_words: int
    overlap_words: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "source_documents": self.source_documents,
            "chunks": self.chunks,
            "chunk_words": self.chunk_words,
            "overlap_words": self.overlap_words,
        }


def ingest_path(
    input_path: str | Path,
    output_path: str | Path,
    *,
    chunk_words: int = 220,
    overlap_words: int = 45,
    min_chunk_chars: int = 120,
) -> IngestionReport:
    """Convert raw research material into ARPO JSONL chunk documents."""

    source_path = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    _validate_ingestion_settings(chunk_words, overlap_words, min_chunk_chars)

    sources = load_source_documents(source_path)
    if not sources:
        raise ValueError("No source documents were found for ingestion.")

    chunks = build_chunk_documents(
        sources,
        source_path=source_path,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        min_chunk_chars=min_chunk_chars,
    )
    if not chunks:
        raise ValueError("Ingestion produced no chunks. Check source text length and chunk settings.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for document in chunks:
            handle.write(
                json.dumps(
                    {
                        "id": document.id,
                        "title": document.title,
                        "text": document.text,
                        "metadata": document.metadata,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            handle.write("\n")

    return IngestionReport(
        input_path=source_path.as_posix(),
        output_path=destination.as_posix(),
        source_documents=len(sources),
        chunks=len(chunks),
        chunk_words=chunk_words,
        overlap_words=overlap_words,
    )


def load_source_documents(path: Path) -> list[SourceDocument]:
    if not path.is_file():
        raise FileNotFoundError(f"Source file was not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SOURCE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_EXTENSIONS))
        raise ValueError(f"Unsupported source type '{suffix}'. Supported extensions: {allowed}")

    if suffix == ".jsonl":
        return _load_jsonl_sources(path)
    if suffix == ".json":
        return _load_json_sources(path)
    if suffix in {".txt", ".md", ".markdown"}:
        return [_plain_text_source(path)]
    if suffix == ".pdf":
        return [_pdf_source(path)]

    raise ValueError(f"Unsupported source type: {suffix}")


def build_chunk_documents(
    sources: Iterable[SourceDocument],
    *,
    source_path: Path,
    chunk_words: int,
    overlap_words: int,
    min_chunk_chars: int,
) -> list[Document]:
    provisional: list[Document] = []
    source_to_chunk_ids: dict[str, list[str]] = {}

    for source in sources:
        source_chunks = _chunk_source(
            source,
            source_path=source_path,
            chunk_words=chunk_words,
            overlap_words=overlap_words,
            min_chunk_chars=min_chunk_chars,
        )
        provisional.extend(source_chunks)
        source_to_chunk_ids[source.id] = [chunk.id for chunk in source_chunks]

    return _attach_chunk_relations(provisional, source_to_chunk_ids)


def _load_jsonl_sources(path: Path) -> list[SourceDocument]:
    sources: list[SourceDocument] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            sources.append(_source_from_record(record, fallback_id=f"{path.stem}-{line_number}"))
    return sources


def _load_json_sources(path: Path) -> list[SourceDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [
            _source_from_record(record, fallback_id=f"{path.stem}-{index}")
            for index, record in enumerate(payload, start=1)
        ]
    if isinstance(payload, dict):
        documents = payload.get("documents")
        if isinstance(documents, list):
            return [
                _source_from_record(record, fallback_id=f"{path.stem}-{index}")
                for index, record in enumerate(documents, start=1)
            ]
        return [_source_from_record(payload, fallback_id=path.stem)]
    raise ValueError("JSON source must be an object, a list of objects, or contain a 'documents' list.")


def _source_from_record(record: Any, *, fallback_id: str) -> SourceDocument:
    if not isinstance(record, dict):
        raise ValueError("Document records must be JSON objects.")

    text_value = record.get("text") or record.get("content") or record.get("abstract") or record.get("body")
    if not text_value:
        raise ValueError("Document record must include text, content, abstract, or body.")

    raw_id = str(record.get("id") or record.get("document_id") or fallback_id)
    title = str(record.get("title") or record.get("name") or raw_id)
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    for key in ("year", "domain", "keywords", "citations", "related_ids", "url", "authors"):
        if key in record and key not in metadata:
            metadata[key] = record[key]

    return SourceDocument(
        id=_slugify(raw_id),
        title=_clean_text(title),
        text=_clean_text(str(text_value)),
        metadata=dict(metadata),
    )


def _plain_text_source(path: Path) -> SourceDocument:
    text = _clean_text(path.read_text(encoding="utf-8"))
    heading = HEADING_RE.search(text)
    title = heading.group(1).strip() if heading else path.stem.replace("-", " ").replace("_", " ").title()
    return SourceDocument(
        id=_slugify(path.stem),
        title=title,
        text=text,
        metadata={"source_type": path.suffix.lower().lstrip(".")},
    )


def _pdf_source(path: Path) -> SourceDocument:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise ValueError("PDF ingestion requires the optional dependency: pip install pypdf") from exc

    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[Page {index}]\n{page_text}")

    text = _clean_text("\n\n".join(pages))
    if not text:
        raise ValueError("No extractable text found in PDF.")

    return SourceDocument(
        id=_slugify(path.stem),
        title=path.stem.replace("-", " ").replace("_", " ").title(),
        text=text,
        metadata={"source_type": "pdf", "page_count": len(reader.pages)},
    )


def _chunk_source(
    source: SourceDocument,
    *,
    source_path: Path,
    chunk_words: int,
    overlap_words: int,
    min_chunk_chars: int,
) -> list[Document]:
    words = source.text.split()
    if not words:
        return []

    spans: list[tuple[int, int]] = []
    if len(words) <= chunk_words:
        spans.append((0, len(words)))
    else:
        start = 0
        while start < len(words):
            end = min(len(words), start + chunk_words)
            spans.append((start, end))
            if end == len(words):
                break
            start = max(end - overlap_words, start + 1)

    documents: list[Document] = []
    chunk_count = len(spans)
    base_metadata = dict(source.metadata)
    raw_keywords = _coerce_string_list(base_metadata.get("keywords"))
    source_entities = _extract_entities(f"{source.title} {source.text}")

    for index, (start, end) in enumerate(spans, start=1):
        chunk_text = _clean_text(" ".join(words[start:end]))
        if len(chunk_text) < min_chunk_chars and chunk_count > 1:
            continue

        chunk_id = source.id if chunk_count == 1 else f"{source.id}-chunk-{index:03d}"
        keywords = _keywords(chunk_text, seed=raw_keywords)
        entities = _extract_entities(chunk_text, seed=source_entities)
        metadata = {
            **base_metadata,
            "source_file": source_path.name,
            "source_path": source_path.as_posix(),
            "source_document_id": source.id,
            "source_title": source.title,
            "chunk_index": index,
            "chunk_count": chunk_count,
            "chunk_start_word": start,
            "chunk_end_word": end,
            "keywords": keywords,
            "entities": entities,
            "citations": _coerce_string_list(base_metadata.get("citations")),
            "related_ids": _coerce_string_list(base_metadata.get("related_ids")),
        }
        documents.append(
            Document(
                id=chunk_id,
                title=source.title if chunk_count == 1 else f"{source.title} - Chunk {index}",
                text=chunk_text,
                metadata=metadata,
            )
        )

    return documents


def _attach_chunk_relations(
    documents: list[Document],
    source_to_chunk_ids: dict[str, list[str]],
    *,
    max_related: int = 8,
) -> list[Document]:
    by_id = {document.id: document for document in documents}
    keyword_index: dict[str, set[str]] = defaultdict(set)
    for document in documents:
        for keyword in _coerce_string_list(document.metadata.get("keywords")):
            keyword_index[keyword.lower()].add(document.id)

    enriched: list[Document] = []
    for document in documents:
        related: list[str] = []
        source_id = str(document.metadata.get("source_document_id", ""))
        siblings = source_to_chunk_ids.get(source_id, [])
        if document.id in siblings:
            position = siblings.index(document.id)
            for neighbor in (position - 1, position + 1):
                if 0 <= neighbor < len(siblings):
                    related.append(siblings[neighbor])

        for key in ("related_ids", "citations"):
            for raw_id in _coerce_string_list(document.metadata.get(key)):
                related.extend(source_to_chunk_ids.get(_slugify(raw_id), [raw_id]))

        scores: Counter[str] = Counter()
        for keyword in _coerce_string_list(document.metadata.get("keywords")):
            for candidate_id in keyword_index.get(keyword.lower(), set()):
                if candidate_id != document.id:
                    scores[candidate_id] += 1
        related.extend([candidate_id for candidate_id, _ in scores.most_common(max_related)])

        deduped = _dedupe([item for item in related if item in by_id and item != document.id])
        metadata = dict(document.metadata)
        metadata["related_ids"] = deduped[:max_related]
        metadata["citations"] = [item for item in _coerce_string_list(metadata.get("citations")) if item in by_id]
        enriched.append(Document(document.id, document.title, document.text, metadata))

    return enriched


def _validate_ingestion_settings(chunk_words: int, overlap_words: int, min_chunk_chars: int) -> None:
    if chunk_words < 40:
        raise ValueError("chunk_words must be at least 40.")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative.")
    if overlap_words >= chunk_words:
        raise ValueError("overlap_words must be smaller than chunk_words.")
    if min_chunk_chars < 0:
        raise ValueError("min_chunk_chars cannot be negative.")


def _keywords(text: str, *, seed: list[str], limit: int = 12) -> list[str]:
    counts = Counter(tokenize(text))
    seeded = [keyword.lower() for keyword in seed if keyword]
    ranked = [token for token, _ in counts.most_common(limit * 2) if token not in STOPWORDS and len(token) > 2]
    return _dedupe([*seeded, *ranked])[:limit]


def _extract_entities(text: str, *, seed: list[str] | None = None, limit: int = 10) -> list[str]:
    entities = list(seed or [])
    for match in ENTITY_RE.finditer(text):
        value = match.group(0).strip()
        if len(value) < 3 or value.lower() in STOPWORDS:
            continue
        if sum(1 for char in value if char.isupper()) == 0:
            continue
        entities.append(value)
    return _dedupe(entities)[:limit]


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _slugify(value: str) -> str:
    slug = SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "document"


def _clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()
