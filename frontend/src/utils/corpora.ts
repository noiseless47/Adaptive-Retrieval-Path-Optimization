import { CorpusInfo } from '../types/api';
import { displayLabel } from './format';

export const DEFAULT_CORPUS_PATH = 'data/arpo-openalex-corpus.jsonl';
export const DEFAULT_QUERY_SET_PATH = 'data/arpo-openalex-queries.jsonl';

export function visibleProductionCorpora(corpora: CorpusInfo[]): CorpusInfo[] {
  const uploaded = corpora.filter((corpus) => corpus.type === 'uploaded');
  return uploaded.length > 0 ? uploaded : corpora;
}

export function corpusDisplayName(corpus: CorpusInfo): string {
  const stem = corpus.id.replace(/\.jsonl$/i, '');

  if (stem === 'arpo-openalex-corpus') {
    return 'OpenAlex Research Corpus';
  }

  if (stem === 'corpus' && corpus.type === 'example') {
    return 'Demo Corpus';
  }

  return displayLabel(stem);
}

export function corpusSupportingText(corpus: CorpusInfo): string {
  const documentCount = typeof corpus.documents === 'number' ? `${corpus.documents.toLocaleString()} docs` : undefined;
  const source = corpus.type === 'uploaded' ? 'Production Corpus' : 'Demo Corpus';
  return [source, documentCount].filter(Boolean).join(' - ');
}

export function corpusOptions(corpora: CorpusInfo[]) {
  const visibleCorpora = visibleProductionCorpora(corpora);
  if (!visibleCorpora.length) {
    return [{ label: 'OpenAlex Research Corpus', value: DEFAULT_CORPUS_PATH }];
  }

  return visibleCorpora.map((corpus) => ({
    label: corpusDisplayName(corpus),
    value: corpus.path,
  }));
}

export function preferredCorpusPath(corpora: CorpusInfo[], currentPath?: string): string {
  const options = corpusOptions(corpora);
  if (currentPath && options.some((option) => option.value === currentPath)) {
    return currentPath;
  }

  return options[0]?.value ?? DEFAULT_CORPUS_PATH;
}
