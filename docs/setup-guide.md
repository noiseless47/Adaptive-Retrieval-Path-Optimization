# ARPO Studio Setup Guide

This guide explains how to set up ARPO Studio on a fresh machine for local development,
research experiments, and production-style serving.

ARPO has two parts:

- Python backend: FastAPI service plus the adaptive retrieval pipeline.
- Vite frontend: React, TypeScript, Tailwind, React Flow, charts, and command UI.

The default production corpus is:

```text
data/arpo-openalex-corpus.jsonl
```

The default evaluation query set is:

```text
data/arpo-openalex-queries.jsonl
```

Keep those files if you want the app to open with the OpenAlex-backed production corpus.

## 1. Prerequisites

Install these first:

| Tool | Recommended Version | Why |
| --- | --- | --- |
| Git | Latest stable | Clone the repository |
| Python | 3.10 or newer, 3.11 recommended | Backend, API, retrieval pipeline |
| Node.js | 22 LTS recommended | Frontend dev server and production build |
| npm | Bundled with Node.js | Frontend dependency installation |
| Docker Desktop | Optional | Containerized production-style run |

Verify them:

```powershell
git --version
python --version
node --version
npm --version
docker --version
```

On macOS or Linux, use `python3 --version` if `python` is not available.

## 2. Clone The Repository

```powershell
git clone <your-repository-url>
cd Adaptive-Retrieval-Path-Optimization
```

Expected top-level structure:

```text
src/          Python ARPO backend and retrieval pipeline
frontend/     React/Vite ARPO Studio frontend
data/         OpenAlex corpus and evaluation query set
examples/     Tiny demo corpus and demo query set
scripts/      Development startup scripts
tests/        Backend tests
docs/         Architecture and setup documentation
```

## 3. Python Backend Setup

Create a virtual environment from the repository root.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[api,dev,ingestion]"
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[api,dev,ingestion]"
```

Optional ML dependencies:

```powershell
python -m pip install -e ".[ml]"
```

Use the optional `ml` extra only if you want SentenceTransformers, spaCy, NetworkX,
and heavier retrieval tooling. The project works without it using the default local
hash embedding backend.

## 4. Frontend Setup

From the repository root:

```powershell
cd frontend
npm install
cd ..
```

This installs the ARPO Studio UI dependencies, including React, Vite, Tailwind,
TanStack Query, React Flow, Recharts, Framer Motion, cmdk, Radix controls, and Zod.

## 5. Start Backend And Frontend Together

The easiest path on Windows is the provided script:

```powershell
.\scripts\start-dev.ps1
```

If this is the first setup on the machine, let the script install dependencies too:

```powershell
.\scripts\start-dev.ps1 -Install
```

CMD shortcut:

```cmd
start-dev.cmd
```

Default URLs:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
Health:   http://127.0.0.1:8000/health
```

The frontend proxies `/api/*` requests to the backend during development.

## 6. Start Manually

Use this if you are on macOS/Linux or want two visible terminals.

Terminal 1, backend:

```powershell
python -m uvicorn arpo.api.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, frontend:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## 7. Verify The Setup

Backend health:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

Corpus listing:

```powershell
curl.exe http://127.0.0.1:8000/api/corpora
```

You should see `arpo-openalex-corpus.jsonl` listed as an uploaded/data corpus.
Query-set files such as `queries.jsonl` should not appear as corpora.

Autocomplete check:

```powershell
curl.exe "http://127.0.0.1:8000/api/suggest?q=rag&corpus_path=data/arpo-openalex-corpus.jsonl"
```

You should receive corpus-derived retrieval suggestions.

Search check:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/search `
  -H "Content-Type: application/json" `
  -d '{"query":"Trace evidence paths linking RAG hallucination detection to citation-grounded evaluation","top_k":5,"corpus_path":"data/arpo-openalex-corpus.jsonl"}'
```

## 8. Run Quality Checks

From the repository root:

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
cd ..
```

Run these before presenting the project or pushing changes.

## 9. Production-Style Local Build

Build the frontend:

```powershell
cd frontend
npm run build
cd ..
```

Start the backend:

```powershell
python -m uvicorn arpo.api.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

When `frontend/dist` exists, FastAPI serves the built ARPO Studio frontend.

## 10. Docker Setup

Build the image:

```powershell
docker build -t arpo-studio .
```

Run it:

```powershell
docker run --rm -p 8000:8000 arpo-studio
```

Open:

```text
http://127.0.0.1:8000
```

The Docker image includes:

- Python backend
- built frontend
- `examples/`
- `data/arpo-openalex-corpus.jsonl`
- `data/arpo-openalex-queries.jsonl`

Large generated folders such as `data/raw`, `data/processed`, and
`data/vector-indexes` are excluded from the Docker context.

## 11. Corpus Setup

The project needs JSONL corpus files with this shape:

```json
{"id":"doc-001","title":"Document title","text":"Document body","metadata":{"source":"..."}}
```

