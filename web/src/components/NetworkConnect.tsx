import { useCallback, useEffect, useState } from "react";
import { fetchNetwork, type NetworkStatus } from "../api";

type Props = {
  onReadyChange: (ready: boolean) => void;
};

function networkReady(s: NetworkStatus): boolean {
  return s.can_lookup ?? s.state === "connected";
}

export function NetworkConnect({ onReadyChange }: Props) {
  const [status, setStatus] = useState<NetworkStatus | null>(null);

  const apply = useCallback(
    (s: NetworkStatus) => {
      setStatus(s);
      onReadyChange(networkReady(s));
    },
    [onReadyChange]
  );

  const load = useCallback(async () => {
    try {
      apply(await fetchNetwork());
    } catch {
      setStatus({
        state: "disconnected",
        message: "Discovery is getting ready.",
        can_lookup: false,
      });
      onReadyChange(false);
    }
  }, [apply, onReadyChange]);

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

  const ready = status ? networkReady(status) : false;

  return (
    <div className={`net${ready ? " net--ok" : ""}`} role="status">
      <div className="net__left">
        <span className={`net__dot${ready ? " net__dot--on" : ""}`} />
        <span className="net__text">
          {ready ? status?.message || "Discovery ready." : status?.message || "Discovery is getting ready."}
        </span>
      </div>
    </div>
  );
}
