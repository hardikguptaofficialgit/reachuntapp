export const PLACEHOLDER_LINES = [
  "domain.com",
  "Company name or domain",
  "Try: Notion or stripe.com",
  "Try: figma.com or openai.com",
];

export function pick<T>(arr: T[], seed = 0): T {
  return arr[Math.abs(seed) % arr.length];
}

export function rotatePlaceholder(tick: number): string {
  return pick(PLACEHOLDER_LINES, tick);
}

