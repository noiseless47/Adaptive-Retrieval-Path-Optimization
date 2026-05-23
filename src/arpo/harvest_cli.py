from __future__ import annotations

import argparse
import json

from arpo.datasets.openalex import DEFAULT_TOPICS, harvest_openalex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest scholarly paper metadata for ARPO corpora.")
    parser.add_argument(
        "--output",
        default="data/arpo-openalex-corpus.jsonl",
        help="Destination ARPO JSONL corpus.",
    )
    parser.add_argument(
        "--raw-output",
        default="data/raw/openalex-works.jsonl",
        help="Destination raw OpenAlex response JSONL.",
    )
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics",
        help="Search topic. Repeat to add multiple topics. Defaults to ARPO research topics.",
    )
    parser.add_argument("--per-topic", type=int, default=50, help="Maximum works per topic.")
    parser.add_argument("--year-from", type=int, default=2018, help="Earliest publication year.")
    parser.add_argument("--mailto", help="Optional email for OpenAlex polite pool.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = harvest_openalex(
        args.output,
        raw_path=args.raw_output,
        topics=args.topics or DEFAULT_TOPICS,
        per_topic=args.per_topic,
        mailto=args.mailto,
        year_from=args.year_from,
    )
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
