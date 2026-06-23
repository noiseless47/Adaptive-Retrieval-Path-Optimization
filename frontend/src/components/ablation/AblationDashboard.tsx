import React, { useState } from 'react';
import { useAblation, useClaimStudy } from '../../api/hooks';
import { AblationReport, ClaimStudyReport } from '../../types/api';
import {
  BadgeCheck,
  BarChart3,
  Database,
  FileDown,
  FileText,
  LayoutGrid,
  ListOrdered,
  Microscope,
  Play,
  Rows3,
  Sigma,
  TriangleAlert,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import { StepperField, TextField } from '../ui/controls';
import { compactNumber, displayLabel, milliseconds } from '../../utils/format';
import { DEFAULT_CORPUS_PATH, DEFAULT_QUERY_SET_PATH } from '../../utils/corpora';

const VARIANTS = ['full', 'no_pruning', 'no_query_graph', 'sparse_only', 'dense_only', 'fixed_hybrid'];

export function AblationDashboard() {
  const ablationMutation = useAblation();
  const claimMutation = useClaimStudy();
  const [corpusPath, setCorpusPath] = useState(DEFAULT_CORPUS_PATH);
  const [queriesPath, setQueriesPath] = useState(DEFAULT_QUERY_SET_PATH);
  const [topK, setTopK] = useState(5);

  const handleRun = () => {
    ablationMutation.mutate({
      corpus_path: corpusPath,
      queries_path: queriesPath,
      top_k: topK,
      variants: VARIANTS,
    });
  };

  const handleClaimStudy = () => {
    claimMutation.mutate({
      corpus_path: corpusPath,
      queries_path: queriesPath,
      top_k: topK,
      variants: VARIANTS,
      benchmark: 'native',
      output_dir: 'data/experiments',
    });
  };

  const report: AblationReport | undefined = ablationMutation.data;
  const claimReport: ClaimStudyReport | undefined = claimMutation.data;

  return (
    <div className="h-full overflow-y-auto bg-[var(--color-bg-base)] p-6 custom-scrollbar">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.98),rgba(11,16,32,0.96))] p-3 shadow-[0_24px_70px_-58px_rgba(0,0,0,0.95)]">
          <div className="grid gap-3 2xl:grid-cols-[minmax(300px,0.8fr)_minmax(520px,1.35fr)_180px]">
            <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.48)] p-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-[var(--color-accent-cyan)] shadow-[0_0_26px_-18px_var(--color-accent-cyan)]">
                  <LayoutGrid size={18} />
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-accent-cyan)]">Strategy Study</div>
                  <h2 className="mt-1 text-xl font-semibold text-[var(--color-text-primary)]">Ablation Dashboard</h2>
                  <p className="mt-1 text-sm leading-5 text-[var(--color-text-muted)]">
                    Compare ARPO variants across graph, pruning, and retrieval policies.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.34)] p-4">
              <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)_128px]">
                <TextField label="Corpus Path" value={corpusPath} onChange={setCorpusPath} icon={<Database size={13} />} />
                <TextField label="Query Set" value={queriesPath} onChange={setQueriesPath} icon={<FileText size={13} />} />
                <StepperField
                  label="Top K"
                  value={topK}
                  min={1}
                  max={50}
                  onChange={setTopK}
                  icon={<ListOrdered size={13} />}
                  accent="var(--color-accent-cyan)"
                />
              </div>
            </div>

            <div className="grid gap-2">
              <button
                onClick={handleRun}
                disabled={ablationMutation.isPending}
                className="group flex min-h-[56px] items-center justify-center gap-3 rounded-lg border border-[rgba(34,211,238,0.38)] bg-[linear-gradient(135deg,var(--color-accent-cyan),#2dd4bf)] px-5 text-sm font-bold text-[var(--color-bg-base)] shadow-[0_24px_54px_-32px_var(--color-accent-cyan)] transition hover:brightness-110 disabled:opacity-50"
              >
                {ablationMutation.isPending ? (
                  <div className="h-5 w-5 rounded-full border-2 border-[var(--color-bg-base)] border-t-transparent animate-spin" />
                ) : (
                  <Play size={15} fill="currentColor" />
                )}
                <span className="text-left leading-tight">
                  <span className="block">Run Ablation</span>
                  <span className="block text-[11px] font-semibold uppercase tracking-wider text-[rgba(7,11,23,0.68)]">Compare Variants</span>
                </span>
              </button>
              <button
                onClick={handleClaimStudy}
                disabled={claimMutation.isPending}
                className="group flex min-h-[56px] items-center justify-center gap-3 rounded-lg border border-[rgba(139,92,246,0.44)] bg-[rgba(139,92,246,0.14)] px-5 text-sm font-bold text-[var(--color-text-primary)] shadow-[0_20px_48px_-34px_var(--color-accent-violet)] transition hover:border-[rgba(139,92,246,0.72)] hover:bg-[rgba(139,92,246,0.2)] disabled:opacity-50"
              >
                {claimMutation.isPending ? (
                  <div className="h-5 w-5 rounded-full border-2 border-[var(--color-accent-violet)] border-t-transparent animate-spin" />
                ) : (
                  <Microscope size={15} />
                )}
                <span className="text-left leading-tight">
                  <span className="block">Claim Study</span>
                  <span className="block text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Stats + Artifacts</span>
                </span>
              </button>
            </div>
          </div>
        </header>

        {ablationMutation.isError && (
          <div className="rounded-lg border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-4 text-sm text-[var(--color-danger)]">
            Ablation failed: {ablationMutation.error.message}
          </div>
        )}

        {claimMutation.isError && (
          <div className="rounded-lg border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-4 text-sm text-[var(--color-danger)]">
            Claim study failed: {claimMutation.error.message}
          </div>
        )}

        {report ? <AblationReportView report={report} /> : <EmptyAblationState />}
        {claimReport && <ClaimStudyReportView report={claimReport} />}
      </div>
    </div>
  );
}

