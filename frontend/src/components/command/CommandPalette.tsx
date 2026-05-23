import React, { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { Search, Database, LayoutGrid, Terminal, X, Play, Radar, FileText } from 'lucide-react';
import { useAppStore } from '../../store/app-store';

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const { dispatch } = useAppStore();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    const openPalette = () => setOpen(true);
    window.addEventListener('arpo:open-command-palette', openPalette);
    return () => {
      document.removeEventListener('keydown', down);
      window.removeEventListener('arpo:open-command-palette', openPalette);
    };
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-[#020617b8] px-4 pt-[13vh] backdrop-blur-md">
      <div className="w-full max-w-2xl overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.98),rgba(8,13,26,0.98))] shadow-[0_34px_100px_-52px_rgba(0,0,0,1)] animate-in fade-in zoom-in-95 duration-200">
        <Command label="Global Command Menu" className="flex h-full w-full flex-col">
          <div className="flex items-center border-b border-[var(--color-border-subtle)] px-4">
            <Search size={16} className="mr-3 text-[var(--color-accent-cyan)]" />
            <Command.Input 
              placeholder="Type a command or search..." 
              className="w-full border-none bg-transparent py-4 text-sm text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
              autoFocus
            />
            <button
              onClick={() => setOpen(false)}
              className="grid h-8 w-8 place-items-center rounded-md text-[var(--color-text-muted)] transition hover:bg-[var(--color-bg-base)] hover:text-[var(--color-text-primary)]"
              aria-label="Close command palette"
            >
              <X size={16} />
            </button>
          </div>
          
          <Command.List className="max-h-[380px] overflow-y-auto p-2 custom-scrollbar">
            <Command.Empty className="py-6 text-center text-sm text-[var(--color-text-muted)]">
              No results found.
            </Command.Empty>

            <Command.Group heading="Navigation" className="text-xs font-medium text-[var(--color-text-muted)] px-2 py-1.5 [&_[cmdk-group-heading]]:mb-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
              <Command.Item 
                onSelect={() => { dispatch({ type: 'SET_ACTIVE_TAB', payload: 'graph' }); setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)] aria-selected:text-[var(--color-accent-cyan)]"
              >
                <CommandIcon tone="cyan"><LayoutGrid size={14} /></CommandIcon>
                <span className="flex-1">Open Graph Workspace</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Graph</span>
              </Command.Item>
              <Command.Item
                onSelect={() => { dispatch({ type: 'SET_ACTIVE_TAB', payload: 'evidence' }); setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)] aria-selected:text-[var(--color-accent-cyan)]"
              >
                <CommandIcon tone="violet"><FileText size={14} /></CommandIcon>
                <span className="flex-1">Open Ranked Evidence</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Evidence</span>
              </Command.Item>
              <Command.Item
                onSelect={() => { dispatch({ type: 'SET_ACTIVE_TAB', payload: 'analysis' }); setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)] aria-selected:text-[var(--color-accent-cyan)]"
              >
                <CommandIcon tone="amber"><Radar size={14} /></CommandIcon>
                <span className="flex-1">Open Query Analysis</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Signals</span>
              </Command.Item>
              <Command.Item 
                onSelect={() => { dispatch({ type: 'TOGGLE_FEED' }); setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)] aria-selected:text-[var(--color-accent-cyan)]"
              >
                <CommandIcon tone="cyan"><Terminal size={14} /></CommandIcon>
                <span className="flex-1">Toggle Live Retrieval Feed</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Trace</span>
              </Command.Item>
            </Command.Group>

            <Command.Separator className="h-px bg-[var(--color-border-subtle)] my-1" />

            <Command.Group heading="Actions" className="text-xs font-medium text-[var(--color-text-muted)] px-2 py-1.5 [&_[cmdk-group-heading]]:mb-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
              <Command.Item 
                onSelect={() => { setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)] aria-selected:text-[var(--color-accent-violet)]"
              >
                <CommandIcon tone="violet"><Play size={14} /></CommandIcon>
                <span className="flex-1">Run New Search</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Pipeline</span>
              </Command.Item>
              <Command.Item 
                onSelect={() => { setOpen(false); }}
                className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-primary)] aria-selected:bg-[var(--color-bg-base)]"
              >
                <CommandIcon tone="amber"><Database size={14} /></CommandIcon>
                <span className="flex-1">Switch Corpus</span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Source</span>
              </Command.Item>
            </Command.Group>

          </Command.List>
        </Command>
      </div>
    </div>
  );
}

function CommandIcon({ children, tone }: { children: React.ReactNode; tone: 'cyan' | 'violet' | 'amber' }) {
  const color =
    tone === 'cyan'
      ? 'text-[var(--color-accent-cyan)]'
      : tone === 'violet'
        ? 'text-[var(--color-accent-violet)]'
        : 'text-[var(--color-warning)]';

  return (
    <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] ${color}`}>
      {children}
    </span>
  );
}
