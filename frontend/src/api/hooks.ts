import { useMutation, useQuery } from '@tanstack/react-query';
import {
  checkHealth,
  getJobAPI,
  getRunAPI,
  listCorporaAPI,
  listJobsAPI,
  listRunsAPI,
  searchAPI,
  SearchParams,
  suggestAPI,
} from './client';
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

import {
  ablationAPI,
  AblationParams,
  claimStudyAPI,
  ClaimStudyParams,
  evaluateAPI,
  EvaluateParams,
} from './client';

export function useCorpora() {
  return useQuery({
    queryKey: ['corpora'],
    queryFn: listCorporaAPI,
    staleTime: 15000,
  });
}

export function useRuns(limit = 25) {
  return useQuery({
    queryKey: ['runs', limit],
    queryFn: () => listRunsAPI(limit),
    staleTime: 10000,
  });
}

export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRunAPI(runId || ''),
    enabled: Boolean(runId),
    staleTime: 30000,
  });
}

export function useJobs(limit = 25) {
  return useQuery({
    queryKey: ['jobs', limit],
    queryFn: () => listJobsAPI(limit),
    refetchInterval: 3000,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobAPI(jobId || ''),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'completed' || status === 'failed' ? false : 1500;
    },
  });
}

export function useQuerySuggestions(q: string, corpusPath: string, limit = 7) {
  const normalized = q.trim();

  return useQuery({
    queryKey: ['query-suggestions', normalized.toLowerCase(), corpusPath, limit],
    queryFn: () => suggestAPI({ q: normalized, corpus_path: corpusPath, limit }),
    enabled: normalized.length >= 2,
    staleTime: 60000,
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

export function useClaimStudy() {
  return useMutation({
    mutationFn: (params: ClaimStudyParams) => claimStudyAPI(params)
  });
}
