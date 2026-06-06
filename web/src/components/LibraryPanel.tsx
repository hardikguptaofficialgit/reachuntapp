import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addFavorite,
  clearFavorites,
  clearHistory,
  fetchFavorites,
  fetchHistory,
  removeFavorite,
  removeHistoryItem,
  type FavoriteItem,
  type HistoryItem,
} from "../api";
import { useToast } from "../context/ToastContext";
import type { AppSettings } from "../hooks/useSettings";
import { parseNameFromQuery } from "../lib/mailCompose";
import { BulkMailCompose } from "./BulkMailCompose";

type Props = {
  onRun: (query: string) => void;
  onBuild?: (query: string) => void;
  mailSettings?: Pick<
    AppSettings,
    "mailSubject" | "mailBody" | "mailMode" | "mailSelfTo"
  >;
};

export function LibraryPanel({ onRun, onBuild, mailSettings }: Props) {
  const { push } = useToast();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "found" | "miss">("all");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const [clearingSaved, setClearingSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      const [h, f] = await Promise.all([
        fetchHistory({
          q: search,
          verifiedOnly: filter === "found",
          missedOnly: filter === "miss",
          limit: 50,
        }),
        fetchFavorites(),
      ]);
      setHistory(h);
      setFavorites(f);
    } catch {
      setHistory([]);
      setFavorites([]);
    }
  }, [search, filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const exportCsv = () => {
    const rows = [
      ["query", "email", "status", "created_at"],
      ...history.map((i) => [i.query, i.email, i.status, i.created_at]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reachunt-history.csv";
    a.click();
    URL.revokeObjectURL(a.href);
    push("Exported");
  };

  const star = async (item: HistoryItem) => {
    await addFavorite(item.query, item.email);
    push("Saved");
    void load();
  };

  const unstar = async (id: string) => {
    await removeFavorite(id);
    void load();
  };

  const clearSaved = async () => {
    if (!favorites.length) return;
    if (!window.confirm("Delete all saved lookups? This cannot be undone.")) return;
    setClearingSaved(true);
    try {
      const deleted = await clearFavorites();
      setFavorites([]);
      push(deleted ? `Deleted ${deleted}` : "Nothing to delete");
    } catch {
      push("Clear saved failed");
    } finally {
      setClearingSaved(false);
    }
  };

  const deleteHistory = async (item: HistoryItem) => {
    if (!window.confirm(`Delete "${item.query}" from history?`)) return;
    setDeletingId(item.id);
    try {
      await removeHistoryItem(item.id);
      setHistory((rows) => rows.filter((row) => row.id !== item.id));
      push("Deleted");
    } catch {
      push("Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const clearVisibleHistory = async () => {
    if (!history.length) return;
    const scoped = search.trim() || filter !== "all";
    const label = scoped ? "visible history results" : "all history";
    if (!window.confirm(`Delete ${label}? This cannot be undone.`)) return;
    setClearing(true);
    try {
      const deleted = await clearHistory({
        q: search,
        verifiedOnly: filter === "found",
        missedOnly: filter === "miss",
      });
      push(deleted ? `Deleted ${deleted}` : "Nothing to delete");
      void load();
    } catch {
      push("Clear failed");
    } finally {
      setClearing(false);
    }
  };

  const mailRecipients = useMemo(
    () =>
      history
        .filter((h) => h.email?.trim())
        .map((h) => ({
          email: h.email.trim(),
          name: parseNameFromQuery(h.query),
          query: h.query,
        })),
    [history]
  );

  return (
    <section className="library">
      <div className="library__tools">
        <input
          className="library__search"
          type="search"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="library__chips">
          {(["all", "found", "miss"] as const).map((f) => (
            <button
              key={f}
              type="button"
              className={`library__chip${filter === f ? " library__chip--on" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : f === "found" ? "Found" : "Miss"}
            </button>
          ))}
        </div>
        <button type="button" className="glass-btn glass-btn--sm" onClick={exportCsv}>
          Export
        </button>
        <button
          type="button"
          className="glass-btn glass-btn--sm"
          onClick={() => void clearVisibleHistory()}
          disabled={!history.length || clearing}
        >
          {clearing ? "Clearing" : filter === "all" && !search.trim() ? "Clear all" : "Clear shown"}
        </button>
      </div>

      {mailRecipients.length > 0 && (
        <BulkMailCompose
          recipients={mailRecipients}
          settings={mailSettings}
          title="Email from library"
        />
      )}

      {favorites.length > 0 && (
        <>
          <div className="library__section-head">
            <h3 className="library__head">Saved</h3>
            <button
              type="button"
              className="library__link"
              onClick={() => void clearSaved()}
              disabled={clearingSaved}
            >
              {clearingSaved ? "Clearing" : "Clear saved"}
            </button>
          </div>
          <ul className="recent__list">
            {favorites.map((f) => (
              <li key={f.id} className="library__fav">
                <button type="button" className="recent__item" onClick={() => onRun(f.query)}>
                  <span className="recent__q">{f.query}</span>
                  <span className="recent__e recent__e--hit">{f.email || "—"}</span>
                </button>
                <button
                  type="button"
                  className="library__star library__star--on"
                  onClick={() => void unstar(f.id)}
                  aria-label="Remove saved"
                >
                  ★
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3 className="library__head">History</h3>
      <ul className="recent__list">
        {history.map((item) => (
          <li key={item.id || `${item.created_at}-${item.query}`} className="library__fav">
            <button type="button" className="recent__item" onClick={() => onRun(item.query)}>
              <span className="recent__q">{item.query}</span>
              <span className={`recent__e${item.email ? " recent__e--hit" : ""}`}>
                {item.email || "—"}
              </span>
            </button>
            <button
              type="button"
              className="library__star"
              onClick={() => void star(item)}
              aria-label="Save"
            >
              ☆
            </button>
            {onBuild && (
              <button
                type="button"
                className="library__star library__star--build"
                onClick={() => onBuild(item.query)}
                aria-label="Build project"
                title="Build prompt"
              >
                ◫
              </button>
            )}
            <button
              type="button"
              className="library__star library__star--danger"
              onClick={() => void deleteHistory(item)}
              disabled={deletingId === item.id}
              aria-label="Delete lookup"
              title="Delete lookup"
            >
              {deletingId === item.id ? "..." : "x"}
            </button>
          </li>
        ))}
      </ul>
      {!history.length && <p className="library__empty">No results yet.</p>}
    </section>
  );
}
