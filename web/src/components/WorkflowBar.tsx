type Props = {
  busy: boolean;
  canLookup: boolean;
  tab: string;
  lastQuery?: string | null;
};

export function WorkflowBar({ busy, canLookup, tab, lastQuery }: Props) {
  const needsNet = tab === "discover" || tab === "bulk";

  if (busy) {
    return (
      <div className="workflow-bar workflow-bar--busy" role="status" aria-live="polite">
        <span className="workflow-bar__pulse" aria-hidden />
        <span>
          Lookup running
          {lastQuery ? ` · ${shortQuery(lastQuery)}` : ""}
        </span>
      </div>
    );
  }

  if (needsNet && !canLookup) {
    return (
      <div className="workflow-bar workflow-bar--warn" role="status">
        Connect your network above to run lookups
      </div>
    );
  }

  return null;
}

function shortQuery(q: string) {
  const s = q.trim();
  if (s.length <= 28) return s;
  return `${s.slice(0, 26)}…`;
}
