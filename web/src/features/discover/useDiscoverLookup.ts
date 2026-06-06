import { useCallback, useRef } from "react";
import {
  createLookup,
  parseQuery,
  pollJob,
  type BuildContext,
  type Job,
} from "../../api";
import type { SearchMode } from "../../components/SearchForm";
import { buildLookupQuery } from "../../lib/queryIntent";
import { trackEvent } from "../../lib/analytics";
import { notifyComplete } from "../../hooks/useSettings";
import { loadRecentQueries, pushRecentQuery } from "../../hooks/useRecentQueries";

type Args = {
  mode: SearchMode;
  query: string;
  name: string;
  domain: string;
  busy: boolean;
  canLookup: boolean;
  notifyOnComplete: boolean;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
  onJob: (job: Job | null) => void;
  onActiveQuery: (q: string | null) => void;
  onQuery: (q: string) => void;
  onTabDiscover: () => void;
  onBuildContext: (ctx: BuildContext | null) => void;
  onRecentQueries: (items: string[]) => void;
  onDone: () => void;
  pushToast: (msg: string) => void;
};

export function useDiscoverLookup(args: Args) {
  const lookupGen = useRef(0);

  const runLookup = useCallback(
    async (text?: string) => {
      if (args.busy) return;

      const q = (text ?? buildLookupQuery(args.mode, args.query, args.name, args.domain)).trim();
      if (!q) return;
      if (!args.canLookup) {
        args.onError("Discovery is getting ready. Try again in a moment.");
        args.onTabDiscover();
        return;
      }

      const parsed = await parseQuery(q);
      if (!parsed.ok) {
        args.onError(parsed.error);
        args.onTabDiscover();
        return;
      }

      const gen = ++lookupGen.current;
      args.onTabDiscover();
      if (args.mode === "quick") args.onQuery(q);
      args.onBusy(true);
      args.onError(null);
      args.onJob(null);
      args.onActiveQuery(q);
      trackEvent("lookup_start", { mode: args.mode });

      try {
        const jobId = await createLookup(q);
        const finalJob = await pollJob(jobId, args.onJob);
        if (gen !== lookupGen.current) return;
        const email = finalJob.result?.email ?? "";
        if (finalJob.status === "failed") {
          args.onError(finalJob.error ?? finalJob.result?.message ?? "Failed.");
          args.pushToast("Lookup failed.");
        } else {
          const r = finalJob.result;
          if (email) {
            args.pushToast("Email found.");
            trackEvent("lookup_complete", { hit: true });
          } else {
            args.pushToast("No email found.");
            trackEvent("lookup_complete", { hit: false });
          }
          if (r?.domain) {
            args.onBuildContext({
              company: r.name || r.domain.split(".")[0],
              domain: r.domain,
              founderName: r.display_name || "",
              founderEmail: email,
            });
          }
          if (args.notifyOnComplete) {
            notifyComplete(q, email);
          }
        }
        args.onRecentQueries(pushRecentQuery(q) ?? loadRecentQueries());
        args.onDone();
      } catch (err) {
        if (gen === lookupGen.current) {
          args.onError(err instanceof Error ? err.message : "Something went wrong.");
        }
      } finally {
        if (gen === lookupGen.current) {
          args.onBusy(false);
          args.onActiveQuery(null);
        }
      }
    },
    [
      args.busy,
      args.canLookup,
      args.mode,
      args.query,
      args.name,
      args.domain,
      args.notifyOnComplete,
      args.onBusy,
      args.onError,
      args.onJob,
      args.onActiveQuery,
      args.onQuery,
      args.onTabDiscover,
      args.onBuildContext,
      args.onRecentQueries,
      args.onDone,
      args.pushToast,
    ]
  );

  return { runLookup, lookupGen };
}
