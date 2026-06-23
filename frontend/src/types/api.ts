import { z } from 'zod';

export const DocumentSchema = z.object({
  id: z.string(),
  title: z.string(),
  text: z.string(),
  metadata: z.record(z.string(), z.any()),
});

export const QueryAnalysisSchema = z.object({
  query_type: z.string(),
  complexity_score: z.number(),
  ambiguity_score: z.number(),
  required_hops: z.number(),
  retrieval_mode: z.string(),
  reranking_policy: z.string(),
  signals: z.record(z.string(), z.union([z.number(), z.string(), z.boolean()])),
});

export const QueryGraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.string(),
  weight: z.number(),
  terms: z.array(z.string()),
});

export const QueryGraphEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  relation: z.string(),
  weight: z.number(),
});

export const QueryGraphSchema = z.object({
  root_id: z.string(),
  nodes: z.array(QueryGraphNodeSchema),
  edges: z.array(QueryGraphEdgeSchema),
});

export const RetrievalStrategySchema = z.object({
  strategy_id: z.string(),
  sparse_weight: z.number(),
  dense_weight: z.number(),
  graph_weight: z.number(),
  top_k: z.number(),
  per_hop_k: z.number(),
  max_hops: z.number(),
  pruning_threshold: z.number(),
  diversity_lambda: z.number(),
  reranking_mode: z.string(),
});

export const EvidenceNodeSchema = z.object({
  document_id: z.string(),
  title: z.string(),
  score: z.number(),
  confidence: z.number(),
  claims: z.array(z.string()),
  lineage: z.array(z.string()),
});

export const EvidenceGraphNodeSchema = EvidenceNodeSchema.extend({
  id: z.string(),
  features: z.record(z.string(), z.union([z.number(), z.string(), z.boolean()])),
});

export const EvidenceEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  relation: z.string(),
  weight: z.number(),
});

export const EvidenceGraphSchema = z.object({
  nodes: z.array(EvidenceGraphNodeSchema),
  edges: z.array(EvidenceEdgeSchema),
});

export const PipelineResultSchema = z.object({
  query: z.string(),
  analysis: QueryAnalysisSchema,
  query_graph: QueryGraphSchema,
  strategy: RetrievalStrategySchema,
  evidence_graph: EvidenceGraphSchema,
  ranked_evidence: z.array(EvidenceNodeSchema),
  answer: z.string(),
  diagnostics: z.object({
    candidate_count: z.number(),
    evidence_nodes_before_pruning: z.number(),
    evidence_nodes_after_pruning: z.number(),
    evidence_edges_after_pruning: z.number(),
  }).catchall(z.any()),
});

// TypeScript Types
export type Document = z.infer<typeof DocumentSchema>;
export type QueryAnalysis = z.infer<typeof QueryAnalysisSchema>;
export type QueryGraphNode = z.infer<typeof QueryGraphNodeSchema>;
export type QueryGraphEdge = z.infer<typeof QueryGraphEdgeSchema>;
export type QueryGraph = z.infer<typeof QueryGraphSchema>;
export type RetrievalStrategy = z.infer<typeof RetrievalStrategySchema>;
export type EvidenceNode = z.infer<typeof EvidenceNodeSchema>;
export type EvidenceGraphNode = z.infer<typeof EvidenceGraphNodeSchema>;
export type EvidenceEdge = z.infer<typeof EvidenceEdgeSchema>;
export type EvidenceGraph = z.infer<typeof EvidenceGraphSchema>;
export type PipelineResult = z.infer<typeof PipelineResultSchema>;

// Phase 2 Types
export const EvaluationQueryReportSchema = z.object({
  id: z.string(),
  query: z.string(),
  query_type: z.string(),
  ranking: z.array(z.string()),
  precision_at_k: z.number(),
  recall_at_k: z.number(),
  ndcg_at_k: z.number(),
  latency_ms: z.number(),
  diagnostics: z.record(z.string(), z.any())
});

export const EvaluationReportSchema = z.object({
  top_k: z.number(),
  query_count: z.number(),
  precision_at_k: z.number(),
  recall_at_k: z.number(),
  ndcg_at_k: z.number(),
  mrr: z.number(),
  latency_ms: z.number(),
  queries: z.array(EvaluationQueryReportSchema)
});

export const AblationVariantSchema = z.object({
  variant: z.string(),
  recall_at_k: z.number(),
  ndcg_at_k: z.number(),
  mrr: z.number(),
  latency_ms: z.number()
});

export const AblationReportSchema = z.object({
  top_k: z.number().optional(),
  query_count: z.number().optional(),
  results: z.array(AblationVariantSchema)
});

