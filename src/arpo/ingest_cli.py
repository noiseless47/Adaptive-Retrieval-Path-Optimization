from __future__ import annotations

import argparse
import json

from arpo.ingestion import ingest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest raw research material into an ARPO JSONL corpus.")
    parser.add_argument("input", help="Source file: .jsonl, .json, .txt, .md, .markdown, or .pdf.")
    parser.add_argument("output", help="Destination ARPO corpus JSONL path.")
    parser.add_argument("--chunk-words", type=int, default=220, help="Target words per chunk.")
    parser.add_argument("--overlap-words", type=int, default=45, help="Overlapping words between adjacent chunks.")
    parser.add_argument("--min-chunk-chars", type=int, default=120, help="Drop tiny trailing chunks below this size.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = ingest_path(
        args.input,
        args.output,
        chunk_words=args.chunk_words,
        overlap_words=args.overlap_words,
        min_chunk_chars=args.min_chunk_chars,
    )
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
