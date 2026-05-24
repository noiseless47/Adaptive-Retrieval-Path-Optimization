import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, FileSearch, Network, Search, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { QuerySuggestion } from '../../types/api';
import { displayLabel } from '../../utils/format';

export function QuerySuggestionPanel({
  suggestions,
  isLoading,
  activeIndex,
  onActiveIndex,
  onSelect,
  compact = false,
  className,
}: {
  suggestions: QuerySuggestion[];
  isLoading: boolean;
  activeIndex: number;
  onActiveIndex: (index: number) => void;
  onSelect: (suggestion: QuerySuggestion) => void;
  compact?: boolean;
  className?: string;
}) {
  if (!isLoading && suggestions.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className={clsx(
        'overflow-hidden rounded-xl border border-[rgba(31,41,55,0.95)] bg-[rgba(11,16,32,0.97)] shadow-[0_24px_80px_-46px_rgba(0,0,0,0.96)] backdrop-blur-xl',
        compact ? 'mt-2' : 'mx-auto mt-3 max-w-3xl',
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-4 py-2.5">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
          <Search size={13} className="text-[var(--color-accent-cyan)]" />
          Corpus Autofill
        </div>
        <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
          {isLoading && suggestions.length === 0 ? 'Searching' : `${suggestions.length} matches`}
        </div>
      </div>

      <div className={clsx('custom-scrollbar overflow-y-auto p-1.5', compact ? 'max-h-[250px]' : 'max-h-[286px]')}>
        {isLoading && suggestions.length === 0 ? (
          <div className="space-y-2 p-2">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-10 rounded-lg bg-[rgba(31,41,55,0.44)] animate-pulse" />
            ))}
          </div>
        ) : (
          suggestions.map((suggestion, index) => (
            <button
              key={`${suggestion.kind}-${suggestion.text}`}
              type="button"
              onMouseEnter={() => onActiveIndex(index)}
              onClick={() => onSelect(suggestion)}
              className={clsx(
                'group flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition',
                index === activeIndex
                  ? 'bg-[rgba(34,211,238,0.1)] text-[var(--color-text-primary)]'
                  : 'text-[var(--color-text-muted)] hover:bg-[rgba(31,41,55,0.42)] hover:text-[var(--color-text-primary)]',
              )}
            >
              <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.72)] text-[var(--color-accent-cyan)]">
                {suggestionIcon(suggestion.kind)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium leading-5 text-[var(--color-text-primary)]">
                  {suggestion.text}
                </span>
                <span className="mt-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  {displayLabel(suggestion.kind)}
                  <span className="h-1 w-1 rounded-full bg-[var(--color-border-subtle)]" />
                  {displayLabel(suggestion.source)}
                </span>
              </span>
              <ArrowRight
                size={14}
                className={clsx(
                  'mt-1.5 shrink-0 transition',
                  index === activeIndex ? 'translate-x-0 text-[var(--color-accent-cyan)]' : '-translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100',
                )}
              />
            </button>
          ))
        )}
      </div>
    </motion.div>
  );
}

function suggestionIcon(kind: string) {
  switch (kind) {
    case 'brief':
      return <Sparkles size={14} />;
    case 'paper':
      return <FileSearch size={14} />;
    default:
      return <Network size={14} />;
  }
}
