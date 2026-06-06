import { useEffect, useState } from "react";

/** Enables entrance CSS after first paint so flow-in can run. */
export function useEnterAnimation(active = true): boolean {
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    if (!active) {
      setEntered(false);
      return;
    }
    let outer = 0;
    let inner = 0;
    outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => setEntered(true));
    });
    return () => {
      cancelAnimationFrame(outer);
      cancelAnimationFrame(inner);
    };
  }, [active]);

  return entered;
}
