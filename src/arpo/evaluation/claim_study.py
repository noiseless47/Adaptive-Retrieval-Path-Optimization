from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from arpo.evaluation.benchmarks import BenchmarkLoadReport
from arpo.evaluation.runner import QueryRecord, evaluate_pipeline
from arpo.evaluation.statistics import paired_metric_test
from arpo.evaluation.variants import DEFAULT_VARIANTS, VARIANT_LABELS, validate_variants, variant_controls
from arpo.retrieval import Corpus


QUALITY_METRICS = ("precision_at_k", "recall_at_k", "ndcg_at_k", "mrr")
COMPARISON_METRICS = (*QUALITY_METRICS, "latency_ms")


def run_claim_study(
    corpus: Corpus,
    records: list[QueryRecord],
    *,
    top_k: int = 5,
    variants: list[str] | tuple[str, ...] = DEFAULT_VARIANTS,
    primary_variant: str = "full",
    benchmark: BenchmarkLoadReport | None = None,
    artifact_dir: str | Path | None = None,
    corpus_path: str | None = None,
    queries_path: str | None = None,
) -> dict[str, Any]:
    variants = tuple(variants)
    validate_variants(variants)
    if primary_variant not in variants:
        raise ValueError("Primary variant must be included in the variants list.")

    study_id = f"claim-study-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    reports: dict[str, dict[str, Any]] = {}

    for variant in variants:
        strategy_factory, disable_query_graph = variant_controls(variant)
        report = evaluate_pipeline(
            corpus,
            records,
            top_k=top_k,
            strategy_factory=strategy_factory,
            disable_query_graph=disable_query_graph,
        )
        reports[variant] = report

    primary = reports[primary_variant]
    variant_summaries = [
        _variant_summary(variant, reports[variant])
        for variant in variants
    ]
    comparisons = [
        _compare_reports(primary_variant, primary, variant, reports[variant])
        for variant in variants
        if variant != primary_variant
    ]
    slices = _query_type_slices(primary_variant, reports, variants)
    failure_analysis = _failure_analysis(primary_variant, primary, reports)
    claim_verdicts = _claim_verdicts(primary_variant, reports, comparisons)

    payload: dict[str, Any] = {
        "study_id": study_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_path": corpus_path,
        "queries_path": queries_path,
        "top_k": top_k,
        "primary_variant": {
            "key": primary_variant,
            "label": VARIANT_LABELS[primary_variant],
        },
        "benchmark": benchmark.to_dict() if benchmark else {
            "name": "native",
            "source_path": queries_path,
            "query_count": len(records),
            "relevant_judgement_count": sum(len(record.relevant_ids) for record in records),
            "warnings": [],
        },
        "metrics": list(COMPARISON_METRICS),
        "variants": variant_summaries,
        "comparisons": comparisons,
        "slices": slices,
        "failure_analysis": failure_analysis,
        "claim_verdicts": claim_verdicts,
        "reports": {
            variant: {
                "summary": _report_summary(reports[variant]),
                "queries": reports[variant]["queries"],
            }
            for variant in variants
        },
    }

    if artifact_dir is not None:
        payload["artifacts"] = write_claim_study_artifacts(payload, Path(artifact_dir))

    return payload


def write_claim_study_artifacts(report: dict[str, Any], artifact_dir: Path) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    study_id = str(report["study_id"])
    json_path = artifact_dir / f"{study_id}.json"
    variants_csv_path = artifact_dir / f"{study_id}-variants.csv"
    comparisons_csv_path = artifact_dir / f"{study_id}-comparisons.csv"
    markdown_path = artifact_dir / f"{study_id}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with variants_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant_key",
                "variant",
                "precision_at_k",
                "recall_at_k",
                "ndcg_at_k",
                "mrr",
                "latency_ms",
                "avg_pruned_nodes",
                "avg_unsupported_claim_risk",
            ],
        )
        writer.writeheader()
        for row in report["variants"]:
            writer.writerow({
                "variant_key": row["variant_key"],
                "variant": row["variant"],
                **{metric: row["summary"].get(metric, 0.0) for metric in COMPARISON_METRICS},
                "avg_pruned_nodes": row["diagnostics"].get("avg_pruned_nodes", 0.0),
                "avg_unsupported_claim_risk": row["diagnostics"].get(
                    "avg_unsupported_claim_risk", 0.0
                ),
            })

    with comparisons_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "baseline_key",
                "baseline",
                "delta_ndcg_at_k",
                "delta_recall_at_k",
                "delta_mrr",
                "p_value_ndcg_at_k",
                "ci95_low_ndcg_at_k",
                "ci95_high_ndcg_at_k",
            ],
        )
        writer.writeheader()
        for row in report["comparisons"]:
            ndcg_stats = row["paired_significance"]["ndcg_at_k"]
            writer.writerow({
                "baseline_key": row["baseline_key"],
                "baseline": row["baseline"],
                "delta_ndcg_at_k": row["delta"].get("ndcg_at_k", 0.0),
                "delta_recall_at_k": row["delta"].get("recall_at_k", 0.0),
                "delta_mrr": row["delta"].get("mrr", 0.0),
                "p_value_ndcg_at_k": ndcg_stats["p_value"],
                "ci95_low_ndcg_at_k": ndcg_stats["ci95_low"],
                "ci95_high_ndcg_at_k": ndcg_stats["ci95_high"],
            })

    markdown_path.write_text(render_claim_study_markdown(report), encoding="utf-8")

    return {
        "json": json_path.as_posix(),
        "variants_csv": variants_csv_path.as_posix(),
        "comparisons_csv": comparisons_csv_path.as_posix(),
        "markdown": markdown_path.as_posix(),
    }


