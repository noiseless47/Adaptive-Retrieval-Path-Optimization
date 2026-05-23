import React from 'react';
import { QueryAnalysis } from '../../types/api';
import { Activity, GitMerge, BrainCircuit } from 'lucide-react';
import { motion } from 'framer-motion';
import { displayLabel } from '../../utils/format';

export function QueryAnalysisCard({ analysis }: { analysis: QueryAnalysis }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(11,16,32,0.62)] p-4 shadow-[0_18px_44px_-34px_rgba(0,0,0,0.9)] space-y-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[var(--color-text-primary)] font-medium">
          <BrainCircuit size={16} className="text-[var(--color-accent-violet)]" />
          Intelligence
        </div>
        <div className="rounded-md border border-[var(--color-accent-violet)] bg-[rgba(139,92,246,0.08)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-accent-violet)] shadow-[0_0_18px_-10px_var(--color-accent-violet)]">
          {displayLabel(analysis.query_type)}
        </div>
      </div>

      <div className="space-y-3">
        <ScoreBar label="Complexity" score={analysis.complexity_score} color="bg-[var(--color-accent-cyan)]" />
        <ScoreBar label="Ambiguity" score={analysis.ambiguity_score} color="bg-[var(--color-warning)]" />
        
        <div className="flex items-center justify-between text-xs pt-2 border-t border-[var(--color-border-subtle)]">
          <span className="text-[var(--color-text-muted)] flex items-center gap-1">
            <GitMerge size={12} />
            Required Hops
          </span>
          <span className="font-mono text-[var(--color-text-primary)] font-medium">
            {analysis.required_hops}
          </span>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--color-text-muted)] flex items-center gap-1">
            <Activity size={12} />
            Entity Pressure
          </span>
          <span className="font-mono text-[var(--color-text-primary)] font-medium">
            {analysis.signals.entity_pressure as number}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

function ScoreBar({ label, score, color }: { label: string, score: number, color: string }) {
  const percentage = Math.round(score * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[var(--color-text-muted)]">{label}</span>
        <span className="font-mono text-[var(--color-text-primary)]">{percentage}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[rgba(31,41,55,0.92)]">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full ${color}`}
        />
      </div>
    </div>
  );
}
