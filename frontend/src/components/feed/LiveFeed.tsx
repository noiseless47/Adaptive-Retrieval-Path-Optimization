import React, { useEffect, useMemo, useState, useRef } from 'react';
import { useAppStore } from '../../store/app-store';
import { generateFeedEvents } from '../../utils/feed-simulator';
import { Terminal, X, ChevronDown, Check, Filter } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Select from '@radix-ui/react-select';
import { displayLabel } from '../../utils/format';

const FILTERS = ['all', 'info', 'retrieval', 'pruning', 'reranking', 'success', 'error'];

export function LiveFeed() {
  const { state, dispatch } = useAppStore();
  const [filter, setFilter] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const events = useMemo(
    () => (state.currentResult ? generateFeedEvents(state.currentResult) : []),
    [state.currentResult],
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const displayedEvents = filter ? events.filter((event) => event.type === filter) : events;

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-base)]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]">
        <div className="flex items-center gap-2 text-xs font-medium text-[var(--color-text-primary)]">
          <Terminal size={14} className="text-[var(--color-accent-cyan)]" />
          Live Retrieval Feed
        </div>
        <div className="flex items-center gap-2">
          <Select.Root value={filter || 'all'} onValueChange={(value) => setFilter(value === 'all' ? null : value)}>
            <Select.Trigger className="flex h-8 min-w-32 items-center gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] px-2 text-[11px] text-[var(--color-text-muted)] outline-none transition hover:border-[var(--color-text-muted)]">
              <Filter size={12} />
              <Select.Value />
              <Select.Icon asChild>
                <ChevronDown size={13} className="ml-auto" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="arpo-select-content" sideOffset={6} position="popper">
                <Select.Viewport className="p-1">
                  {FILTERS.map((type) => (
                    <Select.Item key={type} value={type} className="arpo-select-item">
                      <Select.ItemText>{type === 'all' ? 'All Events' : displayLabel(type)}</Select.ItemText>
                      <Select.ItemIndicator className="ml-auto">
                        <Check size={13} />
                      </Select.ItemIndicator>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
          <button 
            onClick={() => dispatch({ type: 'TOGGLE_FEED' })}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors p-1"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-1.5 custom-scrollbar">
        <AnimatePresence initial={false}>
          {displayedEvents.map((ev, index) => {
            let color = 'text-[var(--color-text-muted)]';
            if (ev.type === 'retrieval') color = 'text-[var(--color-accent-cyan)]';
            if (ev.type === 'pruning') color = 'text-[var(--color-warning)]';
            if (ev.type === 'reranking') color = 'text-[var(--color-accent-violet)]';
            if (ev.type === 'error') color = 'text-[var(--color-danger)]';
            if (ev.type === 'success') color = 'text-[var(--color-success)]';

            return (
              <motion.div 
                key={ev.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(index * 0.08, 0.8) }}
                className="flex items-start gap-3 hover:bg-[var(--color-bg-panel)] px-2 py-0.5 rounded transition-colors"
              >
                <span className="text-[var(--color-border-subtle)] flex-shrink-0">[{ev.timestamp}]</span>
                <span className={`${color} leading-relaxed break-words flex-1`}>{ev.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {events.length === 0 && (
          <div className="text-[var(--color-text-muted)] opacity-50 italic">Waiting for pipeline execution...</div>
        )}
      </div>
    </div>
  );
}
