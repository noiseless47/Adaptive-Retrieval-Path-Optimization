# ARPO Internal Workings

ARPO, or Adaptive Retrieval Path Optimization, is a research-oriented information
retrieval system for complex queries. Its purpose is not to behave like a normal
chatbot. The core idea is that difficult questions should not be answered by
retrieving a fixed number of chunks and hoping the generator can reason over
them. Instead, ARPO treats retrieval itself as the intelligent part of the
system.

At a high level, ARPO turns a user query into a dynamic retrieval plan, retrieves
evidence through sparse, dense, and graph-based paths, removes weak evidence
branches, reranks the remaining evidence, and only then produces an answer.

```text
User Query
  -> Query Complexity Analysis
  -> Dynamic Query Graph
  -> Retrieval Strategy Planning
  -> Hybrid Retrieval
  -> Evidence Dependency Graph
  -> Confidence Pruning
  -> Adaptive Reranking
  -> Evidence-Grounded Answer
```

The important research claim is not simply that ARPO uses retrieval. The claim is
that the retrieval path adapts to the query.

## Core Idea

Traditional retrieval systems usually apply one static strategy:

```text
embed query -> retrieve top-k chunks -> generate answer
```

That works for simple factual questions, but it breaks down when a query has
multiple intents, hidden relationships, comparisons, causal dependencies, or
multi-hop evidence requirements.

ARPO uses a different principle:

```text
understand query shape -> build semantic dependency graph
-> choose retrieval path -> retrieve connected evidence
-> prune weak branches -> rerank according to query type
```

This means two queries can move through different retrieval paths. A simple
factual query can use a precision-heavy retrieval plan, while a comparative
multi-hop query can trigger query decomposition, graph expansion, stronger
reranking, and confidence pruning.

## Main Internal Objects

ARPO is built around a few internal objects that move through the pipeline.

### Document

A document is the smallest searchable corpus unit. It contains:

- `id`
- `title`
- `text`
- `metadata`

The metadata is important because it can store citation links, related document
IDs, source information, year, concepts, domains, and other signals used during
graph expansion.

### Query Analysis

The query analysis object describes the shape of the query. It includes:

- query type
- complexity score
- ambiguity score
- required hops
- retrieval mode
- reranking policy
- additional diagnostic signals

This object is what lets ARPO choose different retrieval behavior for different
types of questions.

### Query Graph

The query graph represents the query as semantic pieces rather than one flat
string. It contains nodes such as:

- root query
- sub-intents
- entities
- constraints

And edges such as:

- decomposes to
- depends on
- mentions
- expands to

For example, a query like:

```text
Papers where transformers replaced CNNs in medical imaging while reducing inference cost
```

can become:

```text
Root Query
  -> transformers replaced CNNs in medical imaging
  -> reducing inference cost
  -> CNNs
```

This matters because retrieval can now happen per intent rather than against the
whole query as one noisy search string.

### Retrieval Strategy

The retrieval strategy is the control object for the retrieval engine. It
contains:

- sparse retrieval weight
- dense retrieval weight
- graph retrieval weight
- top-k
- per-hop candidate count
- maximum graph hops
- pruning threshold
- diversity strength
- reranking mode

This is the heart of the adaptive behavior. ARPO does not always retrieve the
same way. It creates a retrieval strategy based on query complexity.

### Evidence Graph

After retrieval, ARPO converts candidates into evidence nodes and relationships.
Evidence is not treated as disconnected chunks. It becomes a graph of support,
similarity, citation, contradiction risk, and retrieval lineage.

Each evidence node includes:

- document reference
- retrieval score
- confidence score
- extracted claims
- lineage
- diagnostic features

This gives the system something explainable to inspect before answer generation.

## Pipeline Internals

## 1. Query Complexity Analysis

The first stage estimates what kind of query the user asked.

The analyzer looks for signals such as:

- comparison words
- causal language
- temporal constraints
- ambiguity
- number of entities
- multi-hop indicators
- technical terms

It then classifies the query into a retrieval behavior. For example:

| Query Shape | Likely Behavior |
| --- | --- |
| simple factual | precision-heavy retrieval |
| semantic exploratory | dense-heavy retrieval |
| comparative | graph+dense retrieval |
| ambiguous | diversified retrieval |
| multi-hop | staged graph retrieval |

In the current implementation, this analyzer is deterministic and lightweight.
The interface is intentionally designed so that a transformer classifier can
replace it later without changing the rest of the system.

