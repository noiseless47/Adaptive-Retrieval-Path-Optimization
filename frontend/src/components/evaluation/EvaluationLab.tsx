import React, { useState } from 'react';
import { useEvaluation } from '../../api/hooks';
import { EvaluationReport } from '../../types/api';
import { Database, FileText, FlaskConical, Gauge, ListOrdered, Play, Rows3 } from 'lucide-react';
import { MetricsBarChart } from './MetricsBarChart';
import { motion } from 'framer-motion';
import { StepperField, TextField } from '../ui/controls';
import { compactNumber, displayLabel, milliseconds } from '../../utils/format';

export function EvaluationLab() {
  const evalMutation = useEvaluation();
  const [corpusPath, setCorpusPath] = useState('examples/corpus.jsonl');
  const [queriesPath, setQueriesPath] = useState('examples/queries.jsonl');
  const [topK, setTopK] = useState(5);

  const handleRun = () => {
    evalMutation.mutate({ corpus_path: corpusPath, queries_path: queriesPath, top_k: topK });
  };

  const report: EvaluationReport | undefined = evalMutation.data;

  return (
    <div className="h-full overflow-y-auto bg-[var(--color-bg-base)] p-6 custom-scrollbar">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.98),rgba(11,16,32,0.96))] p-3 shadow-[0_24px_70px_-58px_rgba(0,0,0,0.95)]">
          <div className="grid gap-3 2xl:grid-cols-[minmax(300px,0.8fr)_minmax(520px,1.35fr)_180px]">
            <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.48)] p-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-[var(--color-accent-violet)] shadow-[0_0_26px_-18px_var(--color-accent-violet)]">
                  <FlaskConical size={18} />
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-accent-violet)]">Experiment Run</div>
                  <h2 className="mt-1 text-xl font-semibold text-[var(--color-text-primary)]">Evaluation Lab</h2>
                  <p className="mt-1 text-sm leading-5 text-[var(--color-text-muted)]">
                    Batch score retrieval quality across query sets and corpora.
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
                  accent="var(--color-accent-violet)"
                />
              </div>
            </div>

            <button
              onClick={handleRun}
              disabled={evalMutation.isPending}
              className="group flex min-h-[76px] items-center justify-center gap-3 rounded-lg border border-[rgba(139,92,246,0.38)] bg-[linear-gradient(135deg,var(--color-accent-violet),#6d5dfc)] px-5 text-sm font-bold text-white shadow-[0_24px_54px_-32px_var(--color-accent-violet)] transition hover:brightness-110 disabled:opacity-50"
            >
              {evalMutation.isPending ? (
                <div className="h-5 w-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/12 transition group-hover:bg-white/18">
                  <Play size={15} fill="currentColor" />
                </span>
              )}
              <span className="text-left leading-tight">
                <span className="block">Run Evaluation</span>
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-white/70">Batch Metrics</span>
              </span>
            </button>
          </div>
        </header>

        {evalMutation.isError && (
          <div className="rounded-lg border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-4 text-sm text-[var(--color-danger)]">
            Evaluation failed: {evalMutation.error.message}
          </div>
        )}

        {report ? <EvaluationReportView report={report} /> : <EmptyEvaluationState />}
      </div>
    </div>
  );
}

function EvaluationReportView({ report }: { report: EvaluationReport }) {
  return (
    <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-5">
        <MetricCard label="Precision @K" value={compactNumber(report.precision_at_k)} />
        <MetricCard label="Recall @K" value={compactNumber(report.recall_at_k)} />
        <MetricCard label="NDCG @K" value={compactNumber(report.ndcg_at_k)} highlight />
        <MetricCard label="MRR" value={compactNumber(report.mrr)} />
        <MetricCard label="Latency" value={milliseconds(report.latency_ms)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Aggregate Performance</h3>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">{report.query_count} queries at k={report.top_k}</p>
            </div>
            <Gauge size={17} className="text-[var(--color-accent-cyan)]" />
          </div>
          <MetricsBarChart report={report} />
        </section>

        <section className="overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]">
          <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-5 py-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
              <Rows3 size={16} className="text-[var(--color-accent-violet)]" />
              Query-Level Results
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-5 py-3 font-semibold">Query ID</th>
                  <th className="px-5 py-3 font-semibold">Query</th>
                  <th className="px-5 py-3 font-semibold">Type</th>
                  <th className="px-5 py-3 font-semibold">NDCG @K</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-subtle)]">
                {report.queries.map((query) => (
                  <tr key={query.id} className="transition hover:bg-[rgba(11,16,32,0.72)]">
                    <td className="px-5 py-4 font-mono text-xs text-[var(--color-text-muted)]">{query.id}</td>
                    <td className="max-w-md px-5 py-4 text-[var(--color-text-primary)]">
                      <div className="line-clamp-2">{query.query}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2 py-1 text-[11px] font-semibold text-[var(--color-accent-violet)]">
                        {displayLabel(query.query_type)}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono text-[var(--color-success)]">{compactNumber(query.ndcg_at_k)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </motion.div>
  );
}

function EmptyEvaluationState() {
  return (
    <div className="rounded-lg border border-dashed border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.42)] p-10 text-center">
      <FlaskConical className="mx-auto text-[var(--color-text-muted)]" />
      <h3 className="mt-4 text-sm font-semibold text-[var(--color-text-primary)]">No evaluation run yet</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-[var(--color-text-muted)]">
        Choose a corpus and query set, then run evaluation to inspect aggregate and query-level retrieval quality.
      </p>
    </div>
  );
}

function MetricCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border bg-[var(--color-bg-panel)] p-4 ${highlight ? 'border-[var(--color-accent-cyan)] shadow-[0_0_28px_-22px_var(--color-accent-cyan)]' : 'border-[var(--color-border-subtle)]'}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${highlight ? 'text-[var(--color-accent-cyan)]' : 'text-[var(--color-text-primary)]'}`}>
        {value}
      </div>
    </div>
  );
}
