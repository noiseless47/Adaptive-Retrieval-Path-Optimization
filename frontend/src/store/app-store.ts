import React, { createContext, useContext } from 'react';
import { PipelineResult } from '../types/api';

export type AppState = 'landing' | 'workspace';
export type ActiveTab = 'graph' | 'evidence' | 'trace' | 'analysis' | 'answer' | 'evaluation' | 'ablation';

interface State {
  appState: AppState;
  activeTab: ActiveTab;
  currentResult: PipelineResult | null;
  selectedEvidenceId: string | null;
  isSidebarOpen: boolean;
  isFeedExpanded: boolean;
}

type Action =
  | { type: 'SET_APP_STATE'; payload: AppState }
  | { type: 'SET_ACTIVE_TAB'; payload: ActiveTab }
  | { type: 'SET_RESULT'; payload: PipelineResult }
  | { type: 'SET_SELECTED_EVIDENCE'; payload: string | null }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'TOGGLE_FEED' };

export const initialState: State = {
  appState: 'landing',
  activeTab: 'graph',
  currentResult: null,
  selectedEvidenceId: null,
  isSidebarOpen: true,
  isFeedExpanded: true,
};

export function appReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_APP_STATE':
      return { ...state, appState: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_RESULT':
      return { ...state, currentResult: action.payload, appState: 'workspace' };
    case 'SET_SELECTED_EVIDENCE':
      return { ...state, selectedEvidenceId: action.payload };
    case 'TOGGLE_SIDEBAR':
      return { ...state, isSidebarOpen: !state.isSidebarOpen };
    case 'TOGGLE_FEED':
      return { ...state, isFeedExpanded: !state.isFeedExpanded };
    default:
      return state;
  }
}

export const AppContext = createContext<{ state: State; dispatch: React.Dispatch<Action> } | undefined>(undefined);

export function useAppStore() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppStore must be used within an AppProvider');
  }
  return context;
}