## 2. Dynamic Query Graph Construction

The query graph builder decomposes the query into semantic units. Instead of
searching only the full query, ARPO searches structured sub-intents.

This helps with queries where relevant evidence is split across multiple
documents. For example, one paper may explain transformer replacement of CNNs,
while another provides inference efficiency evidence. A flat retriever may miss
one side of the query. A query graph gives each side a retrieval path.

Internally, the graph builder creates:

- a root node for the full query
- intent nodes for important clauses
- entity nodes for key terms
- dependency edges between related meanings

The output graph is also used by the frontend to visualize how ARPO decomposed
the query.

## 3. Retrieval Strategy Planning

The strategy planner turns query analysis into retrieval controls.

For a factual query, ARPO may use:

```text
high sparse weight
low graph weight
low hop count
precision reranking
```

For a comparative multi-hop query, ARPO may use:

```text
balanced sparse+dense retrieval
higher graph weight
more graph hops
stronger pruning
contradiction-aware reranking
```

This is one of the main differences between ARPO and ordinary RAG systems. The
strategy is not fixed. It is produced dynamically.

## 4. Hybrid Multi-Stage Retrieval

The retriever uses several retrieval signals:

- sparse lexical retrieval
- dense semantic retrieval
- metadata graph expansion

Sparse retrieval is good for exact terms, paper titles, method names, and
technical phrases. Dense retrieval is better for semantic similarity. Graph
expansion is used to follow related documents, citations, or neighboring chunks.

The retriever searches each important query graph intent. Sparse and dense
results are fused using reciprocal-rank-style scoring. Then graph expansion can
pull in related evidence connected to the strongest candidates.

The result is a candidate pool that is broader than a simple top-k search but
still constrained by the query graph and retrieval strategy.

## 5. Evidence Dependency Graph Construction

Retrieved candidates are converted into an evidence graph.

The evidence graph gives ARPO a structured view of the retrieved material:

```text
Evidence Node A
  -> supports relation
  -> semantically related to Evidence Node B
  -> cites Evidence Node C
```

This stage records retrieval lineage so that the system can explain why a
document appeared:

- sparse hit
- dense hit
- fused hit
- graph-expanded neighbor
- related citation

This makes the retrieval process inspectable instead of opaque.

## 6. Confidence-Guided Pruning

Multi-hop retrieval can easily explode. If every retrieved document expands into
more related documents, the system can collect noisy branches. Those noisy
branches are dangerous because they can increase hallucination risk.

ARPO assigns confidence to evidence nodes using signals such as:

- retrieval score
- lexical overlap with query terms
- dependency consistency
- contradiction risk
- graph lineage

Nodes below the pruning threshold are removed before final reranking. This does
two things:

- reduces retrieval noise
- makes answer generation less likely to use weak evidence

The pruning threshold is part of the retrieval strategy, so it can vary by query
type.

## 7. Adaptive Semantic Reranking

After pruning, ARPO reranks the remaining evidence.

The reranking behavior changes depending on the query:

| Query Type | Reranking Priority |
| --- | --- |
| factual | precision and direct relevance |
| comparative | contrastive evidence and contradiction risk |
| ambiguous | diversity |
| multi-hop | dependency coverage |

This means ARPO does not blindly trust the first-stage retrieval score. It
reranks according to what the query needs.

## 8. Evidence-Grounded Answer Generation

Generation is deliberately not the core of ARPO. The system is designed so that
retrieval quality can be measured independently.

The answer generator uses the final ranked evidence and produces a grounded
summary. In a larger deployment, this stage could be replaced by a stronger LLM,
but the research contribution remains the retrieval pipeline, not the language
model.

## Corpus Ingestion Internals

Before ARPO can retrieve, source material must become a searchable corpus.

The ingestion layer converts raw files into ARPO JSONL documents.

Supported source ideas include:

- markdown notes
- plain text
- JSON/JSONL records
- PDFs
- harvested paper metadata

The ingestion process:

```text
source file
  -> text extraction
  -> chunking with overlap
  -> keyword/entity extraction
  -> metadata preservation
  -> related chunk linking
  -> duplicate cleanup
  -> ARPO JSONL corpus
```

Chunk overlap helps preserve context across boundaries. Related IDs and citation
metadata make graph expansion possible. Deduplication reduces repeated evidence
and prevents the retrieval graph from over-counting near-identical chunks.

## Frontend Internal Role

ARPO Studio is not just a skin over the backend. Its purpose is to make the
retrieval process visible.

