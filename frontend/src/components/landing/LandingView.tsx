import React, { useState } from 'react';
import { motion } from 'framer-motion';
import TextareaAutosize from 'react-textarea-autosize';
import { BrainCircuit, Network, Play, ScanSearch } from 'lucide-react';
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
    <div className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-[var(--color-bg-base)]">
      <GridBackground />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
        className="z-10 grid w-full max-w-5xl gap-6 px-6 lg:grid-cols-[0.86fr_1.14fr] lg:items-center"
      >
        <section className="space-y-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] glow-cyan">
              <span className="text-xl font-bold text-[var(--color-accent-cyan)]">A</span>
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-normal text-[var(--color-text-primary)]">ARPO Studio</h1>
              <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                Adaptive Retrieval Observatory
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <LandingSignal icon={<BrainCircuit size={15} />} label="Adaptive Query Routing" value="live" />
            <LandingSignal icon={<Network size={15} />} label="Graph Evidence Control" value="ready" />
          </div>
        </section>

        <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.96),rgba(8,13,26,0.96))] p-4 shadow-[0_30px_90px_-58px_rgba(0,0,0,1)]">
          <form onSubmit={handleSearch} className="group relative">
            <div className="pointer-events-none absolute inset-0 rounded-lg bg-[var(--color-accent-cyan)] opacity-0 blur-2xl transition-opacity duration-500 group-focus-within:opacity-10" />
            <div className="relative rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] transition focus-within:border-[var(--color-accent-cyan)]">
              <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <ScanSearch size={14} className="text-[var(--color-accent-cyan)]" />
                Research Query
              </div>
              <TextareaAutosize
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Enter a complex retrieval query..."
                minRows={3}
                maxRows={7}
                className="w-full resize-none bg-transparent px-4 py-4 text-sm leading-6 text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
                disabled={searchMutation.isPending}
              />
              <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border-subtle)] px-4 py-3">
                <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{query.trim().length} chars</span>
                <button
                  type="submit"
                  disabled={!query.trim() || searchMutation.isPending}
                  className="flex h-10 items-center gap-2 rounded-lg bg-[linear-gradient(135deg,var(--color-accent-cyan),var(--color-accent-violet))] px-4 text-sm font-bold text-[var(--color-bg-base)] transition hover:brightness-110 disabled:opacity-50"
                >
                  {searchMutation.isPending ? (
                    <span className="h-4 w-4 rounded-full border-2 border-[var(--color-bg-base)] border-t-transparent animate-spin" />
                  ) : (
                    <Play size={14} fill="currentColor" />
                  )}
                  {searchMutation.isPending ? 'Executing' : 'Run Pipeline'}
                </button>
              </div>
            </div>
          </form>

          <div className="mt-4 grid gap-3">
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <motion.button
                key={prompt.query}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.18 + idx * 0.08 }}
                onClick={() => setQuery(prompt.query)}
                className="group flex items-start gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(11,16,32,0.58)] px-4 py-3 text-left transition hover:border-[var(--color-accent-cyan)] hover:bg-[rgba(11,16,32,0.86)]"
              >
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-accent-cyan)] shadow-[0_0_10px_var(--color-accent-cyan)]" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm leading-5 text-[var(--color-text-primary)]">{prompt.query}</span>
                  <span className="mt-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                    {prompt.tag}
                  </span>
                </span>
              </motion.button>
            ))}
          </div>
        </section>
      </motion.div>
    </div>
  );
}

function LandingSignal({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.62)] p-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
        <span className="text-[var(--color-accent-cyan)]">{icon}</span>
        {label}
      </div>
      <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-[var(--color-success)]">{value}</div>
    </div>
  );
}
