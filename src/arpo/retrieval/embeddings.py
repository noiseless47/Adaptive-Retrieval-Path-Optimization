from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from typing import Protocol

from arpo.text import hashed_vector


Vector = list[float]


class EmbeddingBackend(Protocol):
    name: str
    model_id: str
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        ...

    def embed_query(self, text: str) -> Vector:
        ...


class HashEmbeddingBackend:
    """Deterministic dependency-free embedding backend for local tests and demos."""

    name = "hash"

    def __init__(self, *, dimensions: int = 512):
        self.dimensions = dimensions
        self.model_id = f"hashing-vectorizer-{dimensions}"

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        return [_sparse_hash_to_dense(text, dimensions=self.dimensions) for text in texts]

    def embed_query(self, text: str) -> Vector:
        return _sparse_hash_to_dense(text, dimensions=self.dimensions)


class SentenceTransformerEmbeddingBackend:
    """SentenceTransformers embedding backend, loaded lazily only when configured."""

    name = "sentence-transformers"

    def __init__(self, model_id: str = "BAAI/bge-small-en-v1.5", *, batch_size: int = 32):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "SentenceTransformers backend requires: pip install -e .[ml]"
            ) from exc

        self.model_id = model_id
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_id)
        dimension = self.model.get_sentence_embedding_dimension()
        self.dimensions = int(dimension or 0)

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        return self._encode(texts)

    def embed_query(self, text: str) -> Vector:
        return self._encode([text])[0]

    def _encode(self, texts: Sequence[str]) -> list[Vector]:  # pragma: no cover - optional dependency
        embeddings = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            convert_to_numpy=False,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in embedding] for embedding in embeddings]


def build_embedding_backend(
    backend: str | None = None,
    *,
    model_id: str | None = None,
    dimensions: int | None = None,
) -> EmbeddingBackend:
    selected = (backend or os.getenv("ARPO_EMBEDDING_BACKEND") or "hash").strip().lower()

    if selected in {"hash", "hashed", "local"}:
        return HashEmbeddingBackend(dimensions=dimensions or _int_env("ARPO_HASH_EMBEDDING_DIMENSIONS", 512))

    if selected in {"sentence-transformers", "sentence_transformers", "st"}:
        return SentenceTransformerEmbeddingBackend(
            model_id=model_id or os.getenv("ARPO_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
            batch_size=_int_env("ARPO_EMBEDDING_BATCH_SIZE", 32),
        )

    raise ValueError(
        "Unsupported embedding backend. Use 'hash' or 'sentence-transformers'."
    )


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0
    common = min(len(left), len(right))
    numerator = sum(left[index] * right[index] for index in range(common))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _sparse_hash_to_dense(text: str, *, dimensions: int) -> Vector:
    sparse = hashed_vector(text, dimensions=dimensions)
    vector = [0.0] * dimensions
    for index, value in sparse.items():
        vector[index] = value
    return _normalize(vector)


def _normalize(vector: Iterable[float]) -> Vector:
    values = [float(value) for value in vector]
    norm = sum(value * value for value in values) ** 0.5
    if norm == 0:
        return values
    return [value / norm for value in values]


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
