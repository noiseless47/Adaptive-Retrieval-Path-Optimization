from __future__ import annotations

import re

from arpo.models import QueryAnalysis, QueryGraph, QueryGraphEdge, QueryGraphNode
from arpo.text import tokenize


class DynamicQueryGraphBuilder:
    """Build a semantic dependency graph from a query."""

    SPLIT_RE = re.compile(
        r"\b(?:and|while|where|with|that|which|because|when|versus|vs|compared to)\b",
        re.IGNORECASE,
    )

    def build(self, query: str, analysis: QueryAnalysis) -> QueryGraph:
        root = QueryGraphNode(
            id="q0",
            label=query.strip(),
            kind="root",
            weight=1.0,
            terms=tuple(tokenize(query)),
        )
        nodes: list[QueryGraphNode] = [root]
        edges: list[QueryGraphEdge] = []

        sub_intents = self._sub_intents(query)
        if not sub_intents:
            sub_intents = [query]

        for index, intent in enumerate(sub_intents, start=1):
            intent_terms = tuple(tokenize(intent))
            weight = self._intent_weight(intent, analysis)
            intent_node = QueryGraphNode(
                id=f"i{index}",
                label=intent,
                kind="intent",
                weight=weight,
                terms=intent_terms,
            )
            nodes.append(intent_node)
            edges.append(
                QueryGraphEdge(source=root.id, target=intent_node.id, relation="decomposes_to", weight=weight)
            )

            for entity_index, entity in enumerate(self._entities(intent), start=1):
                entity_id = f"e{index}_{entity_index}"
                entity_node = QueryGraphNode(
                    id=entity_id,
                    label=entity,
                    kind="entity",
                    weight=min(1.0, 0.55 + weight / 2),
                    terms=tuple(tokenize(entity)),
                )
                nodes.append(entity_node)
                edges.append(
                    QueryGraphEdge(
                        source=intent_node.id,
                        target=entity_id,
                        relation="mentions",
                        weight=entity_node.weight,
                    )
                )

        intent_ids = [node.id for node in nodes if node.kind == "intent"]
        for source, target in zip(intent_ids, intent_ids[1:]):
            edges.append(QueryGraphEdge(source=source, target=target, relation="depends_on", weight=0.72))

        return QueryGraph(nodes=tuple(nodes), edges=tuple(edges), root_id=root.id)

    def _sub_intents(self, query: str) -> list[str]:
        pieces = [piece.strip(" ,.;:") for piece in self.SPLIT_RE.split(query)]
        clean = [piece for piece in pieces if len(tokenize(piece)) >= 2]
        if len(clean) <= 1:
            return clean

        merged: list[str] = []
        for piece in clean:
            if merged and len(tokenize(piece)) <= 2:
                merged[-1] = f"{merged[-1]} {piece}"
            else:
                merged.append(piece)
        return merged[:6]

    @staticmethod
    def _intent_weight(intent: str, analysis: QueryAnalysis) -> float:
        terms = tokenize(intent)
        if not terms:
            return 0.4
        length_bonus = min(0.25, len(terms) / 30)
        complexity_bonus = analysis.complexity_score * 0.25
        return round(min(1.0, 0.45 + length_bonus + complexity_bonus), 3)

    @staticmethod
    def _entities(text: str) -> list[str]:
        candidates = re.findall(r"\b(?:[A-Z][A-Za-z0-9+-]*|[A-Z]{2,})\b(?:\s+\b[A-Z][A-Za-z0-9+-]*\b)*", text)
        question_words = {"how", "what", "when", "where", "why", "which", "who"}
        normalized = []
        seen = set()
        for candidate in candidates:
            compact = candidate.strip()
            key = compact.lower()
            if key not in seen and key not in question_words and len(compact) > 1:
                seen.add(key)
                normalized.append(compact)
        return normalized[:5]
