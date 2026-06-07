import type { Job } from "../../api";
import { RecentStrip } from "../../components/RecentStrip";
import { ResultPanel } from "../../components/ResultPanel";
import { SearchForm, type SearchMode } from "../../components/SearchForm";
import { SettingsStrip } from "../../components/SettingsStrip";
import type { AppSettings } from "../../hooks/useSettings";

type FlowStyle = React.CSSProperties;

type Props = {
  flow: (i: number) => FlowStyle;
  searchRef: React.RefObject<HTMLInputElement | null>;
  recentQueries: string[];
  onRecentPick: (q: string) => void;
  onRecentClear: () => void;
  query: string;
  name: string;
  domain: string;
  mode: SearchMode;
  onModeChange: (m: SearchMode) => void;
  onQueryChange: (v: string) => void;
  onNameChange: (v: string) => void;
  onDomainChange: (v: string) => void;
  onSubmit: () => void;
  busy: boolean;
  suggestions: string[];
  onMultiPaste: (text: string) => void;
  job: Job | null;
  error: string | null;
  settings: AppSettings;
  onSettingsChange: (patch: Partial<AppSettings>) => void;
  onRetry: () => void;
  onSaveFavorite: (q: string, email: string) => void;
  onImpress: () => void;
  showSettings: boolean;
};

export function DiscoverTab({
  flow,
  searchRef,
  recentQueries,
  onRecentPick,
  onRecentClear,
  query,
  name,
  domain,
  mode,
  onModeChange,
  onQueryChange,
  onNameChange,
  onDomainChange,
  onSubmit,
  busy,
  suggestions,
  onMultiPaste,
  job,
  error,
  settings,
  onSettingsChange,
  onRetry,
  onSaveFavorite,
  onImpress,
  showSettings,
}: Props) {
  const flowLine = (i: number): FlowStyle => ({
    ...flow(i),
    "--flow-base": "0s",
  } as FlowStyle);

  return (
    <div
      id="panel-discover"
      role="tabpanel"
      aria-labelledby="tab-discover"
      className="tab-panel discover"
      style={flow(6)}
    >
      <div className="flow-line" style={flowLine(0)}>
        <RecentStrip items={recentQueries} onPick={onRecentPick} onClear={onRecentClear} />
      </div>
      <div className="flow-line" style={flowLine(1)}>
        <SearchForm
          inputRef={searchRef}
          value={query}
          name={name}
          domain={domain}
          mode={mode}
          onModeChange={onModeChange}
          onChange={onQueryChange}
          onNameChange={onNameChange}
          onDomainChange={onDomainChange}
          onSubmit={onSubmit}
          busy={busy}
          suggestions={suggestions}
          onMultiPaste={onMultiPaste}
        />
      </div>
      <div className="flow-line" style={flowLine(2)}>
        <ResultPanel
          job={job}
          error={error}
          busy={busy}
          mailSettings={settings}
          onRetry={onRetry}
          onSave={onSaveFavorite}
          onImpress={onImpress}
        />
      </div>
      {showSettings && (
        <div className="flow-line" style={flowLine(3)}>
          <SettingsStrip settings={settings} onChange={onSettingsChange} />
        </div>
      )}
    </div>
  );
}
