import { useEffect, useState } from "react";
import { checkHistoryQuery } from "../api";

export function useDuplicateCheck(query: string, delayMs = 400) {
  const [duplicate, setDuplicate] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setDuplicate(false);
      return;
    }
    const t = window.setTimeout(() => {
      void checkHistoryQuery(q).then(setDuplicate);
    }, delayMs);
    return () => window.clearTimeout(t);
  }, [query, delayMs]);

  return duplicate;
}
