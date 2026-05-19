from __future__ import annotations

import argparse
import json
from pathlib import Path

from arpo.pipeline import ARPOPipeline
from arpo.retrieval import Corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ARPO adaptive retrieval pipeline.")
    parser.add_argument("--query", required=True, help="User query to retrieve evidence for.")
    parser.add_argument("--corpus", default="examples/corpus.jsonl", help="Path to a JSONL corpus.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of final evidence nodes.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    corpus = Corpus.from_jsonl(Path(args.corpus))
    pipeline = ARPOPipeline.from_corpus(corpus)
    result = pipeline.run(args.query, top_k=args.top_k)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print(result.answer)
    print()
    print("Top evidence:")
    for node in result.ranked_evidence:
        print(f"- {node.document.id}: {node.document.title} (confidence={node.confidence:.2f})")


if __name__ == "__main__":
    main()

