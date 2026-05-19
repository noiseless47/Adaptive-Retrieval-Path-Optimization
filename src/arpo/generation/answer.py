from __future__ import annotations

from arpo.models import EvidenceNode, QueryAnalysis


class EvidenceGroundedAnswerGenerator:
    """Lightweight extractive generator that keeps retrieval as the core contribution."""

    def generate(self, query: str, analysis: QueryAnalysis, evidence: tuple[EvidenceNode, ...]) -> str:
        if not evidence:
            return "No sufficiently supported evidence was retrieved for this query."

        lines = [
            f"Query type: {analysis.query_type} "
            f"(complexity={analysis.complexity_score}, hops={analysis.required_hops}).",
            "Grounded answer:",
        ]

        for index, node in enumerate(evidence, start=1):
            claim = node.claims[0] if node.claims else node.document.text[:180].strip()
            lines.append(
                f"{index}. {claim} "
                f"[{node.document.id}; confidence={node.confidence:.2f}]"
            )

        lines.append("Evidence should be treated as insufficient for claims not covered by the cited snippets.")
        return "\n".join(lines)

