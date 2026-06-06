import { useEffect, useState } from "react";

export function useRotatingText(lines: string[], ms = 3200, active = true): string {
  return useRotatingTextCycle(lines, ms, active).text;
}

/** Index + text so UI can key animations on each phrase change. */
export function useRotatingTextCycle(
  lines: string[],
  ms = 3200,
  active = true,
): { text: string; index: number } {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active || lines.length < 2) return;
    const id = window.setInterval(() => setIndex((n) => (n + 1) % lines.length), ms);
    return () => clearInterval(id);
  }, [active, lines.length, ms]);

  const safeIndex = lines.length ? index % lines.length : 0;
  return { text: lines[safeIndex] ?? lines[0] ?? "", index: safeIndex };
}