def render_claim_study_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# ARPO Research Claim Study: {report['study_id']}",
        "",
        f"- Benchmark: {report['benchmark']['name']}",
        f"- Queries: {report['benchmark']['query_count']}",
        f"- Top K: {report['top_k']}",
        f"- Primary variant: {report['primary_variant']['label']}",
        "",
        "## Variant Summary",
        "",
        "| Variant | Recall@K | NDCG@K | MRR | Latency ms |",
        "|---|---:|---:|---:|---:|",
    ]
    for variant in report["variants"]:
        summary = variant["summary"]
        lines.append(
            "| {variant} | {recall:.3f} | {ndcg:.3f} | {mrr:.3f} | {latency:.3f} |".format(
                variant=variant["variant"],
                recall=summary.get("recall_at_k", 0.0),
                ndcg=summary.get("ndcg_at_k", 0.0),
                mrr=summary.get("mrr", 0.0),
                latency=summary.get("latency_ms", 0.0),
            )
        )

    lines.extend(["", "## Claims", ""])
    for verdict in report["claim_verdicts"]:
        lines.append(f"- **{verdict['status'].title()}**: {verdict['claim']} {verdict['evidence']}")

    lines.extend(["", "## Comparisons", ""])
    lines.append("| Baseline | Delta NDCG@K | Delta Recall@K | p-value NDCG | 95% CI NDCG |")
    lines.append("|---|---:|---:|---:|---|")
    for comparison in report["comparisons"]:
        stats = comparison["paired_significance"]["ndcg_at_k"]
        lines.append(
            "| {baseline} | {d_ndcg:.3f} | {d_recall:.3f} | {p:.4f} | [{low:.3f}, {high:.3f}] |".format(
                baseline=comparison["baseline"],
                d_ndcg=comparison["delta"].get("ndcg_at_k", 0.0),
                d_recall=comparison["delta"].get("recall_at_k", 0.0),
                p=stats["p_value"],
                low=stats["ci95_low"],
                high=stats["ci95_high"],
            )
        )

    if report["failure_analysis"]:
        lines.extend(["", "## Failure Analysis", ""])
        for item in report["failure_analysis"][:12]:
            lines.append(
                f"- `{item['query_id']}` {item['failure_type']}: {item['query']} "
                f"(NDCG={item['ndcg_at_k']:.3f}, Recall={item['recall_at_k']:.3f})"
            )

    return "\n".join(lines) + "\n"


def _variant_summary(variant: str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant_key": variant,
        "variant": VARIANT_LABELS[variant],
        "summary": _report_summary(report),
        "diagnostics": _diagnostic_summary(report),
    }


def _report_summary(report: dict[str, Any]) -> dict[str, float | int]:
    return {
        "top_k": int(report["top_k"]),
        "query_count": int(report["query_count"]),
        "precision_at_k": _round(report["precision_at_k"]),
        "recall_at_k": _round(report["recall_at_k"]),
        "ndcg_at_k": _round(report["ndcg_at_k"]),
        "mrr": _round(report["mrr"]),
        "latency_ms": _round(report["latency_ms"]),
    }


