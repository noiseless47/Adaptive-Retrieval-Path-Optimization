# ARPO Architecture

## Pipeline

```text
USER QUERY
  -> Query Complexity Analyzer
  -> Dynamic Query Graph Builder
  -> Retrieval Strategy Planner
  -> Hybrid Multi-Stage Retriever
  -> Evidence Dependency Graph Builder
  -> Confidence-Guided Pruner
  -> Adaptive Semantic Reranker
  -> Evidence-Grounded Answer Generator
```

Corpus preparation runs before the live query path:

```text
RAW SOURCES
  -> Source Loader (.txt/.md/.json/.jsonl/.pdf)
  -> Chunker with overlap
  -> Keyword/entity extraction
  -> Chunk relation builder
  -> ARPO JSONL corpus
```

## Core Research Objects

### Query Analysis

The analyzer estimates query type, complexity, ambiguity, required hops, and retrieval mode. In the prototype this is heuristic and deterministic. In the research version, the same interface can be backed by DistilBERT, MiniLM, or a small transformer classifier.

### Dynamic Query Graph

The query graph represents the user query as dependent semantic intents. This lets retrieval operate over reasoning paths rather than isolated keywords.

### Retrieval Strategy

The strategy planner decides sparse, dense, and graph weights, traversal depth, pruning threshold, and reranking policy.

### Corpus Ingestion

The ingestion layer converts larger source collections into ARPO's JSONL document contract. It preserves source metadata, creates overlapping chunks, extracts lightweight keywords/entities, and links adjacent or semantically related chunks through `related_ids`. This gives graph expansion something meaningful to traverse beyond the six-document demo corpus.

### Evidence Graph

Candidate documents become evidence nodes. Edges represent shared concepts, citation links, support relations, and possible contradiction paths.

### Confidence Pruning

Each evidence node receives a confidence score from:

- normalized retrieval score
- query/evidence lexical overlap
- dependency consistency
- contradiction risk

Low-confidence branches are pruned before final reranking.

## Extension Points

| Interface | Prototype | Research/Production Adapter |
| --- | --- | --- |
| Dense retrieval | deterministic hashing | BGE, Contriever, E5, Instructor |
| Graph expansion | metadata links | Neo4j, NetworkX, citation graph |
| Reranking | deterministic adaptive scoring | CrossEncoder, MonoT5, ColBERT |
| Query analysis | heuristics | transformer classifier |
| Answering | extractive synthesis | Mistral, Llama, Phi |
| Evaluation | local metrics | BEIR, HotpotQA, MuSiQue, SciFact |

## Ablation Plan

1. **Static baseline:** sparse+dense fixed top-k.
2. **Graph-only addition:** enable dynamic query graph routing.
3. **Pruning addition:** enable confidence-guided pruning.
4. **Adaptive reranking addition:** enable query-type reranking policies.
5. **Full ARPO:** graph routing + pruning + adaptive reranking.
