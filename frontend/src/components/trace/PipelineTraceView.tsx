import React, { useEffect, useState } from 'react';
import { PipelineResult } from '../../types/api';
import { motion } from 'framer-motion';
import { Search, Network, Zap, Settings, GitBranch, Scissors, AlignLeft, MessageSquare } from 'lucide-react';
import { compactNumber, displayLabel, milliseconds } from '../../utils/format';

const STAGES = [
  { id: 'analysis', label: 'Query Analysis', icon: Search, metric: 'analysis_ms' },
  { id: 'graph', label: 'Query Graph', icon: Network, metric: 'query_graph_ms' },
  { id: 'strategy', label: 'Strategy Planning', icon: Settings, metric: 'strategy_ms' },
  { id: 'retrieval', label: 'Retrieval', icon: Zap, metric: 'retrieval_ms' },
  { id: 'expansion', label: 'Evidence Expansion', icon: GitBranch, metric: 'evidence_graph_ms' },
  { id: 'pruning', label: 'Confidence Pruning', icon: Scissors, metric: 'pruning_ms' },
  { id: 'reranking', label: 'Reranking', icon: AlignLeft, metric: 'reranking_ms' },
  { id: 'generation', label: 'Answer Generation', icon: MessageSquare, metric: 'generation_ms' },
];

export function PipelineTraceView({ result }: { result: PipelineResult }) {
  return <PipelineTraceContent key={`${result.query}-${result.diagnostics.candidate_count}`} result={result} />;
}

function PipelineTraceContent({ result }: { result: PipelineResult }) {
  const [activeStage, setActiveStage] = useState(0);
  const timings = (result.diagnostics.stage_timings_ms ?? {}) as Record<string, number>;

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStage((previous) => {
        if (previous < STAGES.length - 1) return previous + 1;
        clearInterval(interval);
        return previous;
      });
    }, 200);

    return () => clearInterval(interval);
  }, [result]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Pipeline Trace</h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Stage-by-stage diagnostics for the adaptive retrieval lifecycle.
          </p>
        </div>
        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] px-4 py-2 text-right">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Total Latency</div>
          <div className="font-mono text-sm font-semibold text-[var(--color-accent-cyan)]">
            {milliseconds(result.diagnostics.latency_ms)}
          </div>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-4">
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = index === activeStage;
          const isCompleted = index <= activeStage;
          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
              className={`rounded-lg border p-4 transition ${
                isActive
                  ? 'border-[var(--color-accent-cyan)] bg-[rgba(34,211,238,0.06)] shadow-[0_0_24px_-18px_var(--color-accent-cyan)]'
                  : isCompleted
                    ? 'border-[rgba(16,185,129,0.42)] bg-[rgba(16,185,129,0.04)]'
                    : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className={`grid h-9 w-9 place-items-center rounded-lg border ${
                  isCompleted ? 'border-[rgba(16,185,129,0.42)] text-[var(--color-success)]' : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)]'
                }`}>
                  <Icon size={16} />
                </div>
                <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
                  {milliseconds(timings[stage.metric] ?? 0)}
                </span>
              </div>
              <div className="mt-3 text-sm font-semibold text-[var(--color-text-primary)]">{stage.label}</div>
              <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                {isActive ? 'Running diagnostics' : isCompleted ? 'Completed' : 'Queued'}
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
            <Zap size={16} className="text-[var(--color-accent-violet)]" />
            Strategy Summary
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <DiagnosticMetric label="Retrieval Mode" value={displayLabel(result.strategy.strategy_id)} />
            <DiagnosticMetric label="Rerank Policy" value={displayLabel(result.strategy.reranking_mode)} />
            <DiagnosticMetric label="Target Evidence" value={result.strategy.top_k} />
            <DiagnosticMetric label="Maximum Hops" value={result.strategy.max_hops} />
            <DiagnosticMetric label="Pruning Threshold" value={compactNumber(result.strategy.pruning_threshold, 2)} highlight />
            <DiagnosticMetric label="Diversity Lambda" value={compactNumber(result.strategy.diversity_lambda, 2)} />
          </div>
        </div>

        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
            <Network size={16} className="text-[var(--color-accent-cyan)]" />
            Evidence Diagnostics
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <DiagnosticMetric label="Candidates Retrieved" value={result.diagnostics.candidate_count} />
            <DiagnosticMetric label="Nodes Before Pruning" value={result.diagnostics.evidence_nodes_before_pruning} />
            <DiagnosticMetric label="Nodes Retained" value={result.diagnostics.evidence_nodes_after_pruning} highlight />
            <DiagnosticMetric label="Edges Retained" value={result.diagnostics.evidence_edges_after_pruning} />
            <DiagnosticMetric label="Query Graph" value={result.diagnostics.query_graph_enabled ? 'Enabled' : 'Disabled'} />
            <DiagnosticMetric label="Total Latency" value={milliseconds(result.diagnostics.latency_ms)} highlight />
          </div>
        </div>
      </div>
    </div>
  );
}

function DiagnosticMetric({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</div>
      <div className={`mt-1 truncate font-mono text-base font-semibold ${highlight ? 'text-[var(--color-accent-cyan)]' : 'text-[var(--color-text-primary)]'}`}>
        {value}
      </div>
    </div>
  );
}
