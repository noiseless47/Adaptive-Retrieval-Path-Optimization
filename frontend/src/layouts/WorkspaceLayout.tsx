import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store/app-store';

import { CommandBar } from '../components/command/CommandBar';
import { MetricsHeader } from '../components/metrics/MetricsHeader';
import { RetrievalConsole } from '../components/console/RetrievalConsole';
import { MainWorkspace } from '../components/workspace/MainWorkspace';
import { LiveFeed } from '../components/feed/LiveFeed';
import { CommandPalette } from '../components/command/CommandPalette';
import { EvaluationLab } from '../components/evaluation/EvaluationLab';
import { AblationDashboard } from '../components/ablation/AblationDashboard';

export function WorkspaceLayout() {
  const { state } = useAppStore();

  let Content = <MainWorkspace />;
  if (state.activeTab === 'evaluation') {
    Content = <EvaluationLab />;
  } else if (state.activeTab === 'ablation') {
    Content = <AblationDashboard />;
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-screen w-full flex flex-col bg-[var(--color-bg-base)] text-[var(--color-text-primary)] overflow-hidden"
    >
      <CommandPalette />
      
      {/* Top Bar area */}
      <div className="flex-none z-20 shadow-md">
        <CommandBar />
        <MetricsHeader />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* Left Sidebar (Console) */}
        <AnimatePresence initial={false}>
          {state.isSidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 380, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="h-full max-w-[40vw] border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] flex-shrink-0 overflow-y-auto"
            >
              <RetrievalConsole />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center Workspace */}
        <div className="flex-1 flex flex-col min-w-0 h-full relative">
          <div className="flex-1 overflow-hidden relative">
            {Content}
          </div>
          
          {/* Bottom Live Feed */}
          <AnimatePresence>
            {state.isFeedExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 170, opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="flex-none border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)]"
              >
                <LiveFeed />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
