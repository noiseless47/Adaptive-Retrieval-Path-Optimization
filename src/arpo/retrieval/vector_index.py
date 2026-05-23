from __future__ import annotations

import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from arpo.models import Document
from arpo.retrieval.corpus import Corpus
from arpo.retrieval.embeddings import EmbeddingBackend, Vector


INDEX_VERSION = 1


@dataclass(frozen=True)
class VectorRecord:
    document: Document
    vector: Vector


class PersistentVectorIndex:
    """Small local vector index with corpus fingerprint validation."""

    def __init__(
        self,
        *,
        records: list[VectorRecord],
        backend_name: str,
        model_id: str,
        dimensions: int,
        corpus_fingerprint: str,
        index_path: Path | None,
        cache_hit: bool,
    ):
        self.records = records
        self.backend_name = backend_name
        self.model_id = model_id
        self.dimensions = dimensions
        self.corpus_fingerprint = corpus_fingerprint
        self.index_path = index_path
        self.cache_hit = cache_hit

    @classmethod
    def from_corpus(
        cls,
        corpus: Corpus,
        backend: EmbeddingBackend,
        *,
        index_dir: str | Path | None = None,
        use_cache: bool | None = None,
    ) -> "PersistentVectorIndex":
        enabled = _cache_enabled(use_cache)
        fingerprint = corpus_fingerprint(corpus, backend)
        path = _index_path(fingerprint, index_dir=index_dir) if enabled else None

        if path is not None and path.is_file():
            cached = cls._load(path, corpus=corpus, backend=backend, fingerprint=fingerprint)
            if cached is not None:
                return cached

        texts = [_document_text(document) for document in corpus.documents]
        vectors = backend.embed_documents(texts)
        records = [
            VectorRecord(document=document, vector=vector)
            for document, vector in zip(corpus.documents, vectors)
        ]
        index = cls(
            records=records,
            backend_name=backend.name,
            model_id=backend.model_id,
            dimensions=backend.dimensions,
            corpus_fingerprint=fingerprint,
            index_path=path,
            cache_hit=False,
        )
        if path is not None:
            index._save(path)
        return index

    @classmethod
    def _load(
        cls,
        path: Path,
        *,
        corpus: Corpus,
        backend: EmbeddingBackend,
        fingerprint: str,
    ) -> "PersistentVectorIndex | None":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if payload.get("version") != INDEX_VERSION:
            return None
        if payload.get("backend_name") != backend.name:
            return None
        if payload.get("model_id") != backend.model_id:
            return None
        if payload.get("dimensions") != backend.dimensions:
            return None
        if payload.get("corpus_fingerprint") != fingerprint:
            return None

        by_id = {document.id: document for document in corpus.documents}
        records = []
        for item in payload.get("vectors", []):
            document = by_id.get(str(item.get("document_id", "")))
            vector = item.get("vector")
            if document is None or not isinstance(vector, list):
                return None
            records.append(VectorRecord(document=document, vector=[float(value) for value in vector]))

        if len(records) != len(corpus.documents):
            return None

        return cls(
            records=records,
            backend_name=backend.name,
            model_id=backend.model_id,
            dimensions=backend.dimensions,
            corpus_fingerprint=fingerprint,
            index_path=path,
            cache_hit=True,
        )

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": INDEX_VERSION,
            "backend_name": self.backend_name,
            "model_id": self.model_id,
            "dimensions": self.dimensions,
            "corpus_fingerprint": self.corpus_fingerprint,
            "vectors": [
                {
                    "document_id": record.document.id,
                    "vector": [round(value, 8) for value in record.vector],
                }
                for record in self.records
            ],
        }
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        temp_path.replace(path)


def corpus_fingerprint(corpus: Corpus, backend: EmbeddingBackend) -> str:
    digest = sha256()
    digest.update(f"{backend.name}:{backend.model_id}:{backend.dimensions}".encode("utf-8"))
    for document in corpus.documents:
        digest.update(document.id.encode("utf-8"))
        digest.update(document.title.encode("utf-8"))
        digest.update(document.text.encode("utf-8"))
        digest.update(json.dumps(document.metadata, sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()


def _document_text(document: Document) -> str:
    metadata_terms = " ".join(
        str(value)
        for key, value in document.metadata.items()
        if key in {"domain", "keywords", "entities", "source_title"}
    )
    return f"{document.title}\n{metadata_terms}\n{document.text}"


def _cache_enabled(use_cache: bool | None) -> bool:
    if use_cache is not None:
        return use_cache
    raw = os.getenv("ARPO_VECTOR_CACHE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _index_path(fingerprint: str, *, index_dir: str | Path | None) -> Path:
    root = Path(
        index_dir
        or os.getenv("ARPO_VECTOR_INDEX_DIR")
        or Path.cwd() / "data" / "vector-indexes"
    )
    return root.resolve() / f"{fingerprint[:24]}.json"
