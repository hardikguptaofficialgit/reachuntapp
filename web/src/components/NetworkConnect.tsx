import { useCallback, useEffect, useState } from "react";
import {
  connectNetwork,
  fetchNetwork,
  refreshNetwork,
  type NetworkState,
  type NetworkStatus,
} from "../api";

type Props = {
  onReadyChange: (ready: boolean) => void;
};

function networkReady(s: NetworkStatus): boolean {
  return s.can_lookup ?? s.state === "connected";
}

export function NetworkConnect({ onReadyChange }: Props) {
  const [status, setStatus] = useState<NetworkStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const [busy, setBusy] = useState(false);

  const apply = useCallback(
    (s: NetworkStatus) => {
      setStatus(s);
      onReadyChange(networkReady(s));
    },
    [onReadyChange]
  );

  const load = useCallback(async () => {
    const s = await fetchNetwork();
    apply(s);
    if (s.state === "connecting") setPolling(true);
  }, [apply]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [load]);

  useEffect(() => {
    if (!polling) return;
    const tick = async () => {
      const s = await refreshNetwork();
      apply(s);
      if (s.state === "connected") setPolling(false);
    };
    void tick();
    const id = window.setInterval(() => void tick(), 1500);
    return () => window.clearInterval(id);
  }, [polling, apply]);

  const state: NetworkState = status?.state ?? "disconnected";

  if (state === "connected") {
    return (
      <div className="net net--ok" role="status">
        <div className="net__left">
          <span className="net__dot net__dot--on" />
          <span className="net__text">Network active</span>
        </div>
      </div>
    );
  }

  const short =
    state === "connecting"
      ? polling
        ? "Checking sign-in…"
        : "Sign in in the Brave window opened by Connect"
      : "Connect to unlock discovery";

  return (
    <div className="net" role="status">
      <div className="net__left">
        <span className={`net__dot${state === "connecting" ? " net__dot--live" : ""}`} />
        <span className="net__text">{short}</span>
      </div>
      <div className="net__actions">
        {state !== "connecting" ? (
          <button
            type="button"
            className="glass-btn glass-btn--sm icon-btn--text"
            onClick={async () => {
              setBusy(true);
              try {
                const s = await connectNetwork();
                apply(s);
                setPolling(true);
                const refreshed = await refreshNetwork();
                apply(refreshed);
                if (refreshed.state === "connected") setPolling(false);
              } finally {
                setBusy(false);
              }
            }}
            disabled={busy}
          >
            Connect
          </button>
        ) : (
          <button
            type="button"
            className="glass-btn glass-btn--sm icon-btn--text"
            onClick={async () => {
              setPolling(true);
              const s = await refreshNetwork();
              apply(s);
              if (s.state === "connected") setPolling(false);
            }}
          >
            Check now
          </button>
        )}
      </div>
    </div>
  );
}
