/**
 * Optional web analytics — Umami, Plausible, or GA4 via env (see WEB.md).
 * Never sends emails, names, or full lookup queries.
 */

type AnalyticsProps = Record<string, string | number | boolean | undefined>;

type UmamiTrack = {
  (event?: string | ((props: Record<string, unknown>) => Record<string, unknown>)): void;
  (event: string, data?: AnalyticsProps): void;
};

declare global {
  interface Window {
    umami?: UmamiTrack;
    plausible?: (event: string, options?: { props?: AnalyticsProps; u?: string }) => void;
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

let provider: "umami" | "plausible" | "ga4" | "none" = "none";
let gaId = "";

function isEnabled(): boolean {
  if (import.meta.env.VITE_ANALYTICS_DISABLED === "true") return false;
  return provider !== "none";
}

function whenUmamiReady(fn: () => void, attempts = 40): void {
  if (window.umami) {
    fn();
    return;
  }
  if (attempts <= 0) return;
  window.setTimeout(() => whenUmamiReady(fn, attempts - 1), 100);
}

/** Load script once at app startup. */
export function initAnalytics(): void {
  if (import.meta.env.VITE_ANALYTICS_DISABLED === "true") return;

  const umamiId = (import.meta.env.VITE_UMAMI_WEBSITE_ID ?? "").trim();
  const umamiSrc = (
    import.meta.env.VITE_UMAMI_SCRIPT_URL ?? "https://cloud.umami.is/script.js"
  ).trim();

  if (umamiId) {
    provider = "umami";
    const script = document.createElement("script");
    script.defer = true;
    script.src = umamiSrc;
    script.dataset.websiteId = umamiId;
    document.head.appendChild(script);
    return;
  }

  gaId = (import.meta.env.VITE_GA_MEASUREMENT_ID ?? "").trim();
  const plausibleDomain = (import.meta.env.VITE_PLAUSIBLE_DOMAIN ?? "").trim();

  if (gaId) {
    provider = "ga4";
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag(...args: unknown[]) {
      window.dataLayer?.push(args);
    };
    window.gtag("js", new Date());
    window.gtag("config", gaId, { send_page_view: false });

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gaId)}`;
    document.head.appendChild(script);
    return;
  }

  if (plausibleDomain) {
    provider = "plausible";
    const base =
      (import.meta.env.VITE_PLAUSIBLE_SCRIPT_URL ?? "https://plausible.io/js/script.js").trim();
    const script = document.createElement("script");
    script.defer = true;
    script.dataset.domain = plausibleDomain;
    script.src = base;
    document.head.appendChild(script);
    return;
  }

  provider = "none";
}

/** Initial full page load (call once at startup). */
export function trackPageView(path = "/"): void {
  if (!isEnabled()) return;
  const page = path.startsWith("/") ? path : `/${path}`;
  const url = `${window.location.origin}${page}`;

  if (provider === "umami") {
    whenUmamiReady(() => {
      window.umami?.((props) => ({ ...props, url }));
    });
    return;
  }

  if (provider === "plausible" && window.plausible) {
    window.plausible("pageview", { u: url });
    return;
  }

  if (provider === "ga4" && window.gtag) {
    window.gtag("event", "page_view", {
      page_path: page,
      page_title: document.title,
    });
  }
}

/** SPA tab / screen change (discover, bulk, auth, etc.). */
export function trackScreen(screen: string): void {
  const page = `/${screen}`;
  if (provider === "umami") {
    whenUmamiReady(() => {
      window.umami?.((props) => ({
        ...props,
        url: `${window.location.origin}${page}`,
      }));
    });
    return;
  }
  trackEvent("screen_view", { screen });
}

/** Custom product events (no PII). */
export function trackEvent(name: string, props?: AnalyticsProps): void {
  if (!isEnabled()) return;
  const safe = props ? scrubProps(props) : undefined;

  if (provider === "umami") {
    whenUmamiReady(() => {
      if (safe && Object.keys(safe).length > 0) {
        window.umami?.(name, safe);
      } else {
        window.umami?.(name);
      }
    });
    return;
  }

  if (provider === "plausible" && window.plausible) {
    window.plausible(name, safe ? { props: safe } : undefined);
    return;
  }

  if (provider === "ga4" && window.gtag) {
    window.gtag("event", name, safe ?? {});
  }
}

function scrubProps(props: AnalyticsProps): AnalyticsProps {
  const out: AnalyticsProps = {};
  for (const [k, v] of Object.entries(props)) {
    if (v === undefined) continue;
    const key = k.toLowerCase();
    if (key.includes("email") || key.includes("query") || key.includes("name")) continue;
    out[k] = v;
  }
  return out;
}

export function analyticsProvider(): typeof provider {
  return provider;
}
