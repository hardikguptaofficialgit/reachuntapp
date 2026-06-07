type Props = {
  busy: boolean;
  tab: string;
  lastQuery?: string | null;
};

export function WorkflowBar({ busy, tab, lastQuery }: Props) {
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

  return null;
}

function shortQuery(q: string) {
  const s = q.trim();
  if (s.length <= 28) return s;
  return `${s.slice(0, 26)}...`;
}
