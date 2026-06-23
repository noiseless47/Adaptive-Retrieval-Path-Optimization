# Production Readiness Notes

This document maps the production-readiness work in ARPO Studio to the original
15 hardening areas. The project is still a local research system, but it now has
clean production foundations instead of demo-only assumptions.

## Implemented Foundations

| Area | Current Implementation |
| --- | --- |
| Larger corpus workflow | OpenAlex corpus is the default, with `arpo-corpus` and `/api/corpora/stats` for quality checks. |
| Real embeddings path | Hash embeddings remain local-safe; SentenceTransformers is configurable with `ARPO_EMBEDDING_BACKEND` and index jobs. |
| Persistent vector/graph path | Local persistent vector indexes exist; Docker Compose includes optional Qdrant and Neo4j infrastructure profiles. |
| Async jobs | `/api/jobs/evaluate`, `/api/jobs/ablation`, `/api/jobs/claim-study`, and `/api/jobs/index` execute long-running work outside the request path. |
| Auth layer | Optional API-key auth through `ARPO_API_KEYS`, `x-api-key`, or bearer token headers. |
| Observability | Request IDs, latency headers, in-memory API metrics, `/api/metrics`, `/api/healthz`, and structured request logs. |
| Frontend error states | Header connection indicator now reflects backend health instead of always saying connected. |
| Frontend tests path | Browser QA remains manual; frontend lint/build are wired and documented. |
| Evaluation benchmarks | OpenAlex query set is default; native JSONL, HotpotQA, SciFact, and BEIR-style benchmark loaders are available through the claim-study layer. |
| Research claim validation | `arpo-research` and `/api/research/claim-study` run Full ARPO against baselines, compute paired deltas, confidence intervals, p-values, failure slices, and write JSON/CSV/Markdown artifacts. |
| Evidence audit metrics | Pipeline diagnostics now include `evidence_audit` with confidence and contradiction-risk signals. |
| Security hardening | Path sandboxing, upload validation, rate limiting, optional auth, request IDs, and upload-size controls. |
| Docker verification path | Dockerfile includes `data/`; Compose has health checks and optional infra profiles. |
| Deployment config | `.env.example`, `docker-compose.yml`, Dockerfile, and setup docs are present. |
| Ingestion hardening | Ingestion now removes duplicate chunks and cleans relation/citation links after dedupe. |
| Saved runs | SQLite-backed run store persists searches, evaluations, ablations, and job results; `/api/runs` exposes history. |

## What Still Requires Real Infrastructure

Some production concerns cannot be honestly completed inside a local code-only pass:

- Managed vector DB deployment and collection lifecycle.
- Managed Neo4j/Postgres evidence graph storage.
- Real user accounts, organizations, permissions, and billing-safe workspace isolation.
- Full frontend Playwright/Vitest suite.
- Large benchmark dataset downloads and a hosted benchmark registry.
- Hosted observability stack such as OpenTelemetry, Prometheus, Grafana, or Sentry.

The current implementation keeps those as explicit extension points while making
the local project much closer to something deployable.

## Useful Commands

Corpus quality report:

```powershell
python -m arpo.corpus_cli data/arpo-openalex-corpus.jsonl
```

Async evaluation job:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/jobs/evaluate `
  -H "Content-Type: application/json" `
  -d '{"corpus_path":"data/arpo-openalex-corpus.jsonl","queries_path":"data/arpo-openalex-queries.jsonl","top_k":5}'
```

Research claim study:

```powershell
python -m arpo.research_cli --config experiments/claim-study.openalex.json
```

API claim study:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/research/claim-study `
  -H "Content-Type: application/json" `
  -d '{"corpus_path":"data/arpo-openalex-corpus.jsonl","queries_path":"data/arpo-openalex-queries.jsonl","benchmark":"native","top_k":5}'
```

List jobs:

```powershell
curl.exe http://127.0.0.1:8000/api/jobs
```

List saved runs:

```powershell
curl.exe http://127.0.0.1:8000/api/runs
```

Production health:

```powershell
curl.exe http://127.0.0.1:8000/api/healthz
```

Metrics:

```powershell
curl.exe http://127.0.0.1:8000/api/metrics
```
