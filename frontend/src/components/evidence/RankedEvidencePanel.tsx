import React from 'react';
import { EvidenceNode } from '../../types/api';
import { motion } from 'framer-motion';
import { AlertCircle, ChevronDown, FileSearch, GitMerge, Link2, ShieldCheck } from 'lucide-react';
import { compactNumber, displayLabel, documentLabel } from '../../utils/format';

export function RankedEvidencePanel({ evidence }: { evidence: EvidenceNode[] }) {
  if (evidence.length === 0) {
    return (
      <div className="mx-auto mt-16 max-w-xl rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-8 text-center text-sm text-[var(--color-text-muted)]">
        No evidence retained after confidence pruning.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Ranked Evidence</h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Final retained evidence ordered by adaptive confidence and semantic relevance.
          </p>
        </div>
        <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] px-3 py-1.5 font-mono text-xs text-[var(--color-accent-cyan)]">
          {evidence.length} retained
        </div>
      </div>

      {evidence.map((node, index) => (
        <EvidenceCard key={`${node.document_id}-${index}`} node={node} rank={index + 1} />
      ))}
    </div>
  );
}

function EvidenceCard({ node, rank }: { node: EvidenceNode; rank: number }) {
  const [expanded, setExpanded] = React.useState(false);
  const confidencePercent = Math.round(node.confidence * 100);
  const confidenceColor =
    node.confidence > 0.8
      ? 'var(--color-success)'
      : node.confidence > 0.4
        ? 'var(--color-warning)'
        : 'var(--color-danger)';

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(rank * 0.06, 0.36) }}
      className="relative overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.98),rgba(10,15,30,0.98))] shadow-[0_24px_68px_-48px_rgba(0,0,0,0.95)]"
      style={{ borderLeft: `4px solid ${confidenceColor}` }}
    >
      <div className="grid gap-5 p-5 md:grid-cols-[64px_minmax(0,1fr)_180px]">
        <div className="flex flex-col items-center gap-2">
          <div className="grid h-12 w-12 place-items-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-lg font-semibold text-[var(--color-text-primary)]">
            {rank}
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Rank</span>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2 py-1 text-[11px] font-semibold text-[var(--color-accent-cyan)]">
              <Link2 size={12} />
              {documentLabel(node.document_id)}
            </span>
            {node.lineage[0] && (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2 py-1 text-[11px] text-[var(--color-text-muted)]">
                <GitMerge size={12} />
                {displayLabel(node.lineage[0])}
              </span>
            )}
          </div>
          <h3 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-[var(--color-text-primary)]">
            {node.title}
          </h3>
          <div className="mt-4 rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.55)] p-4">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
              <AlertCircle size={13} />
              Top Claim
            </div>
            <p className="text-sm leading-relaxed text-[var(--color-text-primary)]">
              {node.claims[0] || 'No extracted claim was returned by the pipeline.'}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <ScoreBlock label="Confidence" value={`${confidencePercent}%`} color={confidenceColor} />
          <ScoreBlock label="Retrieval Score" value={compactNumber(node.score)} />
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-xs font-semibold text-[var(--color-text-muted)] transition hover:border-[var(--color-accent-cyan)] hover:text-[var(--color-text-primary)]"
          >
            {expanded ? 'Hide Provenance' : 'Show Provenance'}
            <ChevronDown size={14} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="border-t border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.42)] p-5"
        >
          <div className="grid gap-5 md:grid-cols-[1fr_1.2fr]">
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
                <FileSearch size={14} className="text-[var(--color-accent-cyan)]" />
                Retrieval Lineage
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {node.lineage.map((step, index) => (
                  <React.Fragment key={`${step}-${index}`}>
                    <span className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2.5 py-1.5 text-xs text-[var(--color-text-muted)]">
                      {displayLabel(step)}
                    </span>
                    {index < node.lineage.length - 1 && <span className="text-[var(--color-border-subtle)]">-&gt;</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
                <ShieldCheck size={14} className="text-[var(--color-success)]" />
                Extracted Claims
              </div>
              <ul className="space-y-2">
                {node.claims.map((claim, index) => (
                  <li key={`${claim}-${index}`} className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-3 py-2 text-xs leading-relaxed text-[var(--color-text-muted)]">
                    {claim}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>
      )}
    </motion.article>
  );
}

function ScoreBlock({ label, value, color = 'var(--color-text-primary)' }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</div>
      <div className="mt-1 text-lg font-semibold" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
