from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPENALEX_WORKS_URL = "https://api.openalex.org/works"


DEFAULT_TOPICS = [
    "retrieval augmented generation hallucination",
    "multi hop question answering retrieval",
    "graph retrieval information retrieval",
    "query decomposition complex search",
    "confidence pruning retrieval",
    "adaptive reranking retrieval",
    "vision transformers medical imaging inference cost",
    "transformers replacing convolutional neural networks medical imaging",
]


@dataclass(frozen=True)
class HarvestReport:
    output_path: str
    raw_path: str
    topics: list[str]
    requested_per_topic: int
    records: int
    skipped_without_abstract: int
    source: str = "OpenAlex"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "topics": self.topics,
            "requested_per_topic": self.requested_per_topic,
            "records": self.records,
            "skipped_without_abstract": self.skipped_without_abstract,
            "raw_path": self.raw_path,
            "output_path": self.output_path,
        }


def harvest_openalex(
    output_path: str | Path,
    *,
    raw_path: str | Path | None = None,
    topics: list[str] | None = None,
    per_topic: int = 50,
    mailto: str | None = None,
    year_from: int = 2018,
    sleep_seconds: float = 0.12,
) -> HarvestReport:
    """Harvest paper metadata and abstracts from OpenAlex into ARPO JSONL."""

    selected_topics = topics or DEFAULT_TOPICS
    if per_topic < 1:
        raise ValueError("per_topic must be at least 1.")

    output = Path(output_path)
    raw = Path(raw_path) if raw_path is not None else output.with_suffix(".openalex-raw.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    raw.parent.mkdir(parents=True, exist_ok=True)

    by_id: dict[str, dict[str, Any]] = {}
    raw_records: list[dict[str, Any]] = []
    skipped_without_abstract = 0

    for topic in selected_topics:
        works = _fetch_topic(topic, per_topic=per_topic, mailto=mailto, year_from=year_from)
        raw_records.extend(works)
        for work in works:
            document = _work_to_document(work, topic)
            if document is None:
                skipped_without_abstract += 1
                continue
            by_id.setdefault(document["id"], document)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    documents = _attach_relations(list(by_id.values()))
    documents.sort(key=lambda item: (item["metadata"].get("year", 0), item["id"]), reverse=True)

    with raw.open("w", encoding="utf-8") as handle:
        for record in raw_records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")

    with output.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(document, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    return HarvestReport(
        output_path=output.as_posix(),
        raw_path=raw.as_posix(),
        topics=selected_topics,
        requested_per_topic=per_topic,
        records=len(documents),
        skipped_without_abstract=skipped_without_abstract,
    )


def _fetch_topic(topic: str, *, per_topic: int, mailto: str | None, year_from: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor = "*"
    per_page = min(200, per_topic)

    while len(results) < per_topic:
        params = {
            "search": topic,
            "filter": f"from_publication_date:{year_from}-01-01,type:article|preprint",
            "per-page": str(min(per_page, per_topic - len(results))),
            "cursor": cursor,
            "sort": "cited_by_count:desc",
        }
        if mailto:
            params["mailto"] = mailto

        payload = _get_json(f"{OPENALEX_WORKS_URL}?{urlencode(params)}")
        page_results = payload.get("results", [])
        if not page_results:
            break
        results.extend(page_results)
        next_cursor = payload.get("meta", {}).get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return results[:per_topic]


def _get_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ARPO-Studio/0.1 (research corpus builder)",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is fixed OpenAlex API.
        return json.loads(response.read().decode("utf-8"))


def _work_to_document(work: dict[str, Any], topic: str) -> dict[str, Any] | None:
    abstract = _abstract_from_inverted_index(work.get("abstract_inverted_index"))
    if not abstract:
        return None

    openalex_id = str(work.get("id") or "")
    local_id = _local_openalex_id(openalex_id)
    title = str(work.get("display_name") or local_id)
    year = work.get("publication_year")
    concepts = work.get("concepts") or []
    authorships = work.get("authorships") or []
    keywords = _keywords(work, topic)
    referenced_works = [_local_openalex_id(str(value)) for value in work.get("referenced_works", [])]
    related_works = [_local_openalex_id(str(value)) for value in work.get("related_works", [])]
    source = _source_name(work)

    return {
        "id": local_id,
        "title": title,
        "text": abstract,
        "metadata": {
            "source": "OpenAlex",
            "openalex_id": openalex_id,
            "doi": work.get("doi"),
            "url": work.get("id"),
            "year": year,
            "domain": topic,
            "venue": source,
            "cited_by_count": work.get("cited_by_count", 0),
            "open_access": work.get("open_access", {}),
            "authors": [
                authorship.get("author", {}).get("display_name")
                for authorship in authorships[:8]
                if authorship.get("author", {}).get("display_name")
            ],
            "keywords": keywords,
            "concepts": [
                concept.get("display_name")
                for concept in concepts[:12]
                if concept.get("display_name")
            ],
            "citations": referenced_works,
            "related_ids": related_works,
            "harvest_query": topic,
        },
    }


def _attach_relations(documents: list[dict[str, Any]], *, max_related: int = 12) -> list[dict[str, Any]]:
    ids = {document["id"] for document in documents}
    keyword_index: dict[str, set[str]] = {}
    for document in documents:
        for keyword in document["metadata"].get("keywords", []):
            keyword_index.setdefault(str(keyword).lower(), set()).add(document["id"])

    enriched = []
    for document in documents:
        metadata = dict(document["metadata"])
        relations = []
        for key in ("citations", "related_ids"):
            relations.extend([item for item in metadata.get(key, []) if item in ids])

        scores: dict[str, int] = {}
        for keyword in metadata.get("keywords", []):
            for candidate_id in keyword_index.get(str(keyword).lower(), set()):
                if candidate_id != document["id"]:
                    scores[candidate_id] = scores.get(candidate_id, 0) + 1
        relations.extend(
            candidate_id
            for candidate_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        )

        metadata["related_ids"] = _dedupe(relations)[:max_related]
        metadata["citations"] = [item for item in metadata.get("citations", []) if item in ids]
        enriched.append({**document, "metadata": metadata})

    return enriched


def _abstract_from_inverted_index(value: Any) -> str:
    if not isinstance(value, dict):
        return ""

    positions: dict[int, str] = {}
    for token, indexes in value.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            try:
                positions[int(index)] = str(token)
            except (TypeError, ValueError):
                continue
    return " ".join(positions[index] for index in sorted(positions)).strip()


def _keywords(work: dict[str, Any], topic: str) -> list[str]:
    keywords = [topic]
    keywords.extend(str(keyword.get("display_name")) for keyword in work.get("keywords", [])[:8])
    keywords.extend(str(concept.get("display_name")) for concept in work.get("concepts", [])[:8])
    primary_topic = work.get("primary_topic") or {}
    if primary_topic.get("display_name"):
        keywords.append(str(primary_topic["display_name"]))
    return _dedupe(keyword for keyword in keywords if keyword and keyword != "None")[:14]


def _source_name(work: dict[str, Any]) -> str | None:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("display_name")


def _local_openalex_id(value: str) -> str:
    return value.rstrip("/").rsplit("/", maxsplit=1)[-1].lower() if value else ""


def _dedupe(values: Any) -> list[str]:
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