function AblationReportView({ report }: { report: AblationReport }) {
  const chartData = report.results.map((variant) => ({
    ...variant,
    variantLabel: displayLabel(variant.variant),
  }));

  return (
    <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-5">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Strategy Comparison</h3>
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">
              {report.query_count ?? 0} queries across {report.results.length} variants
            </p>
          </div>
          <BarChart3 size={17} className="text-[var(--color-accent-cyan)]" />
        </div>
        <div className="h-[360px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
              <XAxis dataKey="variantLabel" stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} />
              <YAxis stroke="var(--color-text-muted)" domain={[0, 1]} tick={{ fontSize: 11 }} />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-panel)',
                  borderColor: 'var(--color-border-subtle)',
                  color: 'var(--color-text-primary)',
                  borderRadius: '8px',
                }}
                cursor={{ fill: 'var(--color-border-subtle)', opacity: 0.2 }}
              />
              <Legend wrapperStyle={{ paddingTop: '16px' }} />
              <Bar dataKey="recall_at_k" name="Recall @K" fill="var(--color-accent-violet)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="ndcg_at_k" name="NDCG @K" fill="var(--color-success)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="mrr" name="MRR" fill="var(--color-warning)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]">
        <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-5 py-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
            <Rows3 size={16} className="text-[var(--color-accent-cyan)]" />
            Variant Metrics
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]">
              <tr>
                <th className="px-5 py-3 font-semibold">Variant</th>
                <th className="px-5 py-3 font-semibold">Recall @K</th>
                <th className="px-5 py-3 font-semibold">NDCG @K</th>
                <th className="px-5 py-3 font-semibold">MRR</th>
                <th className="px-5 py-3 font-semibold">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {report.results.map((variant) => {
                const variantLabel = displayLabel(variant.variant);
                const isBase = variantLabel === 'Full ARPO';
                return (
                  <tr key={variant.variant} className={`${isBase ? 'bg-[rgba(34,211,238,0.05)]' : 'hover:bg-[rgba(11,16,32,0.72)]'} transition`}>
                    <td className="px-5 py-4 font-semibold text-[var(--color-text-primary)]">
                      {variantLabel}
                      {isBase && (
                        <span className="ml-2 rounded bg-[var(--color-accent-cyan)] px-1.5 py-0.5 text-[10px] uppercase text-[var(--color-bg-base)]">
                          Baseline
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 font-mono text-[var(--color-text-primary)]">{compactNumber(variant.recall_at_k)}</td>
                    <td className="px-5 py-4 font-mono text-[var(--color-success)]">{compactNumber(variant.ndcg_at_k)}</td>
                    <td className="px-5 py-4 font-mono text-[var(--color-text-primary)]">{compactNumber(variant.mrr)}</td>
                    <td className="px-5 py-4 font-mono text-[var(--color-text-muted)]">{milliseconds(variant.latency_ms)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </motion.div>
  );
}

function ClaimStudyReportView({ report }: { report: ClaimStudyReport }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5 rounded-lg border border-[rgba(139,92,246,0.34)] bg-[linear-gradient(180deg,rgba(17,24,39,0.96),rgba(11,16,32,0.98))] p-5 shadow-[0_26px_80px_-58px_var(--color-accent-violet)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-accent-violet)]">
            <Sigma size={14} />
            Research Claim Study
          </div>
          <h3 className="mt-1 text-lg font-semibold text-[var(--color-text-primary)]">{report.study_id}</h3>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {Number(report.benchmark.query_count ?? 0)} queries at k={report.top_k} against {report.primary_variant.label}
          </p>
        </div>
        {report.artifacts?.markdown && (
          <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.56)] px-3 py-2 text-xs text-[var(--color-text-muted)]">
            <div className="flex items-center gap-2 text-[var(--color-text-primary)]">
              <FileDown size={14} className="text-[var(--color-accent-cyan)]" />
              Report artifact
            </div>
            <div className="mt-1 max-w-[420px] truncate font-mono">{report.artifacts.markdown}</div>
          </div>
        )}
      </div>

      <div className="grid gap-3 lg:grid-cols-4">
        {report.claim_verdicts.map((verdict) => (
          <div key={verdict.claim} className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.5)] p-4">
            <div className="flex items-center gap-2">
              {verdict.status === 'supported' ? (
                <BadgeCheck size={16} className="text-[var(--color-success)]" />
              ) : (
                <TriangleAlert size={16} className={verdict.status === 'mixed' ? 'text-[var(--color-warning)]' : 'text-[var(--color-danger)]'} />
              )}
              <span className={`text-[11px] font-semibold uppercase tracking-wider ${verdict.status === 'supported' ? 'text-[var(--color-success)]' : verdict.status === 'mixed' ? 'text-[var(--color-warning)]' : 'text-[var(--color-danger)]'}`}>
                {displayLabel(verdict.status)}
              </span>
            </div>
            <div className="mt-3 text-sm font-semibold leading-5 text-[var(--color-text-primary)]">{verdict.claim}</div>
            <p className="mt-2 text-xs leading-5 text-[var(--color-text-muted)]">{verdict.evidence}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]">
          <div className="border-b border-[var(--color-border-subtle)] px-5 py-4">
            <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">Paired Baseline Comparisons</h4>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-5 py-3 font-semibold">Baseline</th>
                  <th className="px-5 py-3 font-semibold">Delta NDCG</th>
                  <th className="px-5 py-3 font-semibold">Delta Recall</th>
                  <th className="px-5 py-3 font-semibold">p-value</th>
                  <th className="px-5 py-3 font-semibold">95% CI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-subtle)]">
                {report.comparisons.map((comparison) => {
                  const stats = comparison.paired_significance.ndcg_at_k ?? {};
                  return (
                    <tr key={comparison.baseline_key} className="transition hover:bg-[rgba(11,16,32,0.72)]">
                      <td className="px-5 py-4 font-semibold text-[var(--color-text-primary)]">{comparison.baseline}</td>
                      <td className="px-5 py-4 font-mono text-[var(--color-success)]">{signed(comparison.delta.ndcg_at_k)}</td>
                      <td className="px-5 py-4 font-mono text-[var(--color-text-primary)]">{signed(comparison.delta.recall_at_k)}</td>
                      <td className="px-5 py-4 font-mono text-[var(--color-text-muted)]">{compactNumber(Number(stats.p_value ?? 1))}</td>
                      <td className="px-5 py-4 font-mono text-xs text-[var(--color-text-muted)]">
                        [{compactNumber(Number(stats.ci95_low ?? 0))}, {compactNumber(Number(stats.ci95_high ?? 0))}]
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-5">
          <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">Failure Analysis</h4>
          {report.failure_analysis.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--color-text-muted)]">No high-priority failures were detected in this run.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {report.failure_analysis.slice(0, 4).map((failure) => (
                <div key={failure.query_id} className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.45)] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{failure.query_id}</span>
                    <span className="rounded border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-warning)]">
                      {displayLabel(failure.failure_type)}
                    </span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-[var(--color-text-primary)]">{failure.query}</p>
                  <p className="mt-2 text-xs leading-5 text-[var(--color-text-muted)]">{failure.diagnostic_hint}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </motion.section>
  );
}

function EmptyAblationState() {
  return (
    <div className="rounded-lg border border-dashed border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.42)] p-10 text-center">
      <LayoutGrid className="mx-auto text-[var(--color-text-muted)]" />
      <h3 className="mt-4 text-sm font-semibold text-[var(--color-text-primary)]">No ablation study yet</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-[var(--color-text-muted)]">
        Run the configured variants to compare graph routing, pruning, sparse-only, dense-only, and fixed hybrid behavior.
      </p>
    </div>
  );
}

function signed(value: number | undefined) {
  const normalized = Number(value ?? 0);
  return `${normalized >= 0 ? '+' : ''}${compactNumber(normalized)}`;
}
