from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryAnalysis:
    query_type: str
    complexity_score: float
    ambiguity_score: float
    required_hops: int
    retrieval_mode: str
    reranking_policy: str
    signals: dict[str, float | int | bool | str] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryGraphNode:
    id: str
    label: str
    kind: str
    weight: float = 1.0
    terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryGraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0


@dataclass(frozen=True)
class QueryGraph:
    nodes: tuple[QueryGraphNode, ...]
    edges: tuple[QueryGraphEdge, ...]
    root_id: str

    def intent_nodes(self) -> list[QueryGraphNode]:
        return [node for node in self.nodes if node.kind in {"root", "intent"}]

    def terms(self) -> set[str]:
        terms: set[str] = set()
        for node in self.nodes:
            terms.update(node.terms)
        return terms

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "nodes": [node.__dict__ for node in self.nodes],
            "edges": [edge.__dict__ for edge in self.edges],
        }


@dataclass(frozen=True)
class RetrievalStrategy:
    strategy_id: str
    sparse_weight: float
    dense_weight: float
    graph_weight: float
    top_k: int
    per_hop_k: int
    max_hops: int
    pruning_threshold: float
    diversity_lambda: float
    reranking_mode: str


@dataclass(frozen=True)
class RetrievalCandidate:
    document: Document
    score: float
    source: str
    rank: int
    sub_query_id: str
    explanation: str
    features: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceNode:
    id: str
    document: Document
    score: float
    confidence: float
    claims: tuple[str, ...]
    lineage: tuple[str, ...]
    features: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceEdge:
    source: str
    target: str
    relation: str
    weight: float


@dataclass(frozen=True)
class EvidenceGraph:
    nodes: tuple[EvidenceNode, ...]
    edges: tuple[EvidenceEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": node.id,
                    "document_id": node.document.id,
                    "title": node.document.title,
                    "score": node.score,
                    "confidence": node.confidence,
                    "claims": list(node.claims),
                    "lineage": list(node.lineage),
                    "features": node.features,
                }
                for node in self.nodes
            ],
            "edges": [edge.__dict__ for edge in self.edges],
        }


@dataclass(frozen=True)
class PipelineResult:
    query: str
    analysis: QueryAnalysis
    query_graph: QueryGraph
    strategy: RetrievalStrategy
    evidence_graph: EvidenceGraph
    ranked_evidence: tuple[EvidenceNode, ...]
    answer: str
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "analysis": self.analysis.__dict__,
            "query_graph": self.query_graph.to_dict(),
            "strategy": self.strategy.__dict__,
            "evidence_graph": self.evidence_graph.to_dict(),
            "ranked_evidence": [
                {
                    "document_id": node.document.id,
                    "title": node.document.title,
                    "score": node.score,
                    "confidence": node.confidence,
                    "claims": list(node.claims),
                    "lineage": list(node.lineage),
                }
                for node in self.ranked_evidence
            ],
            "answer": self.answer,
            "diagnostics": self.diagnostics,
        }

