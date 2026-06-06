/** Bearer token for API when cookies are blocked (cross-origin SPA + API host). */

const KEY = "ae_session_token";

export function getSessionToken(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string): void {
  try {
    localStorage.setItem(KEY, token);
  } catch {
    /* private mode */
  }
}

export function clearSessionToken(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
