import React from 'react';
import { useAppStore } from '../../store/app-store';
import { motion } from 'framer-motion';
import { Clock, Database, Search, Target, Zap } from 'lucide-react';
import { displayLabel, milliseconds, percent } from '../../utils/format';

export function MetricsHeader() {
  const { state } = useAppStore();
  const { currentResult } = state;

  if (!currentResult) return null;

  const { diagnostics, analysis, evidence_graph } = currentResult;
  
  // Calculate average confidence
  const avgConfidence = evidence_graph.nodes.length > 0 
    ? evidence_graph.nodes.reduce((acc, n) => acc + n.confidence, 0) / evidence_graph.nodes.length 
    : 0;

  return (
    <div className="h-10 bg-[var(--color-bg-panel)] border-b border-[var(--color-border-subtle)] flex items-center px-4 justify-between text-xs text-[var(--color-text-muted)]">
      <div className="flex items-center gap-4">
        <MetricBadge 
          icon={<Zap size={12} className="text-[var(--color-accent-cyan)]" />}
          label="Mode"
          value={displayLabel(analysis.retrieval_mode)}
        />
        <MetricBadge 
          icon={<Target size={12} className="text-[var(--color-accent-violet)]" />}
          label="Policy"
          value={displayLabel(analysis.reranking_policy)}
        />
      </div>

      <div className="flex items-center gap-6">
        <MetricItem 
          icon={<Search size={12} />}
          label="Retrieved"
          value={diagnostics.candidate_count}
        />
        <MetricItem 
          icon={<Database size={12} />}
          label="Retained"
          value={diagnostics.evidence_nodes_after_pruning}
        />
        <MetricItem 
          icon={<Target size={12} />}
          label="Avg Confidence"
          value={percent(avgConfidence)}
          highlight={avgConfidence > 0.8 ? 'text-[var(--color-success)]' : avgConfidence < 0.4 ? 'text-[var(--color-danger)]' : 'text-[var(--color-warning)]'}
        />
        <MetricItem 
          icon={<Clock size={12} />}
          label="Latency"
          value={milliseconds(diagnostics.latency_ms)}
        />
      </div>
    </div>
  );
}

function MetricBadge({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="opacity-60">{label}</span>
      <div className="flex items-center gap-1.5 bg-[var(--color-bg-base)] px-2 py-0.5 rounded border border-[var(--color-border-subtle)]">
        {icon}
        <span className="font-medium text-[var(--color-text-primary)]">{value}</span>
      </div>
    </div>
  );
}

function MetricItem({ icon, label, value, highlight }: { icon: React.ReactNode, label: string, value: string | number, highlight?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="opacity-60 flex items-center gap-1">
        {icon}
        {label}
      </span>
      <motion.span 
        key={String(value)}
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        className={`font-mono font-medium ${highlight || 'text-[var(--color-text-primary)]'}`}
      >
        {value}
      </motion.span>
    </div>
  );
}
