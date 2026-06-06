export const PLACEHOLDER_LINES = [
  "Name — domain.com",
  "Company name or domain",
  "Try: Notion or stripe.com",
  "Try: Hardik Gupta — linkitapp.in",
];

export function pick<T>(arr: T[], seed = 0): T {
  return arr[Math.abs(seed) % arr.length];
}

export function rotatePlaceholder(tick: number): string {
  return pick(PLACEHOLDER_LINES, tick);
}
