from __future__ import annotations

from dataclasses import replace
from typing import Callable

from arpo.models import QueryAnalysis, RetrievalStrategy
from arpo.planning.strategy import RetrievalStrategyPlanner


StrategyFactory = Callable[[QueryAnalysis, int], RetrievalStrategy]


VARIANT_LABELS: dict[str, str] = {
    "full": "Full ARPO",
    "no_pruning": "No Pruning",
    "no_query_graph": "No Query Graph",
    "sparse_only": "Sparse Only",
    "dense_only": "Dense Only",
    "fixed_hybrid": "Fixed Hybrid",
}


DEFAULT_VARIANTS = tuple(VARIANT_LABELS)


def variant_controls(variant: str) -> tuple[StrategyFactory, bool]:
    planner = RetrievalStrategyPlanner()

    def planned(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
        return planner.plan(analysis, top_k=top_k)

    if variant == "full":
        return planned, False

    if variant == "no_pruning":

        def no_pruning_strategy(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
            strategy = planned(analysis, top_k)
            return replace(
                strategy,
                strategy_id=f"{strategy.strategy_id}_no_pruning",
                pruning_threshold=0.0,
            )

        return no_pruning_strategy, False

    if variant == "no_query_graph":

        def no_query_graph_strategy(analysis: QueryAnalysis, top_k: int) -> RetrievalStrategy:
            return replace(
                planned(analysis, top_k),
                strategy_id="no_query_graph",
                graph_weight=0.0,
                max_hops=1,
            )

        return no_query_graph_strategy, True

    if variant == "sparse_only":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="sparse_only",
                sparse_weight=1.0,
                dense_weight=0.0,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k, 8),
                max_hops=1,
                pruning_threshold=0.0,
                diversity_lambda=0.0,
                reranking_mode="precision",
            ),
            True,
        )

    if variant == "dense_only":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="dense_only",
                sparse_weight=0.0,
                dense_weight=1.0,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k, 8),
                max_hops=1,
                pruning_threshold=0.0,
                diversity_lambda=0.0,
                reranking_mode="semantic",
            ),
            True,
        )

    if variant == "fixed_hybrid":
        return (
            lambda analysis, top_k: RetrievalStrategy(
                strategy_id="fixed_hybrid",
                sparse_weight=0.5,
                dense_weight=0.5,
                graph_weight=0.0,
                top_k=top_k,
                per_hop_k=max(top_k + 2, 8),
                max_hops=1,
                pruning_threshold=0.4,
                diversity_lambda=0.2,
                reranking_mode="fixed",
            ),
            False,
        )

    raise ValueError(f"Unsupported ablation variant: {variant}")


def validate_variants(variants: list[str] | tuple[str, ...]) -> None:
    invalid = [variant for variant in variants if variant not in VARIANT_LABELS]
    if invalid:
        allowed = ", ".join(sorted(VARIANT_LABELS))
        raise ValueError(f"Unsupported variant(s): {', '.join(invalid)}. Allowed: {allowed}")
