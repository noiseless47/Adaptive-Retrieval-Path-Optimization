import { ReactNode, useReducer } from 'react';
import { AppContext, appReducer, initialState } from './app-store';

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}
