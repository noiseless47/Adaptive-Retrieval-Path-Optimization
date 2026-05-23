import React from 'react';
import { Search, Command, LayoutGrid, TerminalSquare, FlaskConical } from 'lucide-react';
import { useAppStore } from '../../store/app-store';
import { AppTooltip } from '../ui/controls';

export function CommandBar() {
  const { state, dispatch } = useAppStore();
  const openPalette = () => window.dispatchEvent(new Event('arpo:open-command-palette'));

  return (
    <div className="h-12 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] flex items-center px-4 justify-between select-none">
      <div className="flex items-center gap-6">
        <div 
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => dispatch({ type: 'SET_APP_STATE', payload: 'landing' })}
        >
          <div className="w-6 h-6 rounded flex items-center justify-center bg-[var(--color-bg-panel)] border border-[var(--color-border-subtle)] group-hover:border-[var(--color-accent-cyan)] transition-colors">
            <span className="text-[var(--color-accent-cyan)] font-bold text-xs">A</span>
          </div>
          <span className="font-medium text-sm tracking-wide text-[var(--color-text-primary)]">ARPO</span>
        </div>

        <div className="flex gap-1">
          <TabButton 
            active={state.appState === 'workspace' && state.activeTab !== 'evaluation' && state.activeTab !== 'ablation'} 
            icon={<TerminalSquare size={14} />} 
            label="Console" 
            onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'graph' })}
          />
          <TabButton 
            active={state.appState === 'workspace' && state.activeTab === 'evaluation'} 
            icon={<FlaskConical size={14} />} 
            label="Evaluation" 
            onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'evaluation' })}
          />
          <TabButton 
            active={state.appState === 'workspace' && state.activeTab === 'ablation'} 
            icon={<LayoutGrid size={14} />} 
            label="Ablation" 
            onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'ablation' })}
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <AppTooltip label="Open command palette">
          <button
            onClick={openPalette}
            className="hidden items-center gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] md:flex"
          >
            <Search size={14} />
            <span>Search or command...</span>
            <div className="ml-2 flex items-center gap-0.5 opacity-70">
              <Command size={12} />
              <span>K</span>
            </div>
          </button>
        </AppTooltip>
        
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full bg-[var(--color-success)] shadow-[0_0_8px_var(--color-success)]"></div>
          <span className="text-[var(--color-text-muted)]">Connected</span>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  icon,
  label,
  disabled = false,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <div 
      onClick={disabled ? undefined : onClick}
      className={`
      flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
      ${active 
        ? 'bg-[var(--color-bg-panel)] text-[var(--color-text-primary)] shadow-sm border border-[var(--color-border-subtle)]' 
        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-panel)]/50 cursor-pointer border border-transparent'}
      ${disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}
    `}>
      {icon}
      {label}
    </div>
  );
}
