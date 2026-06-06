export type AppTab = "discover" | "bulk" | "library" | "build";

type Props = {
  tab: AppTab;
  onChange: (tab: AppTab) => void;
};

const TABS: { id: AppTab; label: string; short: string }[] = [
  { id: "discover", label: "Discover", short: "Find" },
  { id: "build", label: "Build", short: "Build" },
  { id: "bulk", label: "Bulk", short: "Bulk" },
  { id: "library", label: "Library", short: "Saved" },
];

export function TabNav({ tab, onChange }: Props) {
  return (
    <nav className="tabs" aria-label="App sections">
      <div className="tabs__track" role="tablist">
        {TABS.map((t) => {
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={on}
              aria-controls={`panel-${t.id}`}
              tabIndex={on ? 0 : -1}
              className={`tabs__btn${on ? " tabs__btn--on" : ""}`}
              onClick={() => onChange(t.id)}
            >
              <span className="tabs__label">{t.label}</span>
              <span className="tabs__label tabs__label--short">{t.short}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