The included OpenAlex corpus is already in the correct format:

```text
data/arpo-openalex-corpus.jsonl
```

The tiny demo corpus is:

```text
examples/corpus.jsonl
```

Use the OpenAlex corpus for the frontend. Use the examples only for quick unit
checks or small deterministic tests.

## 12. Create Or Replace A Corpus

Ingest a Markdown, text, JSON, JSONL, or PDF source:

```powershell
python -m arpo.ingest_cli .\docs\my-notes.md .\data\my-notes.jsonl --chunk-words 220 --overlap-words 45
```

Harvest a new OpenAlex corpus:

```powershell
python -m arpo.harvest_cli `
  --output data/arpo-openalex-corpus.jsonl `
  --raw-output data/raw/openalex-works.jsonl `
  --per-topic 50
```

Optional polite OpenAlex email:

```powershell
python -m arpo.harvest_cli `
  --output data/arpo-openalex-corpus.jsonl `
  --raw-output data/raw/openalex-works.jsonl `
  --per-topic 50 `
  --mailto your-email@example.com
```

After changing the corpus, restart the backend so fresh corpus metadata and
autocomplete suggestions are loaded consistently.

## 13. Dense Vector Indexes

ARPO can run without prebuilt indexes. For faster repeated retrieval, build one:

```powershell
python -m arpo.index_cli --corpus data/arpo-openalex-corpus.jsonl --index-dir data/vector-indexes
```

Default embedding backend:

```text
hash
```

SentenceTransformers backend:

```powershell
python -m pip install -e ".[ml]"
$env:ARPO_EMBEDDING_BACKEND="sentence-transformers"
$env:ARPO_EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
python -m arpo.index_cli --corpus data/arpo-openalex-corpus.jsonl --backend sentence-transformers
```

The first SentenceTransformers run downloads model weights, so it requires internet
access and more disk space.

## 14. Evaluation And Ablation

Run evaluation:

```powershell
python -m arpo.eval_cli `
  --queries data/arpo-openalex-queries.jsonl `
  --corpus data/arpo-openalex-corpus.jsonl `
  --top-k 5
```

The frontend Evaluation and Ablation pages default to the same production corpus
and query set.

## 15. Useful Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `ARPO_WORKSPACE_ROOT` | current working directory | Root for project-relative paths |
| `ARPO_DATA_DIR` | `data` | Uploaded/readable corpus directory |
| `ARPO_EXAMPLES_DIR` | `examples` | Bundled example corpus directory |
| `ARPO_FRONTEND_DIST` | `frontend/dist` | Built frontend directory served by FastAPI |
| `ARPO_CORS_ORIGINS` | localhost dev origins | Comma-separated allowed browser origins |
| `ARPO_MAX_UPLOAD_BYTES` | 10485760 | Maximum upload size |
| `ARPO_EMBEDDING_BACKEND` | `hash` | `hash` or `sentence-transformers` |
| `ARPO_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | SentenceTransformers model id |
| `ARPO_VECTOR_INDEX_DIR` | `data/vector-indexes` | Persistent vector index location |
| `ARPO_VECTOR_CACHE` | enabled | Set to `0` to disable vector index caching |

Example:

```powershell
$env:ARPO_CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
python -m uvicorn arpo.api.main:app --reload
```

## 16. Troubleshooting

### PowerShell blocks activation

Run PowerShell as your normal user and allow local scripts for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### `Vite is not installed`

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

### Frontend cannot reach backend

Confirm backend is running:

```powershell
curl.exe http://127.0.0.1:8000/health
```

If you changed the backend port, also update the Vite proxy in:

```text
frontend/vite.config.ts
```

### Corpus dropdown shows only demo data

Check that the OpenAlex corpus exists:

```powershell
Test-Path .\data\arpo-openalex-corpus.jsonl
```

If it is missing, restore it from the repository or run the OpenAlex harvest command.

### Docker page loads but search fails

Rebuild the image after corpus or frontend changes:

```powershell
docker build -t arpo-studio .
docker run --rm -p 8000:8000 arpo-studio
```

### SentenceTransformers is slow or fails

Use the default hash backend first. It is deterministic, local, and good for setup
verification. Move to SentenceTransformers only after the base app works.

## 17. Recommended Fresh-System Checklist

1. Install Git, Python, Node.js, and npm.
2. Clone the repository.
3. Create and activate `.venv`.
4. Run `python -m pip install -e ".[api,dev,ingestion]"`.
5. Run `cd frontend && npm install && cd ..`.
6. Confirm `data/arpo-openalex-corpus.jsonl` exists.
7. Start with `.\scripts\start-dev.ps1` on Windows, or run backend/frontend manually.
8. Open `http://127.0.0.1:5173`.
9. Type `rag hallu` in the landing input and confirm corpus autocomplete appears.
10. Run the quality checks before presenting or submitting.
