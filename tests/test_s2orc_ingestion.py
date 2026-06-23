from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from arpo.datasets.s2orc import convert_s2orc_to_arpo, s2orc_record_to_sources
from arpo.retrieval import Corpus


class S2ORCIngestionTests(unittest.TestCase):
    def test_s2orc_record_preserves_sections_and_citations(self) -> None:
        record = _s2orc_record()

        sources = s2orc_record_to_sources(record, fallback_id="fallback", section_level=True)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].metadata["source"], "S2ORC")
        self.assertEqual(sources[0].metadata["section"], "Introduction")
        self.assertEqual(sources[0].metadata["section_citations"], ["paper-b"])
        self.assertEqual(sources[1].metadata["section"], "Methods")

    def test_convert_s2orc_jsonl_to_arpo_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "s2orc.jsonl"
            output = Path(temp_dir) / "arpo-s2orc.jsonl"
            source.write_text(json.dumps(_s2orc_record()) + "\n", encoding="utf-8")

            report = convert_s2orc_to_arpo(
                source,
                output,
                chunk_words=45,
                overlap_words=8,
                min_chunk_chars=0,
            )
            corpus = Corpus.from_jsonl(output)

        self.assertEqual(report.source_documents, 2)
        self.assertGreaterEqual(len(corpus), 2)
        self.assertTrue(all(document.metadata["source"] == "S2ORC" for document in corpus.documents))
        self.assertTrue(any(document.metadata.get("section") == "Introduction" for document in corpus.documents))

    def test_convert_s2orc_gzip_shard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "s2orc.jsonl.gz"
            output = Path(temp_dir) / "arpo-s2orc.jsonl"
            with gzip.open(source, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(_s2orc_record()) + "\n")

            report = convert_s2orc_to_arpo(
                source,
                output,
                chunk_words=45,
                overlap_words=8,
                min_chunk_chars=0,
                limit=1,
            )

        self.assertEqual(report.skipped_records, 0)
        self.assertGreater(report.chunks, 0)


def _s2orc_record() -> dict:
    repeated_intro = "Graph retrieval links claims to cited evidence for transparent reasoning. "
    repeated_methods = "Confidence pruning removes weak branches while preserving relevant evidence. "
    return {
        "paper_id": "paper-a",
        "title": "Graph Retrieval for Evidence Grounding",
        "abstract": "We study graph-native retrieval for grounded scientific question answering.",
        "year": 2024,
        "venue": "ARPO Workshop",
        "authors": [{"name": "Ada Researcher"}],
        "pdf_parse": {
            "body_text": [
                {
                    "section": "Introduction",
                    "text": repeated_intro * 12,
                    "cite_spans": [{"ref_id": "BIBREF0"}],
                },
                {
                    "section": "Methods",
                    "text": repeated_methods * 12,
                    "cite_spans": [],
                },
            ],
            "bib_entries": {
                "BIBREF0": {
                    "title": "Evidence Graphs",
                    "link": "paper-b",
                }
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
