import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import {
  addFavorite,
  fetchActivity,
  fetchHistory,
  type ActivityDay,
  type BuildContext,
  type Job,
} from "./api";
import { AmbientLayer } from "./components/AmbientLayer";
import { AuthScreen } from "./components/AuthScreen";
import { HeroTitle } from "./components/HeroTitle";
import { ActivityChart } from "./components/ActivityChart";
import { BulkPanel } from "./components/BulkPanel";
import {
  buildDefaultActions,
  CommandPalette,
} from "./components/CommandPalette";
import { InsightsStrip } from "./components/InsightsStrip";
import { LibraryPanel } from "./components/LibraryPanel";
import { NetworkConnect } from "./components/NetworkConnect";
import type { SearchMode } from "./components/SearchForm";
import { AccountSettingsModal } from "./components/AccountSettingsModal";
import { ShellBar } from "./components/ShellBar";
import { BuildStudio } from "./components/BuildStudio";
import { ShortcutsModal } from "./components/ShortcutsModal";
import { TabNav, type AppTab } from "./components/TabNav";
import { WorkflowBar } from "./components/WorkflowBar";
import { DiscoverTab } from "./features/discover/DiscoverTab";
import { useDiscoverLookup } from "./features/discover/useDiscoverLookup";
import { useAuth } from "./context/AuthContext";
import { useToast } from "./context/ToastContext";
import { loadDiscoverDraft, useDiscoverDraftSync } from "./hooks/useDiscoverDraft";
import { useAnalyticsPage } from "./hooks/useAnalyticsPage";
import { useEnterAnimation } from "./hooks/useEnterAnimation";
import { useFocusMode } from "./hooks/useFocusMode";
import { loadRecentQueries } from "./hooks/useRecentQueries";
import { downloadCsv } from "./lib/exportCsv";
import { buildLookupQuery } from "./lib/queryIntent";
import {
  requestNotifyPermission,
  useSettings,
} from "./hooks/useSettings";

