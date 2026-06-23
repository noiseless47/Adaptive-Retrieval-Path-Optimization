from __future__ import annotations

import gzip
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TextIO

from arpo.ingestion.pipeline import SourceDocument, build_chunk_documents
from arpo.models import Document


WHITESPACE_RE = re.compile(r"\s+")
S2_FIELD_NAMES = ("paper_id", "corpusid", "corpus_id", "s2_id", "id", "_id")


@dataclass(frozen=True)
class S2ORCConversionReport:
    input_path: str
    output_path: str
    source_documents: int
    chunks: int
    skipped_records: int
    chunk_words: int
    overlap_words: int
    min_chunk_chars: int
    section_level: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "source_documents": self.source_documents,
            "chunks": self.chunks,
            "skipped_records": self.skipped_records,
            "chunk_words": self.chunk_words,
            "overlap_words": self.overlap_words,
            "min_chunk_chars": self.min_chunk_chars,
            "section_level": self.section_level,
        }


def convert_s2orc_to_arpo(
    input_path: str | Path,
    output_path: str | Path,
    *,
    chunk_words: int = 220,
    overlap_words: int = 45,
    min_chunk_chars: int = 120,
    limit: int | None = None,
    section_level: bool = True,
) -> S2ORCConversionReport:
    source_path = Path(input_path).resolve()
    destination = Path(output_path).resolve()

    if not source_path.is_file():
        raise FileNotFoundError(f"S2ORC source file was not found: {source_path}")

    sources: list[SourceDocument] = []
    skipped = 0
    with _open_text(source_path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if limit is not None and len(sources) >= limit:
                break
            if not line.strip():
                continue

            try:
                raw = json.loads(line)
                parsed = s2orc_record_to_sources(raw, fallback_id=f"{source_path.stem}-{line_number}", section_level=section_level)
            except (TypeError, ValueError, json.JSONDecodeError):
                skipped += 1
                continue

            if not parsed:
                skipped += 1
                continue
            sources.extend(parsed)

    if not sources:
        raise ValueError("No usable S2ORC records were found.")

    chunks = build_chunk_documents(
        sources,
        source_path=source_path,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        min_chunk_chars=min_chunk_chars,
    )
    chunks = _attach_s2orc_cross_paper_relations(chunks)
    if not chunks:
        raise ValueError("S2ORC conversion produced no chunks. Check text length and chunk settings.")

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

    return S2ORCConversionReport(
        input_path=source_path.as_posix(),
        output_path=destination.as_posix(),
        source_documents=len(sources),
        chunks=len(chunks),
        skipped_records=skipped,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        min_chunk_chars=min_chunk_chars,
        section_level=section_level,
    )


def s2orc_record_to_sources(
    record: dict[str, Any],
    *,
    fallback_id: str,
    section_level: bool = True,
) -> list[SourceDocument]:
    if not isinstance(record, dict):
        raise ValueError("S2ORC record must be a JSON object.")

    paper_id = _paper_id(record, fallback_id)
    title = _clean_text(str(record.get("title") or record.get("paper_title") or paper_id))
    abstract = _abstract_text(record)
    body_sections = _body_sections(record)
    bib_entries = _bib_entries(record)
    citations = _resolved_citation_ids(record, bib_entries)
    metadata = _metadata(record, paper_id=paper_id, citations=citations)

    if section_level and body_sections:
        return [
            SourceDocument(
                id=f"{paper_id}-section-{index:03d}",
                title=f"{title} - {section_name}",
                text=section_text,
                metadata={
                    **metadata,
                    "source_document_id": paper_id,
                    "source_title": title,
                    "section": section_name,
                    "section_index": index,
                    "section_count": len(body_sections),
                    "section_citations": _section_citations(section_cite_keys, bib_entries),
                },
            )
            for index, (section_name, section_text, section_cite_keys) in enumerate(body_sections, start=1)
            if section_text
        ]

    text_parts = [abstract, *[section_text for _, section_text, _ in body_sections]]
    text = _clean_text(" ".join(part for part in text_parts if part))
    if not text:
        raise ValueError("S2ORC record has no abstract or body text.")

    return [
        SourceDocument(
            id=paper_id,
            title=title,
            text=text,
            metadata=metadata,
        )
    ]


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _paper_id(record: dict[str, Any], fallback_id: str) -> str:
    for field in S2_FIELD_NAMES:
        value = record.get(field)
        if value:
            return _slugify(str(value))
    return _slugify(fallback_id)


def _abstract_text(record: dict[str, Any]) -> str:
    abstract = record.get("abstract")
    if isinstance(abstract, str):
        return _clean_text(abstract)
    if isinstance(abstract, list):
        return _clean_text(" ".join(_span_text(item) for item in abstract))

    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        nested = metadata.get("abstract")
        if isinstance(nested, str):
            return _clean_text(nested)

    return ""


def _body_sections(record: dict[str, Any]) -> list[tuple[str, str, list[str]]]:
    pdf_parse = record.get("pdf_parse")
    if isinstance(pdf_parse, dict):
        body_text = pdf_parse.get("body_text")
        if isinstance(body_text, list):
            return _sections_from_body_text(body_text)

    body_text = record.get("body_text") or record.get("sections")
    if isinstance(body_text, list):
        return _sections_from_body_text(body_text)

    full_text = record.get("full_text") or record.get("text")
    if isinstance(full_text, str) and full_text.strip():
        return [("Full Text", _clean_text(full_text), [])]

    return []


def _sections_from_body_text(body_text: list[Any]) -> list[tuple[str, str, list[str]]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    citations: dict[str, list[str]] = defaultdict(list)

    for index, item in enumerate(body_text, start=1):
        if isinstance(item, str):
            section = "Body"
            text = item
            cite_keys: list[str] = []
        elif isinstance(item, dict):
            section = _section_name(item.get("section") or item.get("section_name"), index=index)
            text = _span_text(item)
            cite_keys = _cite_span_keys(item.get("cite_spans", []))
        else:
            continue

        text = _clean_text(text)
        if not text:
            continue
        grouped[section].append(text)
        citations[section].extend(cite_keys)

    return [
        (section, _clean_text(" ".join(parts)), _dedupe(citations.get(section, [])))
        for section, parts in grouped.items()
        if _clean_text(" ".join(parts))
    ]


def _section_name(value: Any, *, index: int) -> str:
    name = _clean_text(str(value or ""))
    return name if name else f"Section {index}"


def _span_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        value = item.get("text") or item.get("content") or item.get("paragraph")
        return str(value or "")
    return ""


def _cite_span_keys(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    keys: list[str] = []
    for span in value:
        if not isinstance(span, dict):
            continue
        ref_id = span.get("ref_id") or span.get("cite_key") or span.get("bib_entry")
        if ref_id:
            keys.append(str(ref_id))
    return _dedupe(keys)


def _bib_entries(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pdf_parse = record.get("pdf_parse")
    if isinstance(pdf_parse, dict) and isinstance(pdf_parse.get("bib_entries"), dict):
        return {
            str(key): value
            for key, value in pdf_parse["bib_entries"].items()
            if isinstance(value, dict)
        }
    value = record.get("bib_entries")
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items() if isinstance(item, dict)}
    return {}


def _resolved_citation_ids(record: dict[str, Any], bib_entries: dict[str, dict[str, Any]]) -> list[str]:
    candidates: list[str] = []

    for field in ("outbound_citations", "citations", "references"):
        value = record.get(field)
        if isinstance(value, list):
            candidates.extend(_citation_values(value))

    for entry in bib_entries.values():
        linked_id = (
            entry.get("link")
            or entry.get("paper_id")
            or entry.get("corpus_id")
            or entry.get("corpusid")
            or entry.get("s2_id")
        )
        if linked_id:
            candidates.append(str(linked_id))

    return [_slugify(item) for item in _dedupe(candidates)]


def _section_citations(cite_keys: list[str], bib_entries: dict[str, dict[str, Any]]) -> list[str]:
    citations: list[str] = []
    for key in cite_keys:
        entry = bib_entries.get(key)
        if not entry:
            continue
        linked_id = (
            entry.get("link")
            or entry.get("paper_id")
            or entry.get("corpus_id")
            or entry.get("corpusid")
            or entry.get("s2_id")
        )
        if linked_id:
            citations.append(_slugify(str(linked_id)))
    return _dedupe(citations)


def _citation_values(value: Iterable[Any]) -> list[str]:
    citations: list[str] = []
    for item in value:
        if isinstance(item, str | int):
            citations.append(str(item))
        elif isinstance(item, dict):
            for key in ("paper_id", "corpus_id", "corpusid", "s2_id", "id"):
                if item.get(key):
                    citations.append(str(item[key]))
                    break
    return citations


def _metadata(record: dict[str, Any], *, paper_id: str, citations: list[str]) -> dict[str, Any]:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    authors = record.get("authors") or metadata.get("authors") or []
    if isinstance(authors, list):
        authors = [
            str(author.get("name") if isinstance(author, dict) else author)
            for author in authors
            if str(author.get("name") if isinstance(author, dict) else author).strip()
        ]

    year = record.get("year") or metadata.get("year")
    venue = record.get("venue") or metadata.get("venue")
    doi = record.get("doi") or metadata.get("doi")
    fields_of_study = record.get("fields_of_study") or record.get("fieldsOfStudy") or metadata.get("fields_of_study", [])

    return {
        **metadata,
        "source": "S2ORC",
        "source_type": "s2orc",
        "paper_id": paper_id,
        "s2orc_id": paper_id,
        "doi": doi,
        "year": year,
        "venue": venue,
        "authors": authors if isinstance(authors, list) else [],
        "fields_of_study": fields_of_study if isinstance(fields_of_study, list) else [],
        "citations": citations,
        "related_ids": citations,
        "openalex_id": record.get("openalex_id") or metadata.get("openalex_id"),
        "url": record.get("url") or metadata.get("url"),
    }


def _attach_s2orc_cross_paper_relations(documents: list[Document]) -> list[Document]:
    by_source_id: dict[str, list[str]] = defaultdict(list)
    by_document_id = {document.id: document for document in documents}
    for document in documents:
        source_id = str(document.metadata.get("source_document_id") or document.metadata.get("paper_id") or "")
        if source_id:
            by_source_id[_slugify(source_id)].append(document.id)

    enriched: list[Document] = []
    for document in documents:
        metadata = dict(document.metadata)
        related = list(metadata.get("related_ids", []))
        citations = list(metadata.get("citations", []))
        section_citations = list(metadata.get("section_citations", []))
        for cited in [*citations, *section_citations]:
            related.extend(by_source_id.get(_slugify(str(cited)), []))

        valid_related = [
            item
            for item in _dedupe(str(value) for value in related)
            if item in by_document_id and item != document.id
        ]
        metadata["related_ids"] = valid_related[:12]
        metadata["citations"] = [
            item
            for item in _dedupe(str(value) for value in citations)
            if item in by_source_id or item in by_document_id
        ]
        enriched.append(Document(document.id, document.title, document.text, metadata))

    return enriched


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return slug or "document"


def _clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", str(value)).strip()
