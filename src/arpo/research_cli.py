from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from arpo.evaluation.benchmarks import load_benchmark_records
from arpo.evaluation.claim_study import run_claim_study
from arpo.evaluation.variants import DEFAULT_VARIANTS
from arpo.retrieval import Corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a research claim study with baselines, ablations, and statistics."
    )
    parser.add_argument("--config", help="Optional JSON experiment config.")
    parser.add_argument("--corpus", default="data/arpo-openalex-corpus.jsonl", help="Corpus JSONL path.")
    parser.add_argument("--queries", default="data/arpo-openalex-queries.jsonl", help="Query set path.")
    parser.add_argument("--benchmark", default="auto", help="auto, native, hotpotqa, scifact, or beir.")
    parser.add_argument("--split", default="test", help="Benchmark split for BEIR-style datasets.")
    parser.add_argument("--top-k", type=int, default=5, help="Evaluation cutoff.")
    parser.add_argument("--output-dir", default="data/experiments", help="Artifact output directory.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = _load_config(args.config)
    corpus_path = Path(config.get("corpus_path", args.corpus))
    queries_path = Path(config.get("queries_path", args.queries))
    benchmark = str(config.get("benchmark", args.benchmark))
    split = str(config.get("split", args.split))
    top_k = int(config.get("top_k", args.top_k))
    variants = config.get("variants", list(DEFAULT_VARIANTS))
    output_dir = Path(config.get("output_dir", args.output_dir))

    corpus = Corpus.from_jsonl(corpus_path)
    records, benchmark_report = load_benchmark_records(
        queries_path,
        benchmark=benchmark,
        split=split,
    )
    report = run_claim_study(
        corpus,
        records,
        top_k=top_k,
        variants=variants,
        benchmark=benchmark_report,
        artifact_dir=output_dir,
        corpus_path=corpus_path.as_posix(),
        queries_path=queries_path.as_posix(),
    )

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"ARPO claim study: {report['study_id']}")
    print(f"Benchmark: {report['benchmark']['name']} ({report['benchmark']['query_count']} queries)")
    print("Artifacts:")
    for label, path in report.get("artifacts", {}).items():
        print(f"  {label}: {path}")
    print("Claim verdicts:")
    for verdict in report["claim_verdicts"]:
        print(f"  [{verdict['status']}] {verdict['claim']}")


def _load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