The frontend visualizes:

- query decomposition
- retrieval mode
- query graph structure
- evidence graph structure
- pruning effects
- ranked evidence
- pipeline trace
- evaluation metrics
- ablation and claim-study results

The frontend is designed like an observability console. It shows the engine
thinking through retrieval rather than presenting a simple chat box.

## Evaluation Internals

ARPO has two evaluation layers.

### Basic Evaluation

The basic evaluator runs the pipeline over a query set and computes:

- Precision@K
- Recall@K
- NDCG@K
- MRR
- latency

Each query record contains:

- query ID
- query text
- relevant document IDs
- optional graded relevance

The evaluator records both aggregate metrics and query-level diagnostics.

### Ablation Evaluation

Ablation compares variants of the system:

- Full ARPO
- No Pruning
- No Query Graph
- Sparse Only
- Dense Only
- Fixed Hybrid

The point is to test whether each ARPO component actually helps. For example,
if Full ARPO does not outperform No Query Graph, then the query graph claim is
not supported on that dataset.

## Research Claim Study Layer

The claim-study layer is the strongest research component. It exists to turn
ARPO from a good demo into a defensible experimental system.

It runs Full ARPO against baselines and produces:

- metric deltas
- relative deltas
- paired significance tests
- bootstrap confidence intervals
- query-type slices
- failure analysis
- claim verdicts
- JSON, CSV, and Markdown artifacts

The verdict system labels claims as:

- supported
- mixed
- not supported

Example claims:

- Full ARPO improves retrieval quality over static baselines.
- Query graph decomposition improves retrieval quality.
- Adaptive routing improves over fixed hybrid retrieval.
- Confidence pruning removes noisy evidence without large recall loss.

This is important because it prevents the project from making vague claims.
ARPO has machinery to say what is supported by evidence and what is not.

## How The Main Research Claims Are Tested

### Claim 1: Adaptive Retrieval Improves Quality

Test:

```text
Full ARPO vs sparse-only, dense-only, fixed hybrid
```

Metrics:

- NDCG@K
- Recall@K
- MRR

If Full ARPO wins across these baselines, the adaptive retrieval claim becomes
stronger.

### Claim 2: Query Graphs Help Multi-Hop Retrieval

Test:

```text
Full ARPO vs No Query Graph
```

If Full ARPO retrieves better evidence than the no-query-graph variant, the
semantic dependency graph is contributing useful signal.

### Claim 3: Pruning Reduces Noise

Test:

```text
Full ARPO vs No Pruning
```

The goal is not always to maximize every raw retrieval metric. The goal is to
remove low-confidence evidence while preserving useful evidence. The claim-study
layer checks pruning behavior against recall changes and average pruned nodes.

### Claim 4: Adaptive Routing Beats Static Hybrid

Test:

```text
Full ARPO vs Fixed Hybrid
```

This isolates whether dynamic strategy planning is useful compared to a normal
static sparse+dense recipe.

## Why The System Is Explainable

ARPO keeps intermediate objects instead of hiding them:

- query analysis explains why a strategy was selected
- query graph explains how the query was decomposed
- retrieval strategy explains weights and depth
- evidence graph explains relationships between documents
- pruning diagnostics explain what was removed
- reranking diagnostics explain final ordering
- evaluation artifacts explain whether the method works

This makes the system suitable for research demos because the user can inspect
how the answer was constructed.

## Current Prototype Limits

The current implementation is intentionally local and deterministic by default.
That makes it easy to test and run, but it also means some components are
replaceable research adapters rather than final production research models.

Current limits:

- query analysis is heuristic, not yet a trained classifier
- default dense retrieval uses local hash embeddings unless configured otherwise
- graph expansion uses metadata links rather than a full graph database
- reranking is lightweight compared to CrossEncoder, MonoT5, or ColBERT
- answer generation is extractive and simple
- strong research claims still require larger benchmark runs

These limits do not weaken the architecture. They define the next research
upgrade path.

## Mental Model

The simplest way to understand ARPO is:

```text
RAG retrieves chunks.
ARPO optimizes retrieval paths.
```

A normal system asks:

```text
What are the top-k chunks for this query?
```

ARPO asks:

```text
What kind of query is this?
What semantic pieces does it contain?
Which retrieval path should each piece take?
Which evidence branches are trustworthy?
Which evidence should survive into the final answer?
Can the claim be proven against baselines?
```

That is the internal logic of the project.
