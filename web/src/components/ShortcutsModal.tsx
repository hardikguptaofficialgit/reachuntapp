type Props = {
  open: boolean;
  onClose: () => void;
};

const ROWS: [string, string][] = [
  ["⌘ K", "Command palette"],
  ["⌘ ↵", "Run lookup (Discover)"],
  ["⌘ 1–4", "Switch tabs"],
  ["?", "Shortcuts"],
  ["Esc", "Close palette / modal"],
];

export function ShortcutsModal({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="palette-backdrop" onClick={onClose} role="presentation">
      <div
        className="palette palette--sm"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Keyboard shortcuts"
      >
        <p className="palette__title">Shortcuts</p>
        <ul className="shortcuts">
          {ROWS.map(([key, label]) => (
            <li key={key} className="shortcuts__row">
              <kbd>{key}</kbd>
              <span>{label}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
