import { useCallback, useEffect, useMemo, useState } from "react";
import { createBulkLookup, fetchQueueLimits, type Job, type QueueLimits } from "../api";
import { BulkMailCompose } from "./BulkMailCompose";
import { useToast } from "../context/ToastContext";
import type { AppSettings } from "../hooks/useSettings";
import { notifyComplete } from "../hooks/useSettings";
import {
  buildComposeOptions,
  fillTemplate,
  openGmailCompose,
  parseNameFromQuery,
} from "../lib/mailCompose";
import { downloadCsv } from "../lib/exportCsv";
import { waitForBulkJobs } from "../lib/bulkRunner";
import { GmailIcon } from "./icons/GmailIcon";

const DEFAULT_MAX = 100;

type BulkRow = {
  jobId: string;
  query: string;
  status: Job["status"];
  email: string;
};

type Props = {
  disabled?: boolean;
  notify: boolean;
  onDone: () => void;
  initialText?: string;
  mailSettings?: Pick<
    AppSettings,
    "mailSubject" | "mailBody" | "mailMode" | "mailSelfTo"
  >;
};

function rowsFromJobs(
  jobIds: string[],
  batch: string[],
  jobs: Map<string, Job>
): BulkRow[] {
  return jobIds.map((id, i) => {
    const j = jobs.get(id);
    return {
      jobId: id,
      query: batch[i] ?? j?.query ?? "",
      status: j?.status ?? "queued",
      email: j?.result?.email ?? "",
    };
  });
}

