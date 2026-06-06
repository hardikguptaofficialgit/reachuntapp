import {
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "./lib/session";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function buildFetchOpts(extra?: RequestInit): RequestInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getSessionToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return {
    credentials: "include",
    ...extra,
    headers: {
      ...headers,
      ...(extra?.headers as Record<string, string> | undefined),
    },
  };
}

async function parseError(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({}));
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail[0]?.msg ?? "Request failed.";
  return `Request failed (${res.status})`;
}

export type JobStatus = "queued" | "running" | "completed" | "failed";
export type NetworkState = "disconnected" | "connecting" | "connected";

export interface PublicStep {
  id: string;
  label: string;
}

export interface LookupResultPayload {
  name: string;
  domain: string;
  display_name: string;
  profile_url: string;
  email: string;
  status: string;
  confidence?: number;
  validation?: {
    score?: number;
    verdict?: string;
    signals?: string[];
    mx_found?: boolean;
    smtp_checked?: boolean;
    smtp_valid?: boolean | null;
    disposable?: boolean;
    free_provider?: boolean;
    role_account?: boolean;
    catch_all?: boolean | null;
  };
  message: string;
  steps: PublicStep[];
}

export interface Job {
  id: string;
  query: string;
  status: JobStatus;
  phase: string;
  created_at: string;
  updated_at: string;
  result: LookupResultPayload | null;
  error: string | null;
}

export interface UserAccount {
  display_name: string;
  email: string;
  avatar_style: string;
  avatar_seed: string;
  created_at: string;
  linkit_uid: string;
}

export interface UserProfile {
  user: { id: string; email: string };
  account: UserAccount;
  integration: { network_connected: boolean; connected_at: string | null };
  stats: { lookups: number; verified: number; hit_rate: number; today: number };
  suggestions?: string[];
  avatar_styles?: string[];
}

export interface AccountUpdatePayload {
  display_name?: string;
  avatar_style?: string;
  avatar_seed?: string;
}

export type ParseResult =
  | {
      ok: true;
      name: string;
      domain: string;
      company_only?: boolean;
      company_label?: string;
      query_kind?: "person" | "company_domain" | "company_name";
    }
  | { ok: false; error: string };

export interface NetworkStatus {
  state: NetworkState;
  message: string;
  can_lookup: boolean;
  client_mode?: boolean;
  open_url?: string;
}

export interface HistoryItem {
  id: string;
  query: string;
  email: string;
  status: string;
  created_at: string;
}

export interface FavoriteItem {
  id: string;
  query: string;
  email: string;
  created_at: string;
}

export interface ActivityDay {
  day: string;
  total: number;
  verified: number;
}

export async function fetchHistory(opts?: {
  q?: string;
  verifiedOnly?: boolean;
  missedOnly?: boolean;
  limit?: number;
}): Promise<HistoryItem[]> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.verifiedOnly) params.set("verified_only", "true");
  if (opts?.missedOnly) params.set("missed_only", "true");
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/api/v1/history${qs ? `?${qs}` : ""}`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.items ?? [];
}

export async function checkHistoryQuery(query: string): Promise<boolean> {
  const params = new URLSearchParams({ q: query });
  const res = await fetch(`${API_BASE}/api/v1/history/check?${params}`, buildFetchOpts());
  if (!res.ok) return false;
  const data = await res.json();
  return Boolean(data.exists);
}

export async function removeHistoryItem(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/history/${id}`, {
    ...buildFetchOpts(),
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function clearHistory(opts?: {
  q?: string;
  verifiedOnly?: boolean;
  missedOnly?: boolean;
}): Promise<number> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.verifiedOnly) params.set("verified_only", "true");
  if (opts?.missedOnly) params.set("missed_only", "true");
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/api/v1/history${qs ? `?${qs}` : ""}`, {
    ...buildFetchOpts(),
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return Number(data.deleted ?? 0);
}

export async function fetchActivity(days = 7): Promise<ActivityDay[]> {
  const res = await fetch(`${API_BASE}/api/v1/activity?days=${days}`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.days ?? [];
}

export async function fetchFavorites(): Promise<FavoriteItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/favorites`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.items ?? [];
}

