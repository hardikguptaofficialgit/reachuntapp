/** Linkit SSO — same redirect pattern as linkit-studio */

const SOURCE = "founder-email";

export function resolveLinkitAppUrl(): string {
  const env = import.meta.env.VITE_LINKIT_APP_URL?.trim();
  if (env) return env.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8080";
    }
  }

  return "https://linkitapp.in";
}

/** Return URL without auth tokens (safe to pass as redirect). */
export function buildFounderReturnUrl(): string {
  if (typeof window === "undefined") return "/";

  const url = new URL(window.location.href);
  url.searchParams.delete("authToken");
  url.searchParams.delete("authError");

  const hash = new URLSearchParams(url.hash.replace(/^#/, ""));
  hash.delete("authToken");
  hash.delete("authError");
  url.hash = hash.toString() ? `#${hash.toString()}` : "";

  return url.toString();
}

export function buildLinkitSignInUrl(): string {
  const main = resolveLinkitAppUrl();
  const returnUrl = encodeURIComponent(buildFounderReturnUrl());
  return `${main}/signin?redirect=${returnUrl}&source=${SOURCE}`;
}

export function buildLinkitSignUpUrl(): string {
  const main = resolveLinkitAppUrl();
  const returnUrl = encodeURIComponent(buildFounderReturnUrl());
  return `${main}/signup?redirect=${returnUrl}&source=${SOURCE}`;
}

export function readLinkitAuthFromUrl(): { token: string | null; error: string | null } {
  if (typeof window === "undefined") {
    return { token: null, error: null };
  }

  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  const token = hashParams.get("authToken") || urlParams.get("authToken");
  const error = hashParams.get("authError") || urlParams.get("authError");

  return {
    token: token?.trim() || null,
    error: error ? decodeURIComponent(error) : null,
  };
}

export function clearLinkitAuthFromUrl(): void {
  if (typeof window === "undefined") return;

  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  urlParams.delete("authToken");
  urlParams.delete("authError");
  hashParams.delete("authToken");
  hashParams.delete("authError");

  const hashString = hashParams.toString();
  const newUrl =
    window.location.pathname +
    (urlParams.toString() ? `?${urlParams.toString()}` : "") +
    (hashString ? `#${hashString}` : "");

  window.history.replaceState({}, "", newUrl);
}
