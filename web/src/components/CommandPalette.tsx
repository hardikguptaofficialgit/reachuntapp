import { useEffect, useMemo, useState } from "react";
import { toggleTheme } from "../theme";
import type { AppTab } from "./TabNav";

export type PaletteAction = {
  id: string;
  label: string;
  hint?: string;
  run: () => void;
};

type Props = {
  open: boolean;
  onClose: () => void;
  actions: PaletteAction[];
};

export function CommandPalette({ open, onClose, actions }: Props) {
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return actions;
    return actions.filter(
      (a) => a.label.toLowerCase().includes(s) || a.hint?.toLowerCase().includes(s)
    );
  }, [actions, q]);

  if (!open) return null;

  return (
    <div className="palette-backdrop" onClick={onClose} role="presentation">
      <div
        className="palette"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <input
          className="palette__input"
          autoFocus
          placeholder="Type a command…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul className="palette__list">
          {filtered.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                className="palette__item"
                onClick={() => {
                  a.run();
                  onClose();
                }}
              >
                <span>{a.label}</span>
                {a.hint && <span className="palette__hint">{a.hint}</span>}
              </button>
            </li>
          ))}
          {!filtered.length && <li className="palette__empty">No matches</li>}
        </ul>
      </div>
    </div>
  );
}

export function buildDefaultActions(opts: {
  setTab: (t: AppTab) => void;
  focusSearch: () => void;
  runLookup: () => void;
  exportHistory: () => void;
  toggleNotify: () => void;
  notifyOn: boolean;
  toggleFocus: () => void;
  focusOn: boolean;
  showShortcuts: () => void;
  goToBuild: () => void;
  copyLastEmail: () => void;
  canCopyEmail: boolean;
}): PaletteAction[] {
  return [
    { id: "discover", label: "Go to Discover", hint: "⌘1", run: () => opts.setTab("discover") },
    { id: "build", label: "Build impress project", hint: "⌘2 · Lovable / v0", run: opts.goToBuild },
    { id: "bulk", label: "Go to Bulk", hint: "⌘3", run: () => opts.setTab("bulk") },
    { id: "library", label: "Go to Library", hint: "⌘4", run: () => opts.setTab("library") },
    ...(opts.canCopyEmail
      ? [{ id: "copy-email", label: "Copy last email", hint: "Latest result", run: opts.copyLastEmail }]
      : []),
    { id: "focus", label: "Focus search", hint: "Tab discover", run: opts.focusSearch },
    { id: "run", label: "Run lookup", hint: "⌘↵", run: opts.runLookup },
    {
      id: "zen",
      label: opts.focusOn ? "Show dashboard" : "Focus mode",
      hint: "Hide stats",
      run: opts.toggleFocus,
    },
    {
      id: "theme",
      label: "Toggle theme",
      run: () => {
        toggleTheme();
      },
    },
    {
      id: "notify",
      label: opts.notifyOn ? "Disable notifications" : "Enable notifications",
      run: opts.toggleNotify,
    },
    { id: "shortcuts", label: "Keyboard shortcuts", hint: "?", run: opts.showShortcuts },
    { id: "export", label: "Export history CSV", run: opts.exportHistory },
  ];
}
