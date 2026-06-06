type Props = {
  busy: boolean;
  canLookup: boolean;
  tab: string;
  lastQuery?: string | null;
};

export function WorkflowBar({ busy, canLookup, tab, lastQuery }: Props) {
  const needsDiscovery = tab === "discover" || tab === "bulk";

  if (busy) {
    return (
      <div className="workflow-bar workflow-bar--busy" role="status" aria-live="polite">
        <span className="workflow-bar__pulse" aria-hidden />
        <span>
          Lookup running
          {lastQuery ? ` - ${shortQuery(lastQuery)}` : ""}
        </span>
      </div>
    );
  }

  if (needsDiscovery && !canLookup) {
    return (
      <div className="workflow-bar workflow-bar--warn" role="status">
        Discovery is getting ready
      </div>
    );
  }

  return null;
}

function shortQuery(q: string) {
  const s = q.trim();
  if (s.length <= 28) return s;
  return `${s.slice(0, 26)}...`;
}
