export interface SearchRecord {
  id: string;
  title: string;
  subtitle?: string;
  keywords?: string[];
}

export interface SearchResult extends SearchRecord {
  score: number;
}

export function rankSearch(records: SearchRecord[], query: string): SearchResult[] {
  const terms = query
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  if (terms.length === 0) {
    return records.map((record) => ({ ...record, score: 1 }));
  }

  return records
    .map((record) => {
      const haystack = [record.title, record.subtitle, ...(record.keywords ?? [])].join(" ").toLowerCase();
      const score = terms.reduce((sum, term) => sum + (haystack.includes(term) ? 1 : 0), 0);
      return { ...record, score };
    })
    .filter((record) => record.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title));
}
