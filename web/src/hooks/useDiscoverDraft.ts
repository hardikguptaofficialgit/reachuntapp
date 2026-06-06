import { useEffect, useRef } from "react";
import type { SearchMode } from "../components/SearchForm";

export type DiscoverDraft = {
  mode: SearchMode;
  query: string;
  name: string;
  domain: string;
};

const KEY = "fe-discover-draft";

export function loadDiscoverDraft(): Partial<DiscoverDraft> | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Partial<DiscoverDraft>;
  } catch {
    return null;
  }
}

export function saveDiscoverDraft(draft: DiscoverDraft) {
  try {
    localStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    /* ignore quota */
  }
}

/** Debounced persist for discover form fields. */
export function useDiscoverDraftSync(draft: DiscoverDraft) {
  const timer = useRef(0);

  useEffect(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => saveDiscoverDraft(draft), 400);
    return () => window.clearTimeout(timer.current);
  }, [draft.mode, draft.query, draft.name, draft.domain]);
}
