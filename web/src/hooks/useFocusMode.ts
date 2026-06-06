import { useCallback, useState } from "react";

const KEY = "fe-focus";

export function useFocusMode() {
  const [focus, setFocus] = useState(() => localStorage.getItem(KEY) === "1");

  const toggle = useCallback(() => {
    setFocus((prev) => {
      const next = !prev;
      localStorage.setItem(KEY, next ? "1" : "0");
      return next;
    });
  }, []);

  return { focus, toggle };
}
