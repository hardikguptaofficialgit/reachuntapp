type Props = {
  items: string[];
  onPick: (query: string) => void;
  onClear?: () => void;
};

export function RecentStrip({ items, onPick, onClear }: Props) {
  if (!items.length) return null;

  return (
    <div className="recent-strip" aria-label="Recent lookups">
      <span className="recent-strip__label">Recent</span>
      <div className="recent-strip__chips">
        {items.map((q) => (
          <button
            key={q}
            type="button"
            className="recent-strip__chip"
            onClick={() => onPick(q)}
            title={q}
          >
            {q.split("—")[0]?.trim() || q}
          </button>
        ))}
      </div>
      {onClear && (
        <button type="button" className="recent-strip__clear" onClick={onClear}>
          Clear
        </button>
      )}
    </div>
  );
}
