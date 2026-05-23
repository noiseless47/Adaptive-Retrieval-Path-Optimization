import React, { useState } from 'react';
import { motion } from 'framer-motion';
import TextareaAutosize from 'react-textarea-autosize';
import { ArrowUp, BrainCircuit, Network, Plus, Sparkles } from 'lucide-react';
import { GridBackground } from './GridBackground';
import { useSearch } from '../../api/hooks';

const SAMPLE_PROMPTS = [
  {
    query: 'Papers where transformers replaced CNNs in medical imaging while reducing inference cost',
    tag: 'Scientific IR',
  },
  {
    query: 'How do graph retrieval systems reduce hallucination in multi-hop QA?',
    tag: 'Multi-Hop QA',
  },
  {
    query: 'Adaptive query decomposition for ambiguous complex search',
    tag: 'Query Routing',
  },
];

export function LandingView() {
  const [query, setQuery] = useState("");
  const searchMutation = useSearch();

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate({ query });
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[var(--color-bg-base)]">
      <GridBackground />

      <motion.aside
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: 'easeOut' }}
        className="absolute left-6 right-6 top-6 z-10 max-w-[460px] sm:left-8 sm:right-auto sm:top-8"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] glow-cyan">
            <span className="text-xl font-bold text-[var(--color-accent-cyan)]">A</span>
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-normal text-[var(--color-text-primary)]">ARPO Studio</h1>
            <p className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Adaptive Retrieval Observatory
            </p>
          </div>
        </div>

      </motion.aside>

      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.65, ease: 'easeOut', delay: 0.06 }}
        className="absolute right-6 top-[132px] z-10 grid w-[min(460px,calc(100vw-48px))] gap-2 sm:right-8 sm:top-8 sm:grid-cols-2"
      >
        <LandingSignal icon={<BrainCircuit size={14} />} label="Adaptive Query Routing" value="live" />
        <LandingSignal icon={<Network size={14} />} label="Graph Evidence Control" value="ready" />
      </motion.div>

      <main className="relative z-10 flex min-h-screen items-center justify-center px-6 py-28">
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.72, ease: 'easeOut', delay: 0.08 }}
          className="w-full max-w-3xl"
        >
          <h2 className="mb-9 text-center text-2xl font-medium text-[var(--color-text-primary)] sm:text-3xl">
            What retrieval path are you exploring?
          </h2>

          <form onSubmit={handleSearch} className="group relative">
            <div className="pointer-events-none absolute inset-0 rounded-[28px] bg-[var(--color-accent-cyan)] opacity-0 blur-2xl transition-opacity duration-500 group-focus-within:opacity-12" />
            <div className="relative overflow-hidden rounded-[24px] border border-[rgba(31,41,55,0.95)] bg-[rgba(17,24,39,0.92)] shadow-[0_30px_100px_-64px_rgba(0,0,0,1)] backdrop-blur-xl transition focus-within:border-[rgba(34,211,238,0.72)] focus-within:bg-[rgba(17,24,39,0.98)]">
              <TextareaAutosize
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask ARPO to resolve a complex research query..."
                minRows={3}
                maxRows={6}
                className="w-full resize-none bg-transparent px-6 pb-3 pt-5 text-[15px] leading-6 text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
                disabled={searchMutation.isPending}
              />
              <div className="flex items-center justify-between gap-3 px-4 pb-4">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="grid h-10 w-10 place-items-center rounded-full border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.72)] text-[var(--color-text-muted)] transition hover:border-[rgba(34,211,238,0.5)] hover:text-[var(--color-accent-cyan)]"
                    aria-label="Attach source"
                  >
                    <Plus size={18} strokeWidth={2.3} />
                  </button>
                  <div className="hidden items-center gap-2 rounded-full border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.6)] px-3 py-2 text-xs font-semibold text-[var(--color-text-muted)] sm:flex">
                    <Sparkles size={14} className="text-[var(--color-accent-cyan)]" />
                    OpenAlex corpus ready
                  </div>
                  <span className="hidden font-mono text-[11px] text-[var(--color-text-muted)] sm:inline">
                    {query.trim().length} chars
                  </span>
                </div>
                <button
                  type="submit"
                  disabled={!query.trim() || searchMutation.isPending}
                  className="grid h-10 w-10 place-items-center rounded-full bg-[linear-gradient(135deg,var(--color-accent-cyan),var(--color-accent-violet))] text-[var(--color-bg-base)] shadow-[0_16px_36px_-22px_var(--color-accent-cyan)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-45"
                  aria-label={searchMutation.isPending ? 'Executing pipeline' : 'Run pipeline'}
                >
                  {searchMutation.isPending ? (
                    <span className="h-4 w-4 rounded-full border-2 border-[var(--color-bg-base)] border-t-transparent animate-spin" />
                  ) : (
                    <ArrowUp size={18} strokeWidth={2.6} />
                  )}
                </button>
              </div>
            </div>
          </form>

          <div className="mx-auto mt-6 flex max-w-2xl flex-wrap justify-center gap-2">
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <motion.button
                key={prompt.query}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.22 + idx * 0.08 }}
                onClick={() => setQuery(prompt.query)}
                className="group inline-flex max-w-full items-center gap-2 rounded-full border border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.52)] px-4 py-2.5 text-left text-sm text-[var(--color-text-primary)] transition hover:border-[rgba(34,211,238,0.58)] hover:bg-[rgba(17,24,39,0.92)]"
              >
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-accent-cyan)] shadow-[0_0_10px_var(--color-accent-cyan)]" />
                <span className="truncate">{prompt.query}</span>
                <span className="hidden shrink-0 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] md:inline">
                  {prompt.tag}
                </span>
              </motion.button>
            ))}
          </div>
        </motion.section>
      </main>
    </div>
  );
}

function LandingSignal({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.55)] p-3 backdrop-blur-sm">
      <div className="flex items-center gap-2 text-[11px] font-semibold text-[var(--color-text-primary)]">
        <span className="text-[var(--color-accent-cyan)]">{icon}</span>
        {label}
      </div>
      <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-[var(--color-success)]">{value}</div>
    </div>
  );
}