export function BulkPanel({
  disabled,
  notify,
  onDone,
  initialText = "",
  mailSettings,
}: Props) {
  const { push } = useToast();
  const [text, setText] = useState(initialText);
  const [running, setRunning] = useState(false);
  const [rows, setRows] = useState<BulkRow[]>([]);
  const [doneCount, setDoneCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [drag, setDrag] = useState(false);
  const [limits, setLimits] = useState<QueueLimits | null>(null);

  const maxLines = limits?.bulk_max_queries ?? DEFAULT_MAX;

  useEffect(() => {
    void fetchQueueLimits().then(setLimits).catch(() => setLimits(null));
  }, []);

  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  const failed = rows.filter((r) => r.status === "failed");

  const mailRecipients = useMemo(
    () =>
      rows
        .filter((r) => r.email)
        .map((r) => ({
          email: r.email,
          name: parseNameFromQuery(r.query),
          query: r.query,
        })),
    [rows]
  );

  const ingestFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result ?? "");
      setText((prev) => (prev ? `${prev}\n${raw}` : raw));
      push("Imported");
    };
    reader.readAsText(file);
  }, [push]);

  const overLimit = lines.length > maxLines;

  const run = async (queries?: string[]) => {
    const batch = (queries ?? lines).slice(0, maxLines);
    if (!batch.length || disabled || running) return;
    setRunning(true);
    setRows([]);
    setDoneCount(0);
    setTotalCount(0);

    try {
      const { job_ids: jobIds, queued, requested } = await createBulkLookup(batch);
      if (!jobIds.length) {
        push("Nothing queued — check your lines or queue limit");
        return;
      }
      if (queued < requested) {
        push(`Queued ${queued} of ${requested} (queue cap)`);
      }

      setTotalCount(jobIds.length);
      setRows(
        jobIds.map((id, i) => ({
          jobId: id,
          query: batch[i] ?? "",
          status: "queued",
          email: "",
        }))
      );

      const jobs = await waitForBulkJobs(
        jobIds,
        (_jobs, done, total) => {
          setDoneCount(done);
          setTotalCount(total);
          setRows((prev) =>
            prev.map((r) => {
              const j = _jobs.find((x) => x.id === r.jobId);
              if (!j) return r;
              return {
                ...r,
                status: j.status,
                email: j.result?.email ?? "",
              };
            })
          );
        },
        { batchSize: limits?.job_status_batch_max ?? 40 }
      );

      const finalRows = rowsFromJobs(jobIds, batch, jobs);
      setRows(finalRows);

      let foundCount = 0;
      for (const r of finalRows) {
        if (r.email) foundCount += 1;
        if (notify && r.email) notifyComplete(r.query, r.email);
      }

      push(`Done · ${foundCount}/${jobIds.length} emails`);
      onDone();
      void fetchQueueLimits().then(setLimits).catch(() => undefined);
    } catch (err) {
      push(err instanceof Error ? err.message : "Bulk failed");
    } finally {
      setRunning(false);
    }
  };

  const hits = rows.filter((r) => r.email);

  const copyResults = () => {
    if (!hits.length) return;
    const body = hits.map((r) => `${r.query}\t${r.email}`).join("\n");
    void navigator.clipboard.writeText(body);
    push("Copied results");
  };

  const copyEmailsOnly = () => {
    if (!hits.length) return;
    void navigator.clipboard.writeText(hits.map((r) => r.email).join(", "));
    push("Copied emails");
  };

  const exportHits = () => {
    if (!hits.length) return;
    downloadCsv("bulk-hits.csv", [
      ["query", "email", "status"],
      ...hits.map((r) => [r.query, r.email, r.status]),
    ]);
    push("Exported hits");
  };

  const retryFailed = () => {
    const qs = failed.map((r) => r.query);
    if (!qs.length) return;
    void run(qs);
  };

  const queueHint =
    limits && (limits.queue.queued > 0 || limits.queue.running > 0)
      ? `Queue: ${limits.queue.running} running, ${limits.queue.queued} waiting`
      : null;

  return (
    <section
      className={`bulk${drag ? " bulk--drag" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files[0];
        if (f) ingestFile(f);
      }}
    >
      {drag && <p className="bulk__drop">Drop file to import</p>}
      <p className={`bulk__hint${overLimit ? " bulk__hint--warn" : ""}`}>
        {overLimit
          ? `Only first ${maxLines} lines will run — remove ${lines.length - maxLines} extra`
          : `One per line · up to ${maxLines} · queued on server · drop .txt / .csv`}
      </p>
      {queueHint && <p className="bulk__queue-hint">{queueHint}</p>}
      <textarea
        className="bulk__area"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={"Hardik Gupta — linkitapp.in\nSarah Chen — stripe.com"}
        disabled={running || disabled}
        rows={8}
      />
      <div className="bulk__foot">
        <span className="bulk__count">
          {running && totalCount > 0
            ? `${doneCount}/${totalCount} done`
            : `${lines.length} line${lines.length === 1 ? "" : "s"}`}
        </span>
        <div className="bulk__actions">
          {rows.length > 0 && !running && (
            <>
              <button type="button" className="glass-btn glass-btn--sm" onClick={copyResults}>
                Copy hits
              </button>
              {hits.length > 0 && (
                <>
                  <button type="button" className="glass-btn glass-btn--sm" onClick={copyEmailsOnly}>
                    Copy emails
                  </button>
                  <button type="button" className="glass-btn glass-btn--sm" onClick={exportHits}>
                    CSV
                  </button>
                </>
              )}
              {failed.length > 0 && (
                <button type="button" className="glass-btn glass-btn--sm" onClick={retryFailed}>
                  Retry {failed.length}
                </button>
              )}
            </>
          )}
          <button
            type="button"
            className="glass-btn glass-btn--primary command__go bulk__go"
            disabled={!lines.length || running || disabled || overLimit}
            onClick={() => void run()}
          >
            {running ? "···" : "Queue all"}
          </button>
        </div>
      </div>

      {running && (
        <div className="bulk__progress">
          <div
            className="bulk__progress-fill"
            style={{
              width: `${totalCount ? (doneCount / totalCount) * 100 : 0}%`,
            }}
          />
        </div>
      )}

      {mailRecipients.length > 0 && !running && (
        <BulkMailCompose
          recipients={mailRecipients}
          settings={mailSettings}
          title="Bulk outreach"
        />
      )}

      {rows.length > 0 && (
        <ul className="bulk__list">
          {rows.map((r) => (
            <li
              key={r.jobId}
              className={`bulk__row${running && r.status === "running" ? " bulk__row--active" : ""}${r.status === "completed" && r.email ? " bulk__row--hit" : ""}`}
            >
              <span className="bulk__q">{r.query}</span>
              <span className="bulk__end">
                <span className={`bulk__s bulk__s--${r.status}`}>
                  {r.email || (r.status === "running" ? "···" : r.status)}
                </span>
                {r.email && !running && (
                  <button
                    type="button"
                    className="bulk__gmail glass-btn glass-btn--sm"
                    title="Gmail this person"
                    aria-label={`Gmail ${r.email}`}
                    onClick={() => {
                      const sub = fillTemplate(mailSettings?.mailSubject ?? "", {
                        name: parseNameFromQuery(r.query),
                        email: r.email,
                        query: r.query,
                      });
                      const bod = fillTemplate(mailSettings?.mailBody ?? "", {
                        name: parseNameFromQuery(r.query),
                        email: r.email,
                        query: r.query,
                      });
                      openGmailCompose(
                        buildComposeOptions([r.email], "to", sub, bod)
                      );
                    }}
                  >
                    <GmailIcon size={14} />
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
