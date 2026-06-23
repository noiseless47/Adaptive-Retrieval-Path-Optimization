from __future__ import annotations

import argparse
import json
from pathlib import Path

from arpo.corpus_quality import corpus_quality_report
from arpo.retrieval import Corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect ARPO corpus quality and metadata coverage.")
    parser.add_argument("corpus", help="Path to an ARPO JSONL corpus.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    corpus = Corpus.from_jsonl(corpus_path)
    report = corpus_quality_report(corpus)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print(f"Corpus: {corpus_path}")
    print(f"Documents: {report['document_count']}")
    print(f"Average text length: {report['average_text_tokens']} tokens")
    print(f"Duplicate titles: {report['duplicate_title_count']}")
    print(f"Duplicate texts: {report['duplicate_text_count']}")
    print(f"Citation edges: {report['citation_edges']}")
    print(f"Related edges: {report['related_edges']}")
    if report["year_min"] and report["year_max"]:
        print(f"Year range: {report['year_min']} - {report['year_max']}")


if __name__ == "__main__":
    main()
