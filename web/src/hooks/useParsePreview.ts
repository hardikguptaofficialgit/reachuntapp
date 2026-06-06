import { useEffect, useState } from "react";
import { parseQueryPreview, type ParseResult } from "../api";
import { buildLookupQuery } from "../lib/queryIntent";
import type { SearchMode } from "../components/SearchForm";

export function useParsePreview(
  mode: SearchMode,
  value: string,
  name: string,
  domain: string,
  delayMs = 280,
) {
  const [preview, setPreview] = useState<ParseResult | null>(null);
  const query = buildLookupQuery(mode, value, name, domain);

  useEffect(() => {
    if (!query.trim()) {
      setPreview(null);
      return;
    }

    const timer = window.setTimeout(() => {
      void parseQueryPreview(query).then(setPreview);
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [query, delayMs]);

  return { preview, previewQuery: query };
}
