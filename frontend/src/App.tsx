import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './store/AppProvider';
import { useAppStore } from './store/app-store';
import { WorkspaceLayout } from './layouts/WorkspaceLayout';
import { LandingView } from './components/landing/LandingView';
import { TooltipProvider } from './components/ui/controls';

const queryClient = new QueryClient();

function AppContent() {
  const { state } = useAppStore();
  
  if (state.appState === 'landing') {
    return <LandingView />;
  }
  
  return <WorkspaceLayout />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AppProvider>
          <AppContent />
        </AppProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
