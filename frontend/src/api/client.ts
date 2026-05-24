import {
  AblationReport,
  AblationReportSchema,
  CorporaResponse,
  CorporaResponseSchema,
  EvaluationReport,
  EvaluationReportSchema,
  PipelineResult,
  PipelineResultSchema,
  QuerySuggestionsResponse,
  QuerySuggestionsResponseSchema,
} from '../types/api';
import { DEFAULT_CORPUS_PATH, DEFAULT_QUERY_SET_PATH } from '../utils/corpora';

export interface SearchParams {
  query: string;
  top_k?: number;
  corpus_path?: string;
}

export async function checkHealth() {
  const res = await fetch('/api/health');
  if (!res.ok) throw new Error('API Offline');
  return res.json();
}

export async function listCorporaAPI(): Promise<CorporaResponse> {
  const response = await fetch('/api/corpora');
  await assertOk(response, 'Failed to load corpora');
  return CorporaResponseSchema.parse(await response.json());
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

  const response = await fetch(`/api/suggest?${query.toString()}`);
  await assertOk(response, 'Failed to load suggestions');
  return QuerySuggestionsResponseSchema.parse(await response.json());
}

export async function searchAPI(params: SearchParams): Promise<PipelineResult> {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
