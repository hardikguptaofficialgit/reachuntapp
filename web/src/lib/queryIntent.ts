import type { SearchMode } from "../components/SearchForm";

/** Canonical lookup string sent to the API (parse + jobs). */
export function buildLookupQuery(
  mode: SearchMode,
  value: string,
  name: string,
  domain: string,
): string {
  const v = value.trim();
  const n = name.trim();
  const d = domain.trim().replace(/^https?:\/\//, "").replace(/^www\./, "");

  if (mode === "quick") return v;
  if (n && d) return `${n} — ${d}`;
  if (d) return d;
  if (n) return n;
  return "";
}

/** @deprecated Use buildLookupQuery */
export const buildPreviewQuery = buildLookupQuery;
