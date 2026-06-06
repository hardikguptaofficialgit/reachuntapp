export type RecipientField = "to" | "cc" | "bcc";

export type MailRecipient = {
  email: string;
  name?: string;
  query?: string;
};

export type ComposeOptions = {
  to?: string[];
  cc?: string[];
  bcc?: string[];
  subject?: string;
  body?: string;
};

/** Gmail web compose max varies; keep batches URL-safe. */
export const GMAIL_BATCH_SIZE = 35;

export function parseNameFromQuery(query: string): string {
  const part = query.split("—")[0]?.trim() || query.split("-")[0]?.trim();
  return part || query.trim();
}

export function fillTemplate(
  template: string,
  ctx: { name?: string; email?: string; query?: string; domain?: string }
): string {
  const name = ctx.name || (ctx.query ? parseNameFromQuery(ctx.query) : "");
  const domain = ctx.domain || (ctx.query?.includes("—") ? ctx.query.split("—")[1]?.trim() : "");
  return template
    .replace(/\{\{name\}\}/gi, name)
    .replace(/\{\{email\}\}/gi, ctx.email ?? "")
    .replace(/\{\{query\}\}/gi, ctx.query ?? "")
    .replace(/\{\{domain\}\}/gi, domain ?? "");
}

export function uniqueEmails(recipients: MailRecipient[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const r of recipients) {
    const e = r.email.trim().toLowerCase();
    if (!e || seen.has(e)) continue;
    seen.add(e);
    out.push(r.email.trim());
  }
  return out;
}

export function chunkEmails(emails: string[], size = GMAIL_BATCH_SIZE): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < emails.length; i += size) {
    chunks.push(emails.slice(i, i + size));
  }
  return chunks;
}

export function buildGmailComposeUrl(opts: ComposeOptions): string {
  const params = new URLSearchParams();
  params.set("view", "cm");
  params.set("fs", "1");
  if (opts.to?.length) params.set("to", opts.to.join(","));
  if (opts.cc?.length) params.set("cc", opts.cc.join(","));
  if (opts.bcc?.length) params.set("bcc", opts.bcc.join(","));
  if (opts.subject) params.set("su", opts.subject);
  if (opts.body) params.set("body", opts.body);
  return `https://mail.google.com/mail/?${params.toString()}`;
}

export function buildMailtoUrl(opts: ComposeOptions): string {
  const to = (opts.to ?? []).join(",");
  const params = new URLSearchParams();
  if (opts.cc?.length) params.set("cc", opts.cc.join(","));
  if (opts.bcc?.length) params.set("bcc", opts.bcc.join(","));
  if (opts.subject) params.set("subject", opts.subject);
  if (opts.body) params.set("body", opts.body);
  const qs = params.toString();
  return `mailto:${encodeURIComponent(to)}${qs ? `?${qs}` : ""}`;
}

export function buildComposeOptions(
  emails: string[],
  field: RecipientField,
  subject: string,
  body: string,
  selfTo?: string
): ComposeOptions {
  const opts: ComposeOptions = { subject, body };
  if (field === "to") opts.to = emails;
  else if (field === "cc") opts.cc = emails;
  else opts.bcc = emails;
  if (selfTo?.trim() && field !== "to") {
    opts.to = [selfTo.trim()];
  }
  return opts;
}

export function openGmailCompose(opts: ComposeOptions) {
  window.open(buildGmailComposeUrl(opts), "_blank", "noopener,noreferrer");
}

export function openMailtoCompose(opts: ComposeOptions) {
  window.location.href = buildMailtoUrl(opts);
}

export function openGmailBatches(
  emails: string[],
  field: RecipientField,
  subject: string,
  body: string,
  selfTo?: string
): number {
  const chunks = chunkEmails(emails);
  for (const batch of chunks) {
    openGmailCompose(buildComposeOptions(batch, field, subject, body, selfTo));
  }
  return chunks.length;
}
