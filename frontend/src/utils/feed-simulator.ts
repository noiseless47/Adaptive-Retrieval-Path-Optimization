import { PipelineResult } from '../types/api';
import { displayLabel } from './format';

export type FeedEvent = {
  id: string;
  timestamp: string;
  message: string;
  type: 'info' | 'retrieval' | 'pruning' | 'reranking' | 'success' | 'error';
};

function getTimestamp(delayMs: number): string {
  const d = new Date();
  d.setMilliseconds(d.getMilliseconds() + delayMs);
  return d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');
}

export function generateFeedEvents(result: PipelineResult): FeedEvent[] {
  const events: FeedEvent[] = [];
  let t = 0;

  const push = (message: string, type: FeedEvent['type'] = 'info', offset = 100) => {
    t += offset;
    events.push({
      id: `ev_${events.length}_${t}`,
      timestamp: getTimestamp(t),
      message,
      type
    });
  };

  push(`Query received: "${result.query}"`, 'info');
  push(`Analysis: classified as ${displayLabel(result.analysis.query_type)} with complexity ${result.analysis.complexity_score.toFixed(2)}`, 'info', 150);
  push(`Query decomposed into ${result.query_graph.nodes.filter(n => n.kind === 'intent').length} sub-intents`, 'info', 200);
  
  push(`Retrieval strategy selected: ${displayLabel(result.strategy.strategy_id)}`, 'retrieval', 50);
  push(`Executing parallel retrieval for sub-queries...`, 'retrieval', 300);
  push(`${result.diagnostics.candidate_count} candidates retrieved across all branches`, 'retrieval', 400);
  
  push(`Constructing evidence dependency graph...`, 'info', 150);
  push(`Evidence graph contains ${result.diagnostics.evidence_nodes_before_pruning} nodes before pruning`, 'info', 100);
  
  push(`Applying confidence pruning (threshold: ${result.strategy.pruning_threshold})`, 'pruning', 100);
  const prunedCount = result.diagnostics.evidence_nodes_before_pruning - result.diagnostics.evidence_nodes_after_pruning;
  push(`${prunedCount} noisy/unsupported nodes pruned`, 'pruning', 200);
  
  push(`Adaptive reranking activated with ${displayLabel(result.strategy.reranking_mode)} policy`, 'reranking', 50);
  push(`Final ranking completed. ${result.diagnostics.evidence_nodes_after_pruning} evidence items retained.`, 'reranking', 150);
  
  push(`Generating grounded answer...`, 'info', 200);
  push(`Pipeline execution completed successfully.`, 'success', 100);

  return events;
}
