import type { Job } from "../api";
import type { AppSettings } from "../hooks/useSettings";
import { useToast } from "../context/ToastContext";
import { BrandIcon } from "./BrandIcon";
import { ComposeMailActions } from "./ComposeMailActions";
import { PipelineProgress, phaseFromJob } from "./PipelineProgress";

type Props = {
  job: Job | null;
  error: string | null;
  busy: boolean;
  onRetry?: () => void;
  onSave?: (query: string, email: string) => void;
  onImpress?: () => void;
  mailSettings?: Pick<AppSettings, "mailSubject" | "mailBody">;
};

export function ResultPanel({
  job,
  error,
  busy,
  onRetry,
  onSave,
  onImpress,
  mailSettings,
}: Props) {
  const { push } = useToast();

  if (busy && !job) {
    return (
      <div className="outcome-slot">
        <PipelineProgress steps={[]} active label="Discovering" />
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="outcome-slot">
        <div className="msg-block msg-block--shake">
          <p className="msg msg--err">{error}</p>
          {onRetry && (
          <button type="button" className="glass-btn glass-btn--sm" onClick={onRetry}>
            Try again
          </button>
          )}
        </div>
      </div>
    );
  }

  if (!job) return null;

  const result = job.result;
  const running = job.status === "queued" || job.status === "running";
  const failed = job.status === "failed";
  const email = result?.email?.trim() ?? "";
  const steps = phaseFromJob(job.phase, result?.steps ?? []);
  const lastStep = steps[steps.length - 1]?.label;

  if (running) {
    return (
      <div className="outcome-slot">
        <PipelineProgress steps={steps} active label={lastStep} progress={job.phase} />
      </div>
    );
  }

  if (failed) {
    return (
      <div className="outcome-slot">
        <div className="msg-block msg-block--shake">
          <p className="msg msg--err">
            {job.error ?? result?.message ?? "Could not complete."}
          </p>
          {onRetry && (
          <button type="button" className="glass-btn glass-btn--sm" onClick={onRetry}>
            Try again
          </button>
          )}
        </div>
      </div>
    );
  }

  if (!result) return null;

  const copyEmail = async () => {
    if (!email) return;
    await navigator.clipboard.writeText(email);
    push("Copied");
  };

  const copyFormatted = async () => {
    if (!email) return;
    const line = `${result.display_name || result.name} <${email}> · ${result.domain}`;
    await navigator.clipboard.writeText(line);
    push("Copied line");
  };

  const displayName = result.display_name || result.name;
  const domain = result.domain?.trim();
  const score = result.validation?.score ?? result.confidence ?? 0;
  const emailBadge =
    result.status === "verified"
      ? "Verified"
      : result.status === "likely"
        ? "Likely"
        : result.status === "risky"
          ? "Risky"
          : "Found";
  const validationSignals = [
    result.validation?.mx_found ? "MX" : null,
    result.validation?.smtp_checked
      ? result.validation?.smtp_valid === true
        ? "SMTP"
        : result.validation?.smtp_valid === false
          ? "SMTP rejected"
          : "SMTP unknown"
      : null,
    result.validation?.catch_all ? "Catch-all" : null,
    result.validation?.free_provider ? "Free provider" : null,
    result.validation?.role_account ? "Role address" : null,
    result.validation?.disposable ? "Disposable" : null,
  ].filter(Boolean) as string[];

  return (
    <div className="outcome-slot">
      <div
        className={`outcome${email ? " outcome--hit" : ""}`}
        aria-live="polite"
      >
        {(displayName || domain) && (
          <header className="outcome__meta">
            {displayName && <span className="outcome__name">{displayName}</span>}
            {domain && (
              <a
                className="outcome__domain"
                href={`https://${domain.replace(/^https?:\/\//, "")}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <BrandIcon domain={domain} size={16} className="outcome__favicon" />
                {domain}
              </a>
            )}
          </header>
        )}

        {email ? (
          <>
            <div className="outcome__hero">
              <p className="outcome__email">{email}</p>
              <div className="outcome__verify">
                <span className={`badge badge--${result.status || "found"}`}>{emailBadge}</span>
                {score > 0 && <span className="score-pill">{score}%</span>}
                {validationSignals.slice(0, 4).map((signal) => (
                  <span key={signal} className="signal-pill">
                    {signal}
                  </span>
                ))}
              </div>
            </div>

            <ComposeMailActions
              email={email}
              name={displayName}
              query={job.query}
              domain={domain}
              settings={mailSettings}
            />

            <nav className="outcome__actions" aria-label="Result actions">
              <div className="outcome__action-group">
                <button type="button" className="glass-btn glass-btn--sm" onClick={() => void copyEmail()}>
                  Copy
                </button>
                <button type="button" className="glass-btn glass-btn--sm" onClick={() => void copyFormatted()}>
                  Copy line
                </button>
                {onSave && (
                  <button
                    type="button"
                    className="glass-btn glass-btn--sm"
                    onClick={() => onSave(job.query, email)}
                  >
                    Save
                  </button>
                )}
              </div>
              <div className="outcome__action-group">
                {result.profile_url && (
                  <a
                    className="glass-btn glass-btn--sm"
                    href={result.profile_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Profile
                  </a>
                )}
                {onRetry && (
                  <button type="button" className="glass-btn glass-btn--sm" onClick={onRetry}>
                    Again
                  </button>
                )}
                {onImpress && domain && (
                  <button type="button" className="glass-btn glass-btn--sm glass-btn--accent" onClick={onImpress}>
                    Build for them
                  </button>
                )}
              </div>
            </nav>
          </>
        ) : (
          <p className="outcome__email outcome__email--empty">{result.message}</p>
        )}
      </div>
    </div>
  );
}
