import { useEffect, useState } from "react";
import { buildLinkitSignInUrl, buildLinkitSignUpUrl } from "../lib/linkitAuth";
import { ThemeToggle } from "./ThemeToggle";
import { Logo } from "./Logo";
import { LinkitIcon } from "./icons/LinkitIcon";
import { useAuth } from "../context/AuthContext";
import { AmbientLayer } from "./AmbientLayer";
import { useEnterAnimation } from "../hooks/useEnterAnimation";

export function AuthScreen() {
  const { loginWithLinkit, authError, clearAuthError } = useAuth();
  const entered = useEnterAnimation(true);
  const [busy, setBusy] = useState(false);
  const flow = (i: number) => ({ "--flow-i": i }) as React.CSSProperties;

  const handleLinkit = () => {
    clearAuthError();
    setBusy(true);
    try {
      loginWithLinkit();
    } catch {
      setBusy(false);
    }
  };

  const [apiDown, setApiDown] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    const t = window.setTimeout(() => ctrl.abort(), 4000);
    fetch("/api/v1/health", { signal: ctrl.signal })
      .then((r) => setApiDown(!r.ok))
      .catch(() => setApiDown(true))
      .finally(() => window.clearTimeout(t));
    return () => {
      ctrl.abort();
      window.clearTimeout(t);
    };
  }, []);

  const displayError =
    authError ?? (apiDown ? "API not running - start with .\\run-api.ps1 in the project folder." : null);

  return (
    <>
      <AmbientLayer />
      <div className={`shell shell--auth${entered ? " shell--entered" : ""}`}>
        <div className="bar flow-item" style={{ ...flow(0), border: "none", marginBottom: "2rem" }}>
          <Logo size={32} />
          <ThemeToggle />
        </div>

        <h1 className="auth-mark flow-item" style={flow(1)}>
          Reachunt
        </h1>
        <p className="auth-tag flow-item" style={flow(2)}>
          Find anyone&apos;s work email by name and company. Sign in with Linkit.
        </p>

        {displayError && (
          <p className="auth-err flow-item" style={flow(3)} role="alert">
            {displayError}
          </p>
        )}

<button
  type="button"
  className="auth-submit auth-submit--linkit glass-btn glass-btn--primary flow-item"
  style={flow(displayError ? 4 : 3)}
  onClick={handleLinkit}
  disabled={busy}
>
  <img
    src="https://linkitapp.in/v1.png"
    alt="Linkit"
    width={17}
    height={17}
    style={{
      width: 30,
      height: 30,
      objectFit: "contain",
    }}
  />
  {busy ? "Opening Linkit..." : "Continue with Linkit"}
</button>

        <p className="auth-linkit-hint flow-item" style={flow(displayError ? 5 : 4)}>
          You&apos;ll sign in on Linkit, then return here automatically.
        </p>

        <p className="auth-alt auth-alt--block flow-item" style={flow(displayError ? 6 : 5)}>
          Don&apos;t have a Linkit account?{" "}
          <a href={buildLinkitSignUpUrl()} className="auth-alt__link">
            Sign up on Linkit
          </a>
        </p>

        <p className="auth-alt flow-item" style={flow(displayError ? 7 : 6)}>
          <a href={buildLinkitSignInUrl()} target="_blank" rel="noopener noreferrer" className="auth-alt__link">
            Open sign-in in a new tab
          </a>{" "}
          if redirect does not work.
        </p>
      </div>
    </>
  );
}