export const ClaimStudyVariantSchema = z.object({
  variant_key: z.string(),
  variant: z.string(),
  summary: z.record(z.string(), z.any()),
  diagnostics: z.record(z.string(), z.any())
});

export const ClaimStudyComparisonSchema = z.object({
  primary_key: z.string(),
  primary: z.string(),
  baseline_key: z.string(),
  baseline: z.string(),
  delta: z.record(z.string(), z.number()),
  relative_delta: z.record(z.string(), z.number()),
  paired_significance: z.record(z.string(), z.any())
});

export const ClaimStudyVerdictSchema = z.object({
  claim: z.string(),
  status: z.string(),
  evidence: z.string()
});

export const ClaimStudyFailureSchema = z.object({
  query_id: z.string(),
  query: z.string(),
  query_type: z.string(),
  failure_type: z.string(),
  precision_at_k: z.number(),
  recall_at_k: z.number(),
  ndcg_at_k: z.number(),
  mrr: z.number(),
  ranking: z.array(z.string()),
  diagnostic_hint: z.string()
});

export const ClaimStudyReportSchema = z.object({
  study_id: z.string(),
  created_at: z.string(),
  corpus_path: z.string().nullable().optional(),
  queries_path: z.string().nullable().optional(),
  top_k: z.number(),
  primary_variant: z.object({
    key: z.string(),
    label: z.string()
  }),
  benchmark: z.record(z.string(), z.any()),
  metrics: z.array(z.string()),
  variants: z.array(ClaimStudyVariantSchema),
  comparisons: z.array(ClaimStudyComparisonSchema),
  slices: z.array(z.record(z.string(), z.any())),
  failure_analysis: z.array(ClaimStudyFailureSchema),
  claim_verdicts: z.array(ClaimStudyVerdictSchema),
  artifacts: z.record(z.string(), z.string()).optional(),
  run_id: z.string().optional()
}).catchall(z.any());

export const QuerySuggestionSchema = z.object({
  text: z.string(),
  kind: z.string(),
  source: z.string(),
  score: z.number(),
  metadata: z.record(z.string(), z.any()).optional()
});

export const QuerySuggestionsResponseSchema = z.object({
  suggestions: z.array(QuerySuggestionSchema)
});

export const CorpusInfoSchema = z.object({
  id: z.string(),
  path: z.string(),
  type: z.string(),
  documents: z.number().optional()
});

export const CorporaResponseSchema = z.object({
  corpora: z.array(CorpusInfoSchema)
});

export const RunRecordSchema = z.object({
  id: z.string(),
  run_type: z.string(),
  status: z.string(),
  request: z.record(z.string(), z.any()),
  response: z.record(z.string(), z.any()).nullable(),
  error: z.string().nullable(),
  latency_ms: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string()
});

export const RunsResponseSchema = z.object({
  runs: z.array(RunRecordSchema)
});

export const JobRecordSchema = z.object({
  id: z.string(),
  job_type: z.string(),
  status: z.string(),
  request: z.record(z.string(), z.any()),
  created_at: z.string(),
  updated_at: z.string(),
  result: z.record(z.string(), z.any()).nullable(),
  error: z.string().nullable(),
  latency_ms: z.number().nullable(),
  run_id: z.string().nullable()
});

export const JobsResponseSchema = z.object({
  jobs: z.array(JobRecordSchema)
});

export type EvaluationQueryReport = z.infer<typeof EvaluationQueryReportSchema>;
export type EvaluationReport = z.infer<typeof EvaluationReportSchema>;
export type AblationVariant = z.infer<typeof AblationVariantSchema>;
export type AblationReport = z.infer<typeof AblationReportSchema>;
export type ClaimStudyReport = z.infer<typeof ClaimStudyReportSchema>;
export type ClaimStudyVerdict = z.infer<typeof ClaimStudyVerdictSchema>;
export type ClaimStudyComparison = z.infer<typeof ClaimStudyComparisonSchema>;
export type QuerySuggestion = z.infer<typeof QuerySuggestionSchema>;
export type QuerySuggestionsResponse = z.infer<typeof QuerySuggestionsResponseSchema>;
export type CorpusInfo = z.infer<typeof CorpusInfoSchema>;
export type CorporaResponse = z.infer<typeof CorporaResponseSchema>;
export type RunRecord = z.infer<typeof RunRecordSchema>;
export type RunsResponse = z.infer<typeof RunsResponseSchema>;
export type JobRecord = z.infer<typeof JobRecordSchema>;
export type JobsResponse = z.infer<typeof JobsResponseSchema>;
