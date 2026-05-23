# Adaptive Retrieval Path Optimization

ARPO is a research-grade prototype for **adaptive multi-hop information retrieval**. It routes each query through a dynamic retrieval plan instead of using a fixed top-k retrieval recipe for every request.

The core idea is simple:

```text
query -> complexity analysis -> query graph -> adaptive retrieval plan
      -> hybrid retrieval -> evidence graph -> confidence pruning
      -> adaptive reranking -> grounded answer
```

This repository is intentionally built in two layers:

- **Runnable core/API:** deterministic Python retrieval pipeline with a FastAPI service for UI and experiment access.
- **Research adapters:** clean extension points for sentence-transformers, Qdrant, Neo4j, CrossEncoder rerankers, and BEIR-style evaluation.

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

Build a larger local corpus from raw notes, markdown, JSON, JSONL, or PDFs:

```powershell
python -m arpo.ingest_cli .\docs\my-paper-notes.md .\data\my-paper-notes.jsonl --chunk-words 220 --overlap-words 45
```

Then search it:

```powershell
python -m arpo.cli --query "graph retrieval confidence pruning" --corpus data/my-paper-notes.jsonl
```

PDF ingestion requires the optional extra:

```powershell
pip install -e .[ingestion]
```

For JSON output:

```powershell
python -m arpo.cli --query "How do graph retrieval systems reduce hallucination in multi-hop QA?" --corpus examples/corpus.jsonl --json
```

Run the HTTP service:

```powershell
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

To ingest raw source material through the API:

```http
POST /corpora/ingest
multipart/form-data:
  file=<notes.md | papers.json | corpus.jsonl | paper.pdf>
  chunk_words=220
  overlap_words=45
  min_chunk_chars=120
```

## Project Layout

```text
src/arpo/
  analysis/      query complexity routing
  graph/         dynamic query graph construction
  ingestion/     raw text/JSON/PDF to ARPO JSONL chunks
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

The bundled `examples/corpus.jsonl` is intentionally tiny. Use `arpo-ingest` or `/corpora/ingest` to create larger corpora before drawing conclusions from retrieval quality, pruning behavior, or ablation metrics.

## Frontend

ARPO Studio lives in `frontend/`.

Start backend and frontend together:

```powershell
.\scripts\start-dev.ps1
```

To install backend API and frontend dependencies first:

```powershell
.\scripts\start-dev.ps1 -Install
```

Windows CMD shortcut:

```cmd
start-dev.cmd
```

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`. The UI proxies `/api/search`, `/api/evaluate`, and `/api/ablation` to the FastAPI backend at `http://127.0.0.1:8000`.

For production-style frontend output:

```powershell
cd frontend
npm run lint
npm run build
```

The backend can also serve the built frontend when `frontend/dist` exists, or when `ARPO_FRONTEND_DIST` points to a built asset directory.

## Production And CI

The repository includes:

- FastAPI dependency declarations in `pyproject.toml`
- upload validation, path sandboxing, generic server errors, and configurable CORS
- raw corpus ingestion for `.txt`, `.md`, `.json`, `.jsonl`, and optional `.pdf` sources
- API endpoint tests for health, search, path rejection, and ablation
- frontend lint/build checks
- GitHub Actions CI in `.github/workflows/ci.yml`
- a multi-stage Dockerfile that builds ARPO Studio and serves it from the FastAPI app

Run the full local verification suite:

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -v
python -m ruff check src tests
cd frontend
npm run lint
npm run build
```

Build the production container:

```powershell
docker build -t arpo-studio .
docker run --rm -p 8000:8000 arpo-studio
```

Useful production environment variables:

| Variable | Purpose |
| --- | --- |
| `ARPO_WORKSPACE_ROOT` | Root directory for allowed project-relative paths |
| `ARPO_DATA_DIR` | Upload/read directory for user corpora |
| `ARPO_EXAMPLES_DIR` | Read directory for bundled example corpora |
| `ARPO_FRONTEND_DIST` | Built frontend directory to serve from FastAPI |
| `ARPO_CORS_ORIGINS` | Comma-separated allowed browser origins |
| `ARPO_MAX_UPLOAD_BYTES` | Maximum accepted corpus upload size |

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
