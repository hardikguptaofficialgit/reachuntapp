import { fetchJobsStatus, type Job } from "../api";

const TERMINAL = new Set<Job["status"]>(["completed", "failed"]);

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

/** Poll many jobs in parallel batches until all finish (server queue runs them). */
export async function waitForBulkJobs(
  jobIds: string[],
  onUpdate: (jobs: Job[], done: number, total: number) => void,
  opts?: { intervalMs?: number; batchSize?: number }
): Promise<Map<string, Job>> {
  const intervalMs = opts?.intervalMs ?? 1100;
  const batchSize = opts?.batchSize ?? 40;
  const pending = new Set(jobIds);
  const results = new Map<string, Job>();

  while (pending.size > 0) {
    const ids = [...pending];
    const batches = chunk(ids, batchSize);
    const fetched = await Promise.all(
      batches.map((batch) => fetchJobsStatus(batch).catch(() => [] as Job[]))
    );

    for (const jobs of fetched) {
      for (const job of jobs) {
        results.set(job.id, job);
        if (TERMINAL.has(job.status)) pending.delete(job.id);
      }
    }

    const done = jobIds.filter((id) => {
      const s = results.get(id)?.status;
      return s && TERMINAL.has(s);
    }).length;
    onUpdate(
      jobIds.map((id) => results.get(id)).filter(Boolean) as Job[],
      done,
      jobIds.length
    );

    if (pending.size > 0) await sleep(intervalMs);
  }

  return results;
}
