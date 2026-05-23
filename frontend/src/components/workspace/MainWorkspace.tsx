import React from 'react';
import { useAppStore } from '../../store/app-store';
import { Network, FileText, Activity, MessageSquare, Radar, Sparkles } from 'lucide-react';
import { QueryGraphView } from '../graphs/QueryGraphView';
import { EvidenceGraphView } from '../graphs/EvidenceGraphView';
import { RankedEvidencePanel } from '../evidence/RankedEvidencePanel';
import { PipelineTraceView } from '../trace/PipelineTraceView';
import { QueryRadarChart } from '../analysis/QueryRadarChart';
import { polishGeneratedText } from '../../utils/format';

export function MainWorkspace() {
  const { state, dispatch } = useAppStore();
  const { activeTab, currentResult } = state;

  if (!currentResult) {
    return (
      <div className="h-full flex items-center justify-center text-[var(--color-text-muted)]">
        Run a search to populate workspace.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-base)]">
      {/* Workspace Tabs */}
      <div className="flex px-2 pt-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] gap-1">
        <WorkspaceTab 
          id="graph" 
          label="Graphs" 
          icon={<Network size={14} />} 
          active={activeTab === 'graph'} 
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'graph' })}
        />
        <WorkspaceTab 
          id="evidence" 
          label="Ranked Evidence" 
          icon={<FileText size={14} />} 
          active={activeTab === 'evidence'} 
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'evidence' })}
        />
        <WorkspaceTab 
          id="trace" 
          label="Pipeline Trace" 
          icon={<Activity size={14} />} 
          active={activeTab === 'trace'} 
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'trace' })}
        />
        <WorkspaceTab 
          id="analysis" 
          label="Query Analysis" 
          icon={<Radar size={14} />} 
          active={activeTab === 'analysis'} 
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'analysis' })}
        />
        <WorkspaceTab 
          id="answer" 
          label="Answer" 
          icon={<MessageSquare size={14} />} 
          active={activeTab === 'answer'} 
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'answer' })}
        />
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'graph' && (
          <div className="absolute inset-0 grid grid-cols-[minmax(520px,0.56fr)_minmax(420px,0.44fr)]">
            <div className="relative flex min-w-0 flex-col border-r border-[var(--color-border-subtle)]">
              <div className="flex h-11 items-center justify-between border-b border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.7)] px-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
                  <Network size={14} className="text-[var(--color-accent-cyan)]" />
                  Query Graph
                </div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
                  semantic decomposition
                </div>
              </div>
              <div className="min-h-0 flex-1">
                <QueryGraphView graph={currentResult.query_graph} />
              </div>
            </div>
            <div className="relative flex min-w-0 flex-col">
              <div className="flex h-11 items-center justify-between border-b border-[var(--color-border-subtle)] bg-[rgba(17,24,39,0.7)] px-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
                  <FileText size={14} className="text-[var(--color-warning)]" />
                  Evidence Graph
                </div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
                  confidence + provenance
                </div>
              </div>
              <div className="min-h-0 flex-1">
                <EvidenceGraphView graph={currentResult.evidence_graph} />
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'evidence' && (
          <div className="h-full overflow-y-auto p-6 custom-scrollbar">
            <RankedEvidencePanel evidence={currentResult.ranked_evidence} />
          </div>
        )}

        {activeTab === 'trace' && (
          <div className="h-full overflow-y-auto p-6 custom-scrollbar">
            <PipelineTraceView result={currentResult} />
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="h-full flex items-center justify-center p-6">
            <QueryRadarChart analysis={currentResult.analysis} />
          </div>
        )}

        {activeTab === 'answer' && (
          <div className="h-full overflow-y-auto p-6 custom-scrollbar">
            <div className="mx-auto max-w-4xl space-y-5">
              <div className="flex items-end justify-between">
                <div>
                  <h2 className="flex items-center gap-2 text-lg font-semibold text-[var(--color-text-primary)]">
                    <MessageSquare className="text-[var(--color-accent-cyan)]" size={18} />
                    Grounded Answer
                  </h2>
                  <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                    Lightweight synthesis generated only after evidence pruning and reranking.
                  </p>
                </div>
                <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] px-3 py-1.5 text-xs text-[var(--color-text-muted)]">
                  {currentResult.ranked_evidence.length} evidence items
                </div>
              </div>
              <article className="rounded-lg border border-[var(--color-border-subtle)] bg-[linear-gradient(180deg,rgba(17,24,39,0.98),rgba(10,15,30,0.98))] p-6 leading-relaxed text-[var(--color-text-primary)] shadow-[0_24px_68px_-50px_rgba(0,0,0,0.95)]">
                <div className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                  <Sparkles size={14} className="text-[var(--color-accent-violet)]" />
                  Evidence-Grounded Response
                </div>
                <p className="whitespace-pre-wrap text-sm leading-7">{polishGeneratedText(currentResult.answer)}</p>
              </article>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function WorkspaceTab({ label, icon, active, onClick }: { id: string, label: string, icon: React.ReactNode, active: boolean, onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-medium transition-colors border-t border-x relative
        ${active 
          ? 'bg-[var(--color-bg-base)] text-[var(--color-accent-cyan)] border-[var(--color-border-subtle)]' 
          : 'bg-transparent text-[var(--color-text-muted)] border-transparent hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-base)]/50'}
      `}
    >
      {active && (
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-[var(--color-accent-cyan)] glow-cyan" />
      )}
      {icon}
      {label}
    </button>
  );
}
