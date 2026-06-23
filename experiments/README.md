# ARPO Experiment Configs

This directory stores reproducible research runs for defending ARPO's retrieval claims.

Run the default local claim study:

```bash
python -m arpo.research_cli --config experiments/claim-study.openalex.json
```

The runner compares Full ARPO against no-pruning, no-query-graph, sparse-only,
dense-only, and fixed-hybrid baselines. It writes JSON, CSV, and Markdown artifacts
under `data/experiments/`.

Supported query-set formats:

- `native`: ARPO JSONL with `id`, `query`, `relevant_ids`, and optional `graded_relevance`.
- `hotpotqa`: HotpotQA JSON/JSONL with `question` and `supporting_facts`.
- `scifact`: SciFact claim JSONL with `claim`, `cited_doc_ids`, or `evidence`.
- `beir`: BEIR-style directory containing `queries.jsonl` and qrels files.
