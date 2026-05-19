from __future__ import annotations

import argparse
import json
from pathlib import Path

from arpo.evaluation.runner import evaluate_pipeline, load_query_records
from arpo.retrieval import Corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate ARPO on a JSONL query set.")
    parser.add_argument("--corpus", default="examples/corpus.jsonl", help="Path to JSONL corpus.")
    parser.add_argument("--queries", default="examples/queries.jsonl", help="Path to JSONL query set.")
    parser.add_argument("--top-k", type=int, default=5, help="Evaluation cutoff.")
    parser.add_argument("--json", action="store_true", help="Print full JSON evaluation report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    corpus = Corpus.from_jsonl(Path(args.corpus))
    records = load_query_records(Path(args.queries))
    report = evaluate_pipeline(corpus, records, top_k=args.top_k)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"ARPO evaluation over {report['query_count']} queries at k={report['top_k']}")
    print(f"Precision@K: {report['precision_at_k']:.3f}")
    print(f"Recall@K:    {report['recall_at_k']:.3f}")
    print(f"NDCG@K:      {report['ndcg_at_k']:.3f}")
    print(f"MRR:         {report['mrr']:.3f}")


if __name__ == "__main__":
    main()

