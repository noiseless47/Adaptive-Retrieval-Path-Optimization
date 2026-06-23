import {
  AblationReport,
  AblationReportSchema,
  ClaimStudyReport,
  ClaimStudyReportSchema,
  CorporaResponse,
  CorporaResponseSchema,
  EvaluationReport,
  EvaluationReportSchema,
  JobRecord,
  JobRecordSchema,
  JobsResponse,
  JobsResponseSchema,
  PipelineResult,
  PipelineResultSchema,
  QuerySuggestionsResponse,
  QuerySuggestionsResponseSchema,
  RunRecord,
  RunRecordSchema,
  RunsResponse,
  RunsResponseSchema,
} from '../types/api';
import { DEFAULT_CORPUS_PATH, DEFAULT_QUERY_SET_PATH } from '../utils/corpora';

export interface SearchParams {
  query: string;
  top_k?: number;
  corpus_path?: string;
}

export async function checkHealth() {
  const res = await fetch('/api/health', { headers: apiHeaders() });
  if (!res.ok) throw new Error('API Offline');
  return res.json();
}

export async function listCorporaAPI(): Promise<CorporaResponse> {
  const response = await fetch('/api/corpora', { headers: apiHeaders() });
  await assertOk(response, 'Failed to load corpora');
  return CorporaResponseSchema.parse(await response.json());
}

export async function listRunsAPI(limit = 25): Promise<RunsResponse> {
  const response = await fetch(`/api/runs?limit=${limit}`, { headers: apiHeaders() });
  await assertOk(response, 'Failed to load runs');
  return RunsResponseSchema.parse(await response.json());
}

export async function getRunAPI(runId: string): Promise<RunRecord> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`, { headers: apiHeaders() });
  await assertOk(response, 'Failed to load run');
  return RunRecordSchema.parse(await response.json());
}

export async function listJobsAPI(limit = 25): Promise<JobsResponse> {
  const response = await fetch(`/api/jobs?limit=${limit}`, { headers: apiHeaders() });
  await assertOk(response, 'Failed to load jobs');
  return JobsResponseSchema.parse(await response.json());
}

export async function getJobAPI(jobId: string): Promise<JobRecord> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { headers: apiHeaders() });
  await assertOk(response, 'Failed to load job');
  return JobRecordSchema.parse(await response.json());
}

export interface SuggestParams {
  q: string;
  corpus_path?: string;
  limit?: number;
}

export async function suggestAPI(params: SuggestParams): Promise<QuerySuggestionsResponse> {
  const query = new URLSearchParams({
    q: params.q,
    corpus_path: params.corpus_path || DEFAULT_CORPUS_PATH,
    limit: String(params.limit || 8),
  });

  const response = await fetch(`/api/suggest?${query.toString()}`, { headers: apiHeaders() });
  await assertOk(response, 'Failed to load suggestions');
  return QuerySuggestionsResponseSchema.parse(await response.json());
}

export async function searchAPI(params: SearchParams): Promise<PipelineResult> {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query: params.query,
      top_k: params.top_k || 5,
      corpus_path: params.corpus_path || DEFAULT_CORPUS_PATH
    })
  });
  
  await assertOk(response, 'Search failed');
  
  const data = await response.json();
  return PipelineResultSchema.parse(data);
}

export interface EvaluateParams {
  corpus_path?: string;
  queries_path?: string;
  top_k?: number;
}

export async function evaluateAPI(params: EvaluateParams): Promise<EvaluationReport> {
  const response = await fetch('/api/evaluate', {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      corpus_path: params.corpus_path || DEFAULT_CORPUS_PATH,
      queries_path: params.queries_path || DEFAULT_QUERY_SET_PATH,
      top_k: params.top_k || 5
    })
  });
  await assertOk(response, 'Evaluation failed');
  return EvaluationReportSchema.parse(await response.json());
}

export interface AblationParams extends EvaluateParams {
  variants?: string[];
}

export async function ablationAPI(params: AblationParams): Promise<AblationReport> {
  const response = await fetch('/api/ablation', {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      corpus_path: params.corpus_path || DEFAULT_CORPUS_PATH,
      queries_path: params.queries_path || DEFAULT_QUERY_SET_PATH,
      top_k: params.top_k || 5,
      variants: params.variants || ["full", "no_pruning", "no_query_graph", "sparse_only", "dense_only", "fixed_hybrid"]
    })
  });
  await assertOk(response, 'Ablation failed');
  return AblationReportSchema.parse(await response.json());
}

export interface ClaimStudyParams extends AblationParams {
  benchmark?: 'auto' | 'native' | 'hotpotqa' | 'scifact' | 'beir';
  split?: string;
  output_dir?: string | null;
}

export async function claimStudyAPI(params: ClaimStudyParams): Promise<ClaimStudyReport> {
  const response = await fetch('/api/research/claim-study', {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      corpus_path: params.corpus_path || DEFAULT_CORPUS_PATH,
      queries_path: params.queries_path || DEFAULT_QUERY_SET_PATH,
      top_k: params.top_k || 5,
      variants: params.variants || ["full", "no_pruning", "no_query_graph", "sparse_only", "dense_only", "fixed_hybrid"],
      benchmark: params.benchmark || 'native',
      split: params.split || 'test',
      output_dir: params.output_dir === undefined ? 'data/experiments' : params.output_dir
    })
  });
  await assertOk(response, 'Claim study failed');
  return ClaimStudyReportSchema.parse(await response.json());
}

async function assertOk(response: Response, fallbackMessage: string): Promise<void> {
  if (response.ok) return;

  let detail: string | undefined;
  try {
    const payload = await response.json();
    detail = typeof payload?.detail === 'string' ? payload.detail : undefined;
  } catch {
    detail = undefined;
  }

  throw new Error(`${detail ?? fallbackMessage} (${response.status})`);
}

function apiHeaders(base: Record<string, string> = {}): Record<string, string> {
  const apiKey = import.meta.env.VITE_ARPO_API_KEY;
  if (!apiKey) return base;
  return { ...base, 'x-api-key': apiKey };
}
