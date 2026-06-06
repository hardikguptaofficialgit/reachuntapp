import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  exchangeLinkitToken,
  fetchMe,
  logout as apiLogout,
  type UserProfile,
} from "../api";
import { trackEvent } from "../lib/analytics";
import {
  buildLinkitSignInUrl,
  clearLinkitAuthFromUrl,
  readLinkitAuthFromUrl,
} from "../lib/linkitAuth";

type AuthState = {
  profile: UserProfile | null;
  loading: boolean;
  authError: string | null;
  clearAuthError: () => void;
  refresh: () => Promise<void>;
  loginWithLinkit: () => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await fetchMe();
      if (!me?.user?.email) {
        setProfile(null);
        return;
      }
      const email = me.user.email;
      const fallbackName = email.split("@")[0];
      setProfile({
        ...me,
        account: me.account ?? {
          display_name: fallbackName,
          email,
          avatar_style: "notionists",
          avatar_seed: fallbackName,
          created_at: "",
          linkit_uid: "",
        },
        stats: me.stats ?? { lookups: 0, verified: 0, hit_rate: 0, today: 0 },
        suggestions: me.suggestions ?? [],
        avatar_styles: me.avatar_styles ?? [],
      });
      setAuthError(null);
    } catch {
      setProfile(null);
    }
  }, []);

  const exchangeFromUrl = useCallback(async () => {
    const { token, error } = readLinkitAuthFromUrl();
    if (error) {
      setAuthError(error);
      clearLinkitAuthFromUrl();
      return;
    }
    if (!token) return;

    try {
      setAuthError(null);
      await exchangeLinkitToken(token);
      clearLinkitAuthFromUrl();
      await refresh();
      trackEvent("sign_in", { provider: "linkit" });
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Linkit sign-in failed.");
      clearLinkitAuthFromUrl();
    }
  }, [refresh]);

  useEffect(() => {
    let cancelled = false;
    const watchdog = window.setTimeout(() => {
      if (!cancelled) setLoading(false);
    }, 6000);

    (async () => {
      setLoading(true);
      try {
        await exchangeFromUrl();
        await refresh();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      window.clearTimeout(watchdog);
    };
  }, [exchangeFromUrl, refresh]);

  const loginWithLinkit = useCallback(() => {
    window.location.assign(buildLinkitSignInUrl());
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setProfile(null);
  }, []);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  const value = useMemo(
    () => ({
      profile,
      loading,
      authError,
      clearAuthError,
      refresh,
      loginWithLinkit,
      logout,
    }),
    [profile, loading, authError, clearAuthError, refresh, loginWithLinkit, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth requires AuthProvider");
  return ctx;
}