def _diagnostic_summary(report: dict[str, Any]) -> dict[str, float]:
    queries = report["queries"]
    if not queries:
        return {
            "avg_candidates": 0.0,
            "avg_pruned_nodes": 0.0,
            "avg_retained_nodes": 0.0,
            "avg_unsupported_claim_risk": 0.0,
        }

    return {
        "avg_candidates": _mean(
            float(item["diagnostics"].get("candidate_count", 0.0)) for item in queries
        ),
        "avg_pruned_nodes": _mean(
            float(item["diagnostics"].get("evidence_nodes_before_pruning", 0.0))
            - float(item["diagnostics"].get("evidence_nodes_after_pruning", 0.0))
            for item in queries
        ),
        "avg_retained_nodes": _mean(
            float(item["diagnostics"].get("evidence_nodes_after_pruning", 0.0)) for item in queries
        ),
        "avg_unsupported_claim_risk": _mean(
            float(item["diagnostics"].get("evidence_audit", {}).get("unsupported_claim_risk", 0.0))
            for item in queries
        ),
    }


def _compare_reports(
    primary_variant: str,
    primary: dict[str, Any],
    baseline_variant: str,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    delta = {
        metric: _round(float(primary.get(metric, 0.0)) - float(baseline.get(metric, 0.0)))
        for metric in COMPARISON_METRICS
    }
    relative_delta = {
        metric: _relative_delta(float(primary.get(metric, 0.0)), float(baseline.get(metric, 0.0)))
        for metric in COMPARISON_METRICS
    }

    primary_by_id = {item["id"]: item for item in primary["queries"]}
    baseline_by_id = {item["id"]: item for item in baseline["queries"]}
    shared_ids = [query_id for query_id in primary_by_id if query_id in baseline_by_id]
    significance = {
        metric: paired_metric_test(
            [float(primary_by_id[query_id].get(metric, 0.0)) for query_id in shared_ids],
            [float(baseline_by_id[query_id].get(metric, 0.0)) for query_id in shared_ids],
        )
        for metric in QUALITY_METRICS
    }

    return {
        "primary_key": primary_variant,
        "primary": VARIANT_LABELS[primary_variant],
        "baseline_key": baseline_variant,
        "baseline": VARIANT_LABELS[baseline_variant],
        "delta": delta,
        "relative_delta": relative_delta,
        "paired_significance": significance,
    }


def _query_type_slices(
    primary_variant: str,
    reports: dict[str, dict[str, Any]],
    variants: tuple[str, ...],
) -> list[dict[str, Any]]:
    query_types = sorted({item["query_type"] for report in reports.values() for item in report["queries"]})
    slices: list[dict[str, Any]] = []

    for query_type in query_types:
        rows: dict[str, dict[str, float | int | str]] = {}
        for variant in variants:
            subset = [
                item for item in reports[variant]["queries"]
                if item["query_type"] == query_type
            ]
            rows[variant] = {
                "variant": VARIANT_LABELS[variant],
                "query_count": len(subset),
                "recall_at_k": _mean(float(item["recall_at_k"]) for item in subset),
                "ndcg_at_k": _mean(float(item["ndcg_at_k"]) for item in subset),
                "mrr": _mean(float(item["mrr"]) for item in subset),
            }

        best_baseline = max(
            (variant for variant in variants if variant != primary_variant),
            key=lambda variant: float(rows[variant]["ndcg_at_k"]),
            default=primary_variant,
        )
        primary_ndcg = float(rows[primary_variant]["ndcg_at_k"])
        baseline_ndcg = float(rows[best_baseline]["ndcg_at_k"])
        slices.append({
            "query_type": query_type,
            "query_count": rows[primary_variant]["query_count"],
            "primary": rows[primary_variant],
            "best_baseline": rows[best_baseline],
            "delta_vs_best_baseline": {
                "ndcg_at_k": _round(primary_ndcg - baseline_ndcg),
            },
        })

    return slices


def _failure_analysis(
    primary_variant: str,
    primary: dict[str, Any],
    reports: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    baselines_by_query: dict[str, list[dict[str, Any]]] = {}
    for variant, report in reports.items():
        if variant == primary_variant:
            continue
        for item in report["queries"]:
            baselines_by_query.setdefault(item["id"], []).append(item)

    failures: list[dict[str, Any]] = []
    for item in primary["queries"]:
        diagnostics = item["diagnostics"]
        audit = diagnostics.get("evidence_audit", {})
        best_baseline_ndcg = max(
            (float(other["ndcg_at_k"]) for other in baselines_by_query.get(item["id"], [])),
            default=0.0,
        )
        failure_type = ""
        if float(item["recall_at_k"]) < 0.5 and item.get("relevant_total", 0) > 0:
            failure_type = "missed_relevant_evidence"
        elif float(audit.get("unsupported_claim_risk", 0.0)) >= 0.35:
            failure_type = "high_unsupported_claim_risk"
        elif best_baseline_ndcg - float(item["ndcg_at_k"]) > 0.15:
            failure_type = "baseline_outperformed_arpo"

        if failure_type:
            failures.append(
                {
                    "query_id": item["id"],
                    "query": item["query"],
                    "query_type": item["query_type"],
                    "failure_type": failure_type,
                    "precision_at_k": _round(item["precision_at_k"]),
                    "recall_at_k": _round(item["recall_at_k"]),
                    "ndcg_at_k": _round(item["ndcg_at_k"]),
                    "mrr": _round(item["mrr"]),
                    "ranking": item["ranking"][:10],
                    "diagnostic_hint": _failure_hint(failure_type),
                }
            )

    failures.sort(key=lambda item: (item["ndcg_at_k"], item["recall_at_k"]))
    return failures[:25]


def _claim_verdicts(
    primary_variant: str,
    reports: dict[str, dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> list[dict[str, str]]:
    by_baseline = {item["baseline_key"]: item for item in comparisons}

    verdicts = [
        _quality_verdict(comparisons),
        _comparison_verdict(
            "Query graph decomposition improves retrieval quality.",
            by_baseline.get("no_query_graph"),
            "ndcg_at_k",
        ),
        _comparison_verdict(
            "Adaptive routing improves over a fixed hybrid strategy.",
            by_baseline.get("fixed_hybrid"),
            "ndcg_at_k",
        ),
    ]

    no_pruning = by_baseline.get("no_pruning")
    full_diag = _diagnostic_summary(reports[primary_variant])
    if no_pruning:
        recall_delta = no_pruning["delta"].get("recall_at_k", 0.0)
        pruned = full_diag.get("avg_pruned_nodes", 0.0)
        if pruned > 0 and recall_delta >= -0.05:
            status = "supported"
        elif pruned > 0:
            status = "mixed"
        else:
            status = "not_supported"
        verdicts.append(
            {
                "claim": "Confidence pruning removes noisy evidence without large recall loss.",
                "status": status,
                "evidence": (
                    f"Full ARPO pruned {pruned:.2f} nodes/query on average with "
                    f"Recall@K delta {recall_delta:+.3f} vs no-pruning."
                ),
            }
        )

    return verdicts


def _quality_verdict(comparisons: list[dict[str, Any]]) -> dict[str, str]:
    if not comparisons:
        return {
            "claim": "Full ARPO improves retrieval quality over static baselines.",
            "status": "not_supported",
            "evidence": "No baselines were provided.",
        }

    ndcg_deltas = [item["delta"].get("ndcg_at_k", 0.0) for item in comparisons]
    positive = sum(1 for delta in ndcg_deltas if delta > 0)
    best_delta = min(ndcg_deltas)
    if positive == len(ndcg_deltas) and best_delta > 0:
        status = "supported"
    elif positive > 0:
        status = "mixed"
    else:
        status = "not_supported"
    return {
        "claim": "Full ARPO improves retrieval quality over static baselines.",
        "status": status,
        "evidence": f"NDCG@K improved against {positive}/{len(ndcg_deltas)} compared variants.",
    }


def _comparison_verdict(
    claim: str,
    comparison: dict[str, Any] | None,
    metric: str,
) -> dict[str, str]:
    if comparison is None:
        return {
            "claim": claim,
            "status": "not_supported",
            "evidence": "The required baseline was not included in this study.",
        }

    delta = comparison["delta"].get(metric, 0.0)
    p_value = comparison["paired_significance"].get(metric, {}).get("p_value", 1.0)
    if delta > 0 and p_value <= 0.10:
        status = "supported"
    elif delta > 0:
        status = "mixed"
    else:
        status = "not_supported"
    return {
        "claim": claim,
        "status": status,
        "evidence": (
            f"Delta {metric}={delta:+.3f} vs {comparison['baseline']} "
            f"(paired sign-test p={p_value:.4f})."
        ),
    }


def _failure_hint(failure_type: str) -> str:
    hints = {
        "missed_relevant_evidence": "Inspect query decomposition, bridge entities, and graph expansion depth.",
        "high_unsupported_claim_risk": "Review pruning threshold and contradiction-risk features for retained evidence.",
        "baseline_outperformed_arpo": "Compare ranking lineage against static baseline to isolate over-routing or reranking drift.",
    }
    return hints.get(failure_type, "Inspect query-level diagnostics.")


def _relative_delta(primary: float, baseline: float) -> float:
    if abs(baseline) < 1e-12:
        return 0.0
    return _round((primary - baseline) / abs(baseline))


def _mean(values: Any) -> float:
    values = list(values)
    return _round(sum(values) / len(values)) if values else 0.0


def _round(value: Any, digits: int = 4) -> float:
    return round(float(value), digits)
