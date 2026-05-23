const ACRONYMS = new Map<string, string>([
  ['api', 'API'],
  ['arpo', 'ARPO'],
  ['bm25', 'BM25'],
  ['cnn', 'CNN'],
  ['cnns', 'CNNs'],
  ['id', 'ID'],
  ['ir', 'IR'],
  ['mrr', 'MRR'],
  ['ndcg', 'NDCG'],
  ['qa', 'QA'],
  ['rag', 'RAG'],
]);

export function displayLabel(value: unknown): string {
  if (value === null || value === undefined) return 'Not Available';

  const normalized = String(value)
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) return 'Not Available';

  return normalized
    .split(' ')
    .map((word) => {
      const key = word.toLowerCase();
      if (ACRONYMS.has(key)) return ACRONYMS.get(key);
      if (/^@?k$/i.test(word)) return '@K';
      return key.charAt(0).toUpperCase() + key.slice(1);
    })
    .join(' ');
}

export function compactNumber(value: number, digits = 3): string {
  return Number.isFinite(value) ? value.toFixed(digits) : '0'.padEnd(digits + 2, '0');
}

export function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function milliseconds(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '0 ms';
  if (numeric < 10) return `${numeric.toFixed(3)} ms`;
  if (numeric < 100) return `${numeric.toFixed(2)} ms`;
  return `${Math.round(numeric)} ms`;
}

export function sentenceCase(value: unknown): string {
  const text = displayLabel(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function documentLabel(value: string): string {
  return value.replace(/^paper-/i, 'Paper ');
}

export function polishGeneratedText(value: string): string {
  return value
    .replace(/\b([a-z]+(?:_[a-z]+)+)\b/g, (match) => displayLabel(match))
    .replace(/\[(paper-\d+);\s*confidence=([0-9.]+)\]/gi, (_match, documentId: string, confidence: string) => {
      const confidencePercent = Number(confidence);
      const displayConfidence = Number.isFinite(confidencePercent)
        ? `${Math.round(confidencePercent * 100)}% confidence`
        : 'confidence unavailable';
      return `[${documentLabel(documentId)}; ${displayConfidence}]`;
    })
    .replace(/complexity=([0-9.]+)/gi, (_match, score: string) => `complexity ${Number(score).toFixed(2)}`)
    .replace(/hops=(\d+)/gi, (_match, hops: string) => `${hops} hops`);
}
