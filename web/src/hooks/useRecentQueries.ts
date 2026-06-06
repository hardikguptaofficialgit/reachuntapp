const KEY = "fe-recent-queries";
const MAX = 8;

export function loadRecentQueries(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const list = JSON.parse(raw) as unknown;
    return Array.isArray(list) ? list.filter((x) => typeof x === "string").slice(0, MAX) : [];
  } catch {
    return [];
  }
}

export function pushRecentQuery(query: string) {
  const q = query.trim();
  if (!q) return;
  const prev = loadRecentQueries().filter((x) => x !== q);
  const next = [q, ...prev].slice(0, MAX);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  return next;
}