export default function App() {
  const { profile, loading, refresh, logout } = useAuth();
  const { push } = useToast();
  const { settings, update: updateSettings } = useSettings();
  const { focus, toggle: toggleFocus } = useFocusMode();
  const searchRef = useRef<HTMLInputElement>(null);

  const [tab, setTab] = useState<AppTab>("discover");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [bulkSeed, setBulkSeed] = useState("");
  const [mode, setMode] = useState<SearchMode>(settings.defaultMode);
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canLookup, setCanLookup] = useState(false);
  const [activity, setActivity] = useState<ActivityDay[]>([]);
  const [libraryKey, setLibraryKey] = useState(0);
  const [buildContext, setBuildContext] = useState<BuildContext | null>(null);
  const [recentQueries, setRecentQueries] = useState<string[]>(() => loadRecentQueries());
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const draftHydrated = useRef(false);

  const analyticsScreen = loading ? "loading" : !profile ? "auth" : tab;
  useAnalyticsPage(analyticsScreen);

  const suggestions = profile?.suggestions ?? [];
  useDiscoverDraftSync({ mode, query, name, domain });
  const entered = useEnterAnimation(!!profile);
  useEffect(() => {
    setMode(settings.defaultMode);
  }, [settings.defaultMode]);

  useEffect(() => {
    if (!profile || draftHydrated.current) return;
    draftHydrated.current = true;
    const d = loadDiscoverDraft();
    if (d?.mode) setMode(d.mode);
    if (d?.query) setQuery(d.query);
    if (d?.name) setName(d.name);
    if (d?.domain) setDomain(d.domain);
  }, [profile]);

  useEffect(() => {
    void fetchActivity(7).then(setActivity).catch(() => setActivity([]));
  }, [profile, libraryKey]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === "visible" && profile) void refresh();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [profile, refresh]);

  const refreshLibrary = useCallback(() => {
    setLibraryKey((k) => k + 1);
    void refresh();
    void fetchActivity(7).then(setActivity).catch(() => setActivity([]));
  }, [refresh]);

  const { runLookup } = useDiscoverLookup({
    mode,
    query,
    name,
    domain,
    busy,
    canLookup,
    notifyOnComplete: settings.notifyOnComplete,
    onBusy: setBusy,
    onError: setError,
    onJob: setJob,
    onActiveQuery: setActiveQuery,
    onQuery: setQuery,
    onTabDiscover: () => setTab("discover"),
    onBuildContext: setBuildContext,
    onRecentQueries: setRecentQueries,
    onDone: refreshLibrary,
    pushToast: push,
  });

  const runFromLibrary = useCallback(
    (q: string) => {
      setTab("discover");
      setMode("quick");
      setQuery(q);
      void runLookup(q);
    },
    [runLookup]
  );

  const goToBuild = useCallback(
    (q?: string) => {
      const text = q ?? buildLookupQuery(mode, query, name, domain);
      if (buildContext) setBuildContext({ ...buildContext });
      setTab("build");
      if (text.trim()) setQuery(text);
    },
    [buildContext, mode, query, name, domain]
  );

  const routeToBulk = useCallback(
    (text: string) => {
      setBulkSeed(text.trim());
      setTab("bulk");
      push("Moved to Bulk");
    },
    [push]
  );

  const exportHistory = useCallback(async () => {
    const items = await fetchHistory({ limit: 100 });
    downloadCsv("reachunt-history.csv", [
      ["query", "email", "status", "created_at"],
      ...items.map((i) => [i.query, i.email, i.status, i.created_at]),
    ]);
    push("Exported");
  }, [push]);

  const pickRecent = useCallback((q: string) => {
    setTab("discover");
    setMode("quick");
    setQuery(q);
    searchRef.current?.focus();
  }, []);

  const copyLastEmail = useCallback(() => {
    const email = job?.result?.email?.trim();
    if (!email) {
      push("No email to copy yet");
      return;
    }
    void navigator.clipboard.writeText(email).then(() => push("Copied email"));
  }, [job, push]);

  const paletteActions = useMemo(
    () =>
      buildDefaultActions({
        setTab,
        focusSearch: () => {
          setTab("discover");
          searchRef.current?.focus();
        },
        runLookup: () => void runLookup(),
        exportHistory: () => void exportHistory(),
        toggleNotify: () => {
          const next = !settings.notifyOnComplete;
          updateSettings({ notifyOnComplete: next });
          if (next) requestNotifyPermission();
        },
        notifyOn: settings.notifyOnComplete,
        toggleFocus,
        focusOn: focus,
        showShortcuts: () => setShortcutsOpen(true),
        goToBuild: () => goToBuild(),
        copyLastEmail,
        canCopyEmail: Boolean(job?.result?.email?.trim()),
      }),
    [
      runLookup,
      exportHistory,
      settings.notifyOnComplete,
      updateSettings,
      toggleFocus,
      focus,
      goToBuild,
      copyLastEmail,
      job,
    ]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        const t = e.target as HTMLElement;
        if (t.tagName !== "INPUT" && t.tagName !== "TEXTAREA") {
          e.preventDefault();
          setShortcutsOpen(true);
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (!busy && canLookup && tab === "discover") void runLookup();
      }
      if (e.key === "Escape") {
        if (paletteOpen || shortcutsOpen || accountOpen) {
          setPaletteOpen(false);
          setShortcutsOpen(false);
          setAccountOpen(false);
        }
      }
      const tabKeys: Record<string, AppTab> = {
        "1": "discover",
        "2": "build",
        "3": "bulk",
        "4": "library",
      };
      if ((e.metaKey || e.ctrlKey) && tabKeys[e.key]) {
        e.preventDefault();
        setTab(tabKeys[e.key]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, canLookup, runLookup, tab, paletteOpen, shortcutsOpen, accountOpen]);

  if (!profile) {
    return (
      <>
        <AmbientLayer />
        {loading ? null : <AuthScreen />}
      </>
    );
  }

  const stats = profile.stats ?? {
    lookups: 0,
    verified: 0,
    hit_rate: 0,
    today: 0,
  };

  const flow = (i: number) => ({ "--flow-i": i }) as React.CSSProperties;

  return (
    <>
      <AmbientLayer />
      <div className={`shell${focus ? " shell--focus" : ""}${entered ? " shell--entered" : ""}`}>
        <header className="shell__chrome">
          <div className="flow-item" style={flow(0)}>
            <ShellBar
              account={profile.account}
              focusOn={focus}
              onOpenPalette={() => setPaletteOpen(true)}
              onToggleFocus={toggleFocus}
              onOpenAccount={() => setAccountOpen(true)}
            />
          </div>
          <div className="flow-item" style={flow(1)}>
            <TabNav tab={tab} onChange={setTab} />
          </div>
          <div className="flow-item flow-item--soft" style={flow(2)}>
            <WorkflowBar busy={busy} canLookup={canLookup} tab={tab} lastQuery={activeQuery} />
          </div>
        </header>

        {tab === "discover" && !focus && (
          <section
            className="hero shell__hero flow-item"
            style={flow(3)}
            aria-labelledby="hero-title"
          >
            <HeroTitle />
            <InsightsStrip
              lookups={stats.lookups}
              verified={stats.verified ?? 0}
              hitRate={stats.hit_rate ?? 0}
              today={stats.today ?? 0}
            />
            <ActivityChart days={activity} />
          </section>
        )}

        {(tab === "discover" || tab === "bulk") && (
          <div className="shell__net flow-item" style={flow(4)}>
            <NetworkConnect onReadyChange={setCanLookup} />
          </div>
        )}

        <main className="shell__main flow-item" style={flow(5)}>
          {tab === "discover" && (
            <DiscoverTab
              flow={flow}
              searchRef={searchRef}
              recentQueries={recentQueries}
              onRecentPick={pickRecent}
              onRecentClear={() => {
                localStorage.removeItem("fe-recent-queries");
                setRecentQueries([]);
              }}
              query={query}
              name={name}
              domain={domain}
              mode={mode}
              onModeChange={setMode}
              onQueryChange={setQuery}
              onNameChange={setName}
              onDomainChange={setDomain}
              onSubmit={() => void runLookup()}
              busy={busy}
              canLookup={canLookup}
              suggestions={suggestions}
              onMultiPaste={routeToBulk}
              job={job}
              error={error}
              settings={settings}
              onSettingsChange={updateSettings}
              onRetry={() => void runLookup()}
              onSaveFavorite={(q, email) => {
                void addFavorite(q, email).then(() => {
                  push("Saved");
                  refreshLibrary();
                });
              }}
              onImpress={() => goToBuild(job?.query)}
              showSettings={!focus}
            />
          )}

          {tab === "build" && (
            <div
              id="panel-build"
              role="tabpanel"
              aria-labelledby="tab-build"
              className="tab-panel tab-panel--build"
              style={flow(6)}
            >
              <header className="tab-panel__head">
                <h2 className="tab-panel__title">Build</h2>
                <p className="tab-panel__desc">Prompts for Lovable, v0, or Bolt.</p>
              </header>
              <BuildStudio
                context={buildContext}
                defaultQuery={
                  buildContext
                    ? buildContext.founderName
                      ? `${buildContext.founderName} - ${buildContext.domain}`
                      : buildContext.domain
                    : query
                }
              />
            </div>
          )}

          {tab === "bulk" && (
            <div
              id="panel-bulk"
              role="tabpanel"
              aria-labelledby="tab-bulk"
              className="tab-panel tab-panel--bulk"
              style={flow(6)}
            >
              <header className="tab-panel__head">
                <h2 className="tab-panel__title">Bulk</h2>
                <p className="tab-panel__desc">
                  Queue up to 100 lookups - server runs them in order, cache hits fly through.
                </p>
              </header>
              <BulkPanel
                key={bulkSeed.slice(0, 40)}
                initialText={bulkSeed}
                disabled={!canLookup}
                notify={settings.notifyOnComplete}
                mailSettings={settings}
                onDone={refreshLibrary}
              />
            </div>
          )}

          {tab === "library" && (
            <div
              id="panel-library"
              role="tabpanel"
              aria-labelledby="tab-library"
              className="tab-panel tab-panel--library"
              style={flow(6)}
            >
              <header className="tab-panel__head">
                <h2 className="tab-panel__title">Library</h2>
                <p className="tab-panel__desc">History, favorites, and exports.</p>
              </header>
              <LibraryPanel
                key={libraryKey}
                onRun={runFromLibrary}
                onBuild={(q) => goToBuild(q)}
                mailSettings={settings}
              />
            </div>
          )}
        </main>

        <CommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          actions={paletteActions}
        />
        <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
        <AccountSettingsModal
          open={accountOpen}
          account={profile.account}
          avatarStyles={profile.avatar_styles}
          settings={settings}
          onSettingsChange={updateSettings}
          onClose={() => setAccountOpen(false)}
          onSaved={refresh}
          onLogout={logout}
          savingDisabled={profile.user.id === "local"}
        />
      </div>
    </>
  );
}
