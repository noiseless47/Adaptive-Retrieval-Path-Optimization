from arpo.evaluation.metrics import (
    evidence_audit,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from arpo.evaluation.variants import DEFAULT_VARIANTS, VARIANT_LABELS, validate_variants, variant_controls

__all__ = [
    "DEFAULT_VARIANTS",
    "VARIANT_LABELS",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "evidence_audit",
    "evaluate_pipeline",
    "load_query_records",
    "validate_variants",
    "variant_controls",
]


def __getattr__(name: str):
    if name in {"evaluate_pipeline", "load_query_records"}:
        from arpo.evaluation.runner import evaluate_pipeline, load_query_records

        return {
            "evaluate_pipeline": evaluate_pipeline,
            "load_query_records": load_query_records,
        }[name]
    raise AttributeError(name)
