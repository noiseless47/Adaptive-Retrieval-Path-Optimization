import { useMutation, useQuery } from '@tanstack/react-query';
import { checkHealth, listCorporaAPI, searchAPI, SearchParams } from './client';
import { useAppStore } from '../store/app-store';

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 10000,
  });
}

export function useSearch() {
  const { dispatch } = useAppStore();
  
  return useMutation({
    mutationFn: (params: SearchParams) => searchAPI(params),
    onSuccess: (data) => {
      dispatch({ type: 'SET_RESULT', payload: data });
      dispatch({ type: 'SET_APP_STATE', payload: 'workspace' });
    },
  });
}

import { evaluateAPI, ablationAPI, EvaluateParams, AblationParams } from './client';

export function useCorpora() {
  return useQuery({
    queryKey: ['corpora'],
    queryFn: listCorporaAPI,
    staleTime: 15000,
  });
}

export function useEvaluation() {
  return useMutation({
    mutationFn: (params: EvaluateParams) => evaluateAPI(params)
  });
}

export function useAblation() {
  return useMutation({
    mutationFn: (params: AblationParams) => ablationAPI(params)
  });
}
