from __future__ import annotations

from itertools import combinations

from arpo.models import EvidenceEdge, EvidenceGraph, EvidenceNode, QueryGraph, RetrievalCandidate
from arpo.text import best_snippets, clamp, lexical_overlap, tokenize


class EvidenceGraphBuilder:
    def build(self, candidates: list[RetrievalCandidate], query: str, query_graph: QueryGraph) -> EvidenceGraph:
        query_terms = query_graph.terms() or set(tokenize(query))
        nodes = [self._node(candidate, query, query_terms) for candidate in candidates]
        edges = self._edges(nodes)
        return EvidenceGraph(nodes=tuple(nodes), edges=tuple(edges))

    def _node(self, candidate: RetrievalCandidate, query: str, query_terms: set[str]) -> EvidenceNode:
        document_text = f"{candidate.document.title} {candidate.document.text}"
        doc_terms = tokenize(document_text)
        overlap = lexical_overlap(query_terms, doc_terms)
        contradiction_risk = self._contradiction_risk(candidate.document.text)
        dependency_consistency = self._dependency_consistency(candidate)
        confidence = clamp(
            (0.45 * candidate.score)
            + (0.25 * overlap)
            + (0.20 * dependency_consistency)
            + (0.10 * (1.0 - contradiction_risk))
        )
        snippets = best_snippets(candidate.document.text, query, limit=2)
        return EvidenceNode(
            id=candidate.document.id,
            document=candidate.document,
            score=round(candidate.score, 4),
            confidence=round(confidence, 4),
            claims=tuple(snippets or [candidate.document.text[:240].strip()]),
            lineage=(candidate.source, candidate.sub_query_id, candidate.explanation),
            features={
                **candidate.features,
                "lexical_overlap": round(overlap, 4),
                "dependency_consistency": round(dependency_consistency, 4),
                "contradiction_risk": round(contradiction_risk, 4),
            },
        )

    @staticmethod
    def _edges(nodes: list[EvidenceNode]) -> list[EvidenceEdge]:
        edges: list[EvidenceEdge] = []
        for left, right in combinations(nodes, 2):
            relation, weight = EvidenceGraphBuilder._relation(left, right)
            if weight > 0.12:
                edges.append(EvidenceEdge(source=left.id, target=right.id, relation=relation, weight=round(weight, 4)))
                if relation == "cites":
                    edges.append(EvidenceEdge(source=right.id, target=left.id, relation="cited_by", weight=round(weight, 4)))
        return edges

    @staticmethod
    def _relation(left: EvidenceNode, right: EvidenceNode) -> tuple[str, float]:
        left_citations = set(map(str, left.document.metadata.get("citations", [])))
        right_citations = set(map(str, right.document.metadata.get("citations", [])))
        if right.document.id in left_citations or left.document.id in right_citations:
            return "cites", 0.88

        left_keywords = set(map(str.lower, left.document.metadata.get("keywords", [])))
        right_keywords = set(map(str.lower, right.document.metadata.get("keywords", [])))
        keyword_overlap = lexical_overlap(left_keywords, right_keywords)

        text_overlap = lexical_overlap(
            tokenize(f"{left.document.title} {left.document.text}"),
            tokenize(f"{right.document.title} {right.document.text}"),
        )
        weight = max(keyword_overlap, text_overlap)
        relation = "supports" if weight >= 0.22 else "semantically_related"
        return relation, weight

    @staticmethod
    def _contradiction_risk(text: str) -> float:
        lowered = text.lower()
        markers = ["however", "but", "contradict", "conflict", "failed to", "does not", "no evidence"]
        hits = sum(1 for marker in markers if marker in lowered)
        return clamp(hits / 3)

    @staticmethod
    def _dependency_consistency(candidate: RetrievalCandidate) -> float:
        if candidate.source == "metadata_graph":
            return 0.72
        if "+" in candidate.source:
            return 0.86
        return 0.62

