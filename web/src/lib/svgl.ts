/**
 * Brand icons via SVGL (https://svgl.app) with Google favicon fallback.
 * Routes verified from https://api.svgl.app
 */

import type { Theme } from "../theme";

export type SvglRoute = string | { light: string; dark: string };

export function pickSvglRoute(route: SvglRoute, theme: Theme): string {
  if (typeof route === "string") return route;
  return theme === "dark" ? route.dark : route.light;
}

/** AI builders — Build tab */
export const BUILD_TOOL_SVGL: Record<string, SvglRoute> = {
  lovable: "https://svgl.app/library/lovable.svg",
  v0: {
    light: "https://svgl.app/library/v0_light.svg",
    dark: "https://svgl.app/library/v0_dark.svg",
  },
  bolt: {
    light: "https://svgl.app/library/bolt-new.svg",
    dark: "https://svgl.app/library/bolt-new_dark.svg",
  },
  replit: "https://svgl.app/library/replit.svg",
  cursor: {
    light: "https://svgl.app/library/cursor_light.svg",
    dark: "https://svgl.app/library/cursor_dark.svg",
  },
};

/** Company domains used in lookups / examples */
export const DOMAIN_SVGL: Record<string, SvglRoute> = {
  "notion.so": "https://svgl.app/library/notion.svg",
  "stripe.com": "https://svgl.app/library/stripe.svg",
  "linear.app": "https://svgl.app/library/linear.svg",
  "vercel.com": {
    light: "https://svgl.app/library/vercel.svg",
    dark: "https://svgl.app/library/vercel_dark.svg",
  },
  "figma.com": "https://svgl.app/library/figma.svg",
  "openai.com": {
    light: "https://svgl.app/library/openai.svg",
    dark: "https://svgl.app/library/openai_dark.svg",
  },
  "anthropic.com": {
    light: "https://svgl.app/library/anthropic_black.svg",
    dark: "https://svgl.app/library/anthropic_white.svg",
  },
};

const DOMAIN_ALIASES: Record<string, string> = {
  notion: "notion.so",
  stripe: "stripe.com",
  linear: "linear.app",
  vercel: "vercel.com",
  figma: "figma.com",
  openai: "openai.com",
  anthropic: "anthropic.com",
  linkit: "linkitapp.in",
  linkitapp: "linkitapp.in",
};

function normalizeDomain(domain: string): string {
  return domain
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .split("/")[0]
    .replace(/^www\./, "");
}

export function svglRouteForDomain(domain: string): SvglRoute | undefined {
  const d = normalizeDomain(domain);
  if (!d) return undefined;
  if (DOMAIN_SVGL[d]) return DOMAIN_SVGL[d];
  const base = d.split(".")[0];
  const alias = DOMAIN_ALIASES[base];
  if (alias && DOMAIN_SVGL[alias]) return DOMAIN_SVGL[alias];
  return undefined;
}

export function brandIconUrl(opts: {
  domain?: string;
  toolId?: string;
  theme: Theme;
}): string | null {
  if (opts.toolId && BUILD_TOOL_SVGL[opts.toolId]) {
    return pickSvglRoute(BUILD_TOOL_SVGL[opts.toolId], opts.theme);
  }
  if (opts.domain) {
    const route = svglRouteForDomain(opts.domain);
    if (route) return pickSvglRoute(route, opts.theme);
  }
  return null;
}

const searchCache = new Map<string, string | null>();

/** Optional: resolve unknown brands via SVGL search API (cached per session). */
export async function searchSvglIcon(query: string, theme: Theme): Promise<string | null> {
  const key = `${query.trim().toLowerCase()}|${theme}`;
  if (searchCache.has(key)) return searchCache.get(key) ?? null;

  try {
    const res = await fetch(
      `https://api.svgl.app?search=${encodeURIComponent(query.trim())}`,
    );
    if (!res.ok) {
      searchCache.set(key, null);
      return null;
    }
    const data = (await res.json()) as Array<{ route?: SvglRoute }>;
    const route = data[0]?.route;
    const url = route ? pickSvglRoute(route, theme) : null;
    searchCache.set(key, url);
    return url;
  } catch {
    searchCache.set(key, null);
    return null;
  }
}
