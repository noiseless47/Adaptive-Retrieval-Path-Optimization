from __future__ import annotations

import unittest

from arpo.datasets.openalex import _abstract_from_inverted_index, _work_to_document


class OpenAlexHarvestTests(unittest.TestCase):
    def test_abstract_inverted_index_is_reconstructed_in_order(self) -> None:
        abstract = _abstract_from_inverted_index(
            {
                "Retrieval": [0],
                "graphs": [1],
                "reduce": [2],
                "hallucination": [3],
            }
        )

        self.assertEqual(abstract, "Retrieval graphs reduce hallucination")

    def test_work_to_document_maps_openalex_metadata(self) -> None:
        document = _work_to_document(
            {
                "id": "https://openalex.org/W123",
                "display_name": "Graph Retrieval for Multi-Hop QA",
                "publication_year": 2024,
                "abstract_inverted_index": {"Graph": [0], "retrieval": [1], "helps": [2]},
                "referenced_works": ["https://openalex.org/W456"],
                "related_works": ["https://openalex.org/W789"],
                "concepts": [{"display_name": "Information retrieval"}],
                "authorships": [{"author": {"display_name": "Ada Researcher"}}],
                "primary_location": {"source": {"display_name": "IR Conference"}},
            },
            "graph retrieval",
        )

        assert document is not None
        self.assertEqual(document["id"], "w123")
        self.assertEqual(document["metadata"]["citations"], ["w456"])
        self.assertEqual(document["metadata"]["related_ids"], ["w789"])
        self.assertIn("Information retrieval", document["metadata"]["keywords"])


if __name__ == "__main__":
    unittest.main()
