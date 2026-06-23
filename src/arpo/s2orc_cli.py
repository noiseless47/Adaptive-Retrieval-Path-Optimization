from __future__ import annotations

import argparse
import json

from arpo.datasets.s2orc import convert_s2orc_to_arpo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert local S2ORC JSONL/JSONL.GZ shards into an ARPO evidence corpus."
    )
    parser.add_argument("input", help="S2ORC shard path: .jsonl or .jsonl.gz.")
    parser.add_argument(
        "output",
        nargs="?",
        default="data/arpo-s2orc-corpus.jsonl",
        help="Destination ARPO JSONL corpus.",
    )
    parser.add_argument("--chunk-words", type=int, default=220, help="Target words per chunk.")
    parser.add_argument("--overlap-words", type=int, default=45, help="Overlapping words between chunks.")
    parser.add_argument("--min-chunk-chars", type=int, default=120, help="Drop tiny chunks below this size.")
    parser.add_argument("--limit", type=int, help="Maximum S2ORC records to convert.")
    parser.add_argument(
        "--paper-level",
        action="store_true",
        help="Create paper-level chunks instead of preserving section-level source documents.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = convert_s2orc_to_arpo(
        args.input,
        args.output,
        chunk_words=args.chunk_words,
        overlap_words=args.overlap_words,
        min_chunk_chars=args.min_chunk_chars,
        limit=args.limit,
        section_level=not args.paper_level,
    )
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
