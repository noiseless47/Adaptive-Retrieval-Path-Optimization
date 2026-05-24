import React, { useMemo, useState } from 'react';
import { useCorpora, useQuerySuggestions, useSearch } from '../../api/hooks';
import { useAppStore } from '../../store/app-store';
import {
  BrainCircuit,
  Database,
  Gauge,
  GitBranch,
  Play,
  ScanSearch,
  Settings2,
  SlidersHorizontal,
} from 'lucide-react';
import { QueryAnalysisCard } from './QueryAnalysisCard';
import { FieldLabel, SelectField, SelectOption, SliderField, TextAreaField } from '../ui/controls';
import { DEFAULT_CORPUS_PATH, corpusOptions as buildCorpusOptions, preferredCorpusPath } from '../../utils/corpora';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { QuerySuggestionPanel } from '../query/QuerySuggestionPanel';
import { QuerySuggestion } from '../../types/api';

const RETRIEVAL_MODES: SelectOption[] = [
  { label: 'Auto (Adaptive)', value: 'auto' },
  { label: 'Sparse Only', value: 'bm25_precision' },
  { label: 'Hybrid Balanced', value: 'hybrid_balanced' },
  { label: 'Graph + Dense', value: 'hybrid_graph_dense' },
];

const RERANKING_POLICIES: SelectOption[] = [
  { label: 'Auto (Adaptive)', value: 'auto' },
  { label: 'Precision Focus', value: 'precision' },
  { label: 'Contradiction Aware', value: 'contradiction_aware' },
  { label: 'Diversity Focus', value: 'diversity' },
];

export function RetrievalConsole() {
  const { state } = useAppStore();
  const searchMutation = useSearch();
  const corporaQuery = useCorpora();

  const initialQuery = state.currentResult?.query || '';
  const [query, setQuery] = useState(initialQuery);
  const [topK, setTopK] = useState(5);
  const [mode, setMode] = useState('auto');
  const [policy, setPolicy] = useState('auto');
  const [threshold, setThreshold] = useState(0.45);
  const [corpusPath, setCorpusPath] = useState(DEFAULT_CORPUS_PATH);

  const corpusOptions = useMemo<SelectOption[]>(() => {
    return buildCorpusOptions(corporaQuery.data?.corpora ?? []);
  }, [corporaQuery.data?.corpora]);

  const selectedCorpusPath = preferredCorpusPath(corporaQuery.data?.corpora ?? [], corpusPath);
  const debouncedQuery = useDebouncedValue(query, 180);
  const suggestionsQuery = useQuerySuggestions(debouncedQuery, selectedCorpusPath, 5);
  const suggestions = suggestionsQuery.data?.suggestions ?? [];
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [appliedSuggestionText, setAppliedSuggestionText] = useState('');
  const safeActiveSuggestionIndex = Math.min(activeSuggestionIndex, Math.max(suggestions.length - 1, 0));

  const handleRun = () => {
    if (!query.trim()) return;
    searchMutation.mutate({ query, top_k: topK, corpus_path: selectedCorpusPath });
  };

  const handleQueryChange = (nextQuery: string) => {
    setQuery(nextQuery);
    setActiveSuggestionIndex(0);
    setAppliedSuggestionText('');
  };

  const applySuggestion = (suggestion: QuerySuggestion) => {
    setQuery(suggestion.text);
    setActiveSuggestionIndex(0);
    setAppliedSuggestionText(suggestion.text);
  };

  const handleSuggestionKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (!suggestions.length) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSuggestionIndex((index) => (index + 1) % suggestions.length);
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSuggestionIndex((index) => (index - 1 + suggestions.length) % suggestions.length);
    }

    if (event.key === 'Tab' || (event.key === 'Enter' && !event.shiftKey)) {
      event.preventDefault();
      applySuggestion(suggestions[safeActiveSuggestionIndex] ?? suggestions[0]);
    }
  };

  const showSuggestions = query.trim().length >= 2
    && query !== appliedSuggestionText
    && (suggestions.length > 0 || suggestionsQuery.isFetching);

  return (
    <div className="flex h-full flex-col overflow-y-auto text-sm custom-scrollbar">
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-5 py-4">
        <div>
          <div className="flex items-center gap-2 font-semibold text-[var(--color-text-primary)]">
            <Settings2 size={16} className="text-[var(--color-accent-cyan)]" />
            Retrieval Console
          </div>
          <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">Adaptive path controls</div>
        </div>
        <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2 py-1 font-mono text-[10px] text-[var(--color-accent-cyan)]">
          LIVE
        </div>
      </div>

      <div className="flex-1 space-y-4 p-4">
        <section className="control-section space-y-3">
          <TextAreaField
            label="Query"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={handleSuggestionKeyDown}
            icon={<ScanSearch size={13} />}
            valueLabel={`${query.trim().length} chars`}
            placeholder="Describe a retrieval mission..."
          >
            {showSuggestions && (
              <QuerySuggestionPanel
                suggestions={suggestions}
                isLoading={suggestionsQuery.isFetching}
                activeIndex={safeActiveSuggestionIndex}
                onActiveIndex={setActiveSuggestionIndex}
                onSelect={applySuggestion}
                compact
              />
            )}
          </TextAreaField>
          <button
            onClick={handleRun}
            disabled={!query.trim() || searchMutation.isPending}
            className="group flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[linear-gradient(135deg,var(--color-accent-cyan),var(--color-accent-violet))] text-sm font-bold text-[var(--color-bg-base)] shadow-[0_18px_42px_-28px_var(--color-accent-cyan)] transition duration-200 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {searchMutation.isPending ? (
              <div className="h-4 w-4 rounded-full border-2 border-[var(--color-bg-base)] border-t-transparent animate-spin" />
            ) : (
              <Play size={16} fill="currentColor" className="transition-transform group-hover:translate-x-0.5" />
            )}
            {searchMutation.isPending ? 'Executing Pipeline...' : 'Run Search Pipeline'}
          </button>
        </section>

        <section className="control-section space-y-4">
          <FieldLabel label="Parameters" icon={<SlidersHorizontal size={13} />} />

          <SelectField
            label="Corpus"
            icon={<Database size={14} />}
            value={selectedCorpusPath}
            onChange={setCorpusPath}
            options={corpusOptions}
            accent="text-[var(--color-accent-violet)]"
          />

          <div className="grid grid-cols-2 gap-3">
            <SliderField
              label="Top K"
              value={topK}
              min={1}
              max={20}
              step={1}
              color="var(--color-accent-cyan)"
              onChange={(value) => setTopK(value)}
            />
            <SliderField
              label="Prune"
              value={threshold}
              min={0}
              max={1}
              step={0.05}
              color="var(--color-warning)"
              formatter={(value) => value.toFixed(2)}
              onChange={(value) => setThreshold(value)}
            />
          </div>

          <SelectField
            label="Retrieval Mode"
            icon={<GitBranch size={14} />}
            value={mode}
            onChange={setMode}
            options={RETRIEVAL_MODES}
            accent="text-[var(--color-accent-cyan)]"
          />

          <SelectField
            label="Reranking Policy"
            icon={<BrainCircuit size={14} />}
            value={policy}
            onChange={setPolicy}
            options={RERANKING_POLICIES}
            accent="text-[var(--color-accent-violet)]"
          />
        </section>

        {state.currentResult && (
          <section className="space-y-3">
            <div className="control-label px-1">
              <span className="flex items-center gap-2">
                <Gauge size={13} />
                Intelligence
              </span>
            </div>
            <QueryAnalysisCard analysis={state.currentResult.analysis} />
          </section>
        )}
      </div>
    </div>
  );
}