export async function addFavorite(query: string, email = ""): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/favorites`, {
    ...buildFetchOpts(),
    method: "POST",
    body: JSON.stringify({ query, email }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function removeFavorite(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/favorites/${id}`, {
    ...buildFetchOpts(),
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function clearFavorites(): Promise<number> {
  const res = await fetch(`${API_BASE}/api/v1/favorites`, {
    ...buildFetchOpts(),
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return Number(data.deleted ?? 0);
}

export interface BulkLookupResult {
  job_ids: string[];
  queued: number;
  requested: number;
}

export async function createBulkLookup(queries: string[]): Promise<BulkLookupResult> {
  const res = await fetch(`${API_BASE}/api/v1/lookup/bulk`, buildFetchOpts({
    method: "POST",
    body: JSON.stringify({ queries }),
  }));
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as BulkLookupResult;
  return {
    job_ids: data.job_ids ?? [],
    queued: data.queued ?? data.job_ids?.length ?? 0,
    requested: data.requested ?? queries.length,
  };
}

export interface QueueLimits {
  bulk_max_queries: number;
  queue_max_per_user: number;
  job_status_batch_max: number;
  job_worker_count: number;
  queue: {
    total: number;
    queued: number;
    running: number;
    completed: number;
    failed: number;
    queue_depth: number;
    workers: number;
  };
}

export async function fetchQueueLimits(): Promise<QueueLimits> {
  const res = await fetch(`${API_BASE}/api/v1/config/limits`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<QueueLimits>;
}

export async function fetchJobsStatus(jobIds: string[]): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/api/v1/jobs/status`, {
    ...buildFetchOpts(),
    method: "POST",
    body: JSON.stringify({ job_ids: jobIds }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.jobs ?? [];
}

export async function exchangeLinkitToken(idToken: string) {
  const res = await fetch(
    `${API_BASE}/api/v1/auth/linkit/exchange`,
    buildFetchOpts({
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),
  );
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  if (data.token) setSessionToken(data.token);
  return data;
}

export async function logout() {
  await fetch(
    `${API_BASE}/api/v1/auth/logout`,
    buildFetchOpts({ method: "POST" }),
  );
  clearSessionToken();
}

export async function fetchMe(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/me`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function updateAccount(
  payload: AccountUpdatePayload,
): Promise<{ account: UserAccount }> {
  const res = await fetch(`${API_BASE}/api/v1/me/account`, {
    ...buildFetchOpts(),
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchNetwork(): Promise<NetworkStatus> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/network`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function connectNetwork(): Promise<NetworkStatus> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/network/connect`, {
    ...buildFetchOpts(),
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function refreshNetwork(): Promise<NetworkStatus> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/network/refresh`, {
    ...buildFetchOpts(),
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createLookup(query: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/lookup`, {
    ...buildFetchOpts(),
    method: "POST",
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as { job_id: string };
  return data.job_id;
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`, buildFetchOpts());
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Job>;
}

export interface BuildContext {
  company: string;
  domain: string;
  founderName: string;
  founderEmail: string;
}

export interface BuildPromptType {
  id: string;
  label: string;
  hint: string;
}

export interface BuildPromptQuota {
  limit: number;
  used: number;
  remaining: number;
  ai_enabled: boolean;
  unlimited?: boolean;
}

export interface BuildPromptResult {
  prompt: string;
  prompt_type: string;
  company: string;
  domain: string;
  founder_name: string;
  source?: "ai" | "template";
  quota?: BuildPromptQuota;
}

export async function fetchBuildPromptTypes(): Promise<{
  types: BuildPromptType[];
  ai_enabled: boolean;
}> {
  const res = await fetch(`${API_BASE}/api/v1/build-prompt/types`, buildFetchOpts());
  if (!res.ok) throw new Error("Could not load prompt types.");
  const data = await res.json();
  return { types: data.types ?? [], ai_enabled: Boolean(data.ai_enabled) };
}

export async function fetchBuildPromptQuota(): Promise<BuildPromptQuota> {
  const res = await fetch(`${API_BASE}/api/v1/build-prompt/quota`, buildFetchOpts());
  if (!res.ok) throw new Error("Could not load prompt quota.");
  return res.json() as Promise<BuildPromptQuota>;
}

export async function fetchBuildPrompt(opts: {
  query: string;
  promptType: string;
  founderName?: string;
  founderEmail?: string;
}): Promise<BuildPromptResult> {
  const res = await fetch(`${API_BASE}/api/v1/build-prompt`, {
    ...buildFetchOpts(),
    method: "POST",
    body: JSON.stringify({
      query: opts.query,
      prompt_type: opts.promptType,
      founder_name: opts.founderName ?? "",
      founder_email: opts.founderEmail ?? "",
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<BuildPromptResult>;
}

/** Server-authoritative parse (gates lookups). */
export async function parseQuery(query: string): Promise<ParseResult> {
  const res = await fetch(`${API_BASE}/api/v1/parse`, {
    ...buildFetchOpts(),
    method: "POST",
    body: JSON.stringify({ query: query.trim() }),
  });
  if (!res.ok) {
    return { ok: false, error: await parseError(res) };
  }
  return res.json() as Promise<ParseResult>;
}

/** Fast local preview only — do not use to submit lookups. */
export async function parseQueryPreview(query: string): Promise<ParseResult> {
  const { parseQueryLocal } = await import("./lib/parseQuery");
  const q = query.trim();
  if (!q) return { ok: false, error: "Enter a query." };
  try {
    return await parseQuery(q);
  } catch {
    return parseQueryLocal(q);
  }
}

function handleJobEvent(
  raw: string,
  jobId: string,
  onUpdate: (job: Job) => void,
  resolve: (job: Job) => void,
  reject: (err: Error) => void,
): boolean {
  try {
    const data = JSON.parse(raw) as Job & { error?: string };
    if (data.error === "not_found") {
      reject(new Error("Job not found."));
      return true;
    }
    onUpdate(data);
    if (data.status === "completed" || data.status === "failed") {
      resolve(data);
      return true;
    }
  } catch {
    /* ignore malformed */
  }
  return false;
}

export function streamJob(jobId: string, onUpdate: (job: Job) => void): Promise<Job> {
  const url = `${API_BASE}/api/v1/jobs/${jobId}/stream`;

  return fetch(url, buildFetchOpts()).then(
    (res) =>
      new Promise<Job>((resolve, reject) => {
        if (!res.ok || !res.body) {
          void getJob(jobId)
            .then((job) => {
              onUpdate(job);
              if (job.status === "completed" || job.status === "failed") resolve(job);
              else reject(new Error("Could not stream job status."));
            })
            .catch((e) => reject(e instanceof Error ? e : new Error(String(e))));
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let settled = false;

        const finish = (job: Job) => {
          if (settled) return;
          settled = true;
          resolve(job);
        };

        const fail = (err: Error) => {
          if (settled) return;
          settled = true;
          reject(err);
        };

        const pump = (): void => {
          void reader.read().then(({ done, value }) => {
            if (settled) return;
            if (done) {
              void getJob(jobId)
                .then((job) => {
                  onUpdate(job);
                  if (job.status === "completed" || job.status === "failed") finish(job);
                  else fail(new Error("Connection lost."));
                })
                .catch((e) => fail(e instanceof Error ? e : new Error(String(e))));
              return;
            }
            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split("\n\n");
            buffer = blocks.pop() ?? "";
            for (const block of blocks) {
              const line = block.split("\n").find((l) => l.startsWith("data: "));
              if (!line) continue;
              if (handleJobEvent(line.slice(6), jobId, onUpdate, finish, fail)) return;
            }
            pump();
          });
        };
        pump();
      }),
  );
}

const POLL_TIMEOUT_MS = 180_000;

export async function pollJob(
  jobId: string,
  onUpdate: (job: Job) => void,
  intervalMs = 1100,
  timeoutMs = POLL_TIMEOUT_MS
): Promise<Job> {
  const deadline = Date.now() + timeoutMs;
  try {
    return await Promise.race([
      streamJob(jobId, onUpdate),
      new Promise<Job>((_, reject) => {
        const left = deadline - Date.now();
        window.setTimeout(
          () => reject(new Error("Lookup timed out. Try again.")),
          Math.max(left, 0)
        );
      }),
    ]);
  } catch {
    for (;;) {
      if (Date.now() > deadline) {
        throw new Error("Lookup timed out. Try again.");
      }
      const job = await getJob(jobId);
      onUpdate(job);
      if (job.status === "completed" || job.status === "failed") {
        return job;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
}
