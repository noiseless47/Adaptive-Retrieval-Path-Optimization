from __future__ import annotations

import math
import re
from collections import Counter
from hashlib import blake2b
from typing import Iterable


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "where",
    "which",
    "while",
    "with",
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str, *, keep_stopwords: bool = False) -> list[str]:
    tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
    if keep_stopwords:
        return tokens
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def normalize_score(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))


def lexical_overlap(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[index] * right[index] for index in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def hashed_vector(text: str, *, dimensions: int = 256) -> dict[int, float]:
    tokens = tokenize(text)
    features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    counts = Counter(features)
    vector: dict[int, float] = {}
    for feature, count in counts.items():
        digest = blake2b(feature.encode("utf-8"), digest_size=4).digest()
        index = int.from_bytes(digest, "big") % dimensions
        sign = -1.0 if digest[0] & 1 else 1.0
        vector[index] = vector.get(index, 0.0) + sign * (1.0 + math.log(count))
    return vector


def split_sentences(text: str) -> list[str]:
    sentences = [sentence.strip() for sentence in SENTENCE_RE.split(text.strip())]
    return [sentence for sentence in sentences if sentence]


def best_snippets(text: str, query: str, *, limit: int = 2) -> list[str]:
    query_terms = tokenize(query)
    ranked = []
    for sentence in split_sentences(text):
        score = lexical_overlap(query_terms, tokenize(sentence))
        ranked.append((score, sentence))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [sentence for score, sentence in ranked[:limit] if score > 0]


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))
