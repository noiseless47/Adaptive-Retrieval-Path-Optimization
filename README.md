# Adaptive Retrieval Path Optimization

ARPO is a research-grade prototype for **adaptive multi-hop information retrieval**. It routes each query through a dynamic retrieval plan instead of using a fixed top-k retrieval recipe for every request.

The core idea is simple:

```text
query -> complexity analysis -> query graph -> adaptive retrieval plan
      -> hybrid retrieval -> evidence graph -> confidence pruning
      -> adaptive reranking -> grounded answer
```

This repository is intentionally built in two layers:

- **Runnable core:** pure Python, no required external services, deterministic behavior for tests and ablations.
- **Research adapters:** clean extension points for FastAPI, sentence-transformers, Qdrant, Neo4j, CrossEncoder rerankers, and BEIR-style evaluation.

## Why ARPO Is Different

Most RAG systems retrieve a static number of chunks and then ask a generator to sort out the mess. ARPO treats retrieval as the research problem:

- query complexity controls retrieval depth
- semantic sub-intents become a query dependency graph
- sparse and dense evidence are fused per sub-query
- evidence is represented as a dependency graph
- low-confidence branches are pruned before generation
- reranking policy changes for factual, comparative, ambiguous, and multi-hop queries

## Quick Start

Install the local package:

```powershell
pip install -e .
```

Run the demo query against the included mini corpus:

```powershell
python -m arpo.cli --query "Papers where transformers replaced CNNs in medical imaging while reducing inference cost" --corpus examples/corpus.jsonl
```

For JSON output:

```powershell
python -m arpo.cli --query "How do graph retrieval systems reduce hallucination in multi-hop QA?" --corpus examples/corpus.jsonl --json
```

Install the API extras when you want the HTTP service:

```powershell
pip install -e ".[api]"
uvicorn arpo.api.main:app --reload
```

Then call:

```http
POST /search
{
  "query": "Papers where transformers replaced CNNs in medical imaging while reducing inference cost",
  "top_k": 5
}
```

## Project Layout

```text
src/arpo/
  analysis/      query complexity routing
  graph/         dynamic query graph construction
  planning/      adaptive retrieval strategy selection
  retrieval/     sparse, dense, and hybrid retrieval
  evidence/      evidence dependency graph construction
  pruning/       confidence-guided path pruning
  reranking/     adaptive semantic reranking
  generation/    lightweight evidence-grounded answer synthesis
  evaluation/    IR and hallucination-oriented metrics
  api/           FastAPI adapter
  pipeline.py    end-to-end orchestration
```

## Research Roadmap

The current prototype is designed for ablation experiments:

- fixed retrieval vs adaptive retrieval
- no query graph vs dynamic query graph
- no pruning vs confidence-guided pruning
- static reranking vs query-type adaptive reranking

Recommended benchmark path:

1. Start with the included deterministic mini corpus to validate behavior.
2. Add HotpotQA or MuSiQue for multi-hop QA.
3. Add SciFact for scientific claim retrieval.
4. Add BEIR for broader retrieval evaluation.
5. Replace the built-in hashed dense retriever with sentence-transformers.
6. Replace in-memory graph expansion with Neo4j or another graph backend.

Run the included mini evaluation set:

```powershell
python -m arpo.eval_cli --queries examples/queries.jsonl --corpus examples/corpus.jsonl --top-k 3
```

## Example Python Usage

```python
from arpo.pipeline import ARPOPipeline
from arpo.retrieval.corpus import Corpus

corpus = Corpus.from_jsonl("examples/corpus.jsonl")
pipeline = ARPOPipeline.from_corpus(corpus)

result = pipeline.run(
    "Papers where transformers replaced CNNs in medical imaging while reducing inference cost",
    top_k=5,
)

print(result.answer)
```

## Current Scope

This version focuses on retrieval orchestration. Answer generation is deliberately lightweight and extractive so retrieval quality remains measurable. That keeps the project aligned with its actual research contribution: **adaptive retrieval path optimization**.
