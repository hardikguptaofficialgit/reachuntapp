import type { PublicStep } from "../api";

type Props = {
  steps: PublicStep[];
  active?: boolean;
  label?: string;
  progress?: string;
};

const PHASE_PCT: Record<string, number> = {
  queued: 12,
  discovering: 45,
  complete: 100,
  failed: 100,
};

const PHASE_LABEL: Record<string, string> = {
  queued: "Queued",
  discovering: "Discovering",
  complete: "Complete",
  failed: "Failed",
};

export function PipelineProgress({ steps, active, label, progress }: Props) {
  const last = steps[steps.length - 1];
  const pct = active ? (PHASE_PCT[progress ?? "discovering"] ?? 50) : 100;
  const text = active
    ? PHASE_LABEL[progress ?? "discovering"] ?? "Discovering"
    : (label ?? last?.label ?? "Processing");

  return (
    <div className="track-wrap" aria-live="polite">
      <div className="track">
        <div
          className={`track__fill${active ? " track__fill--live" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="track__label">{text}</p>
    </div>
  );
}

export function phaseFromJob(phase: string, steps: PublicStep[]): PublicStep[] {
  if (steps.length) return steps;
  const map: Record<string, PublicStep> = {
    queued: { id: "parsed", label: "Queued" },
    discovering: { id: "discovering", label: "Discovering" },
    complete: { id: "verified", label: "Complete" },
    failed: { id: "invalid", label: "Failed" },
  };
  return map[phase] ? [map[phase]] : [];
}
