from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from arpo.retrieval import Corpus
from arpo.retrieval.embeddings import build_embedding_backend
from arpo.retrieval.vector_index import PersistentVectorIndex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or refresh an ARPO dense vector index.")
    parser.add_argument("--corpus", default="examples/corpus.jsonl", help="Path to an ARPO JSONL corpus.")
    parser.add_argument(
        "--backend",
        default=os.getenv("ARPO_EMBEDDING_BACKEND", "hash"),
        choices=["hash", "sentence-transformers"],
        help="Embedding backend to use.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("ARPO_EMBEDDING_MODEL"),
        help="SentenceTransformers model id when using the sentence-transformers backend.",
    )
    parser.add_argument(
        "--index-dir",
        default=os.getenv("ARPO_VECTOR_INDEX_DIR", "data/vector-indexes"),
        help="Directory for persistent vector index files.",
    )
    parser.add_argument("--no-cache", action="store_true", help="Build in memory without writing an index file.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    corpus = Corpus.from_jsonl(Path(args.corpus))
    backend = build_embedding_backend(args.backend, model_id=args.model)
    index = PersistentVectorIndex.from_corpus(
        corpus,
        backend,
        index_dir=args.index_dir,
        use_cache=not args.no_cache,
    )
    print(
        json.dumps(
            {
                "corpus": args.corpus,
                "documents": len(index.records),
                "embedding_backend": index.backend_name,
                "embedding_model": index.model_id,
                "dimensions": index.dimensions,
                "cache_hit": index.cache_hit,
                "index_path": str(index.index_path) if index.index_path else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
