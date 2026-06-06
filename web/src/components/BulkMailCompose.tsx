import { useMemo, useState } from "react";
import { useToast } from "../context/ToastContext";
import type { AppSettings } from "../hooks/useSettings";
import {
  type MailRecipient,
  type RecipientField,
  GMAIL_BATCH_SIZE,
  buildComposeOptions,
  chunkEmails,
  fillTemplate,
  openGmailBatches,
  openMailtoCompose,
  uniqueEmails,
} from "../lib/mailCompose";
import { GmailIcon } from "./icons/GmailIcon";
import { MailIcon } from "./icons/MailIcon";

type Props = {
  recipients: MailRecipient[];
  settings?: Pick<AppSettings, "mailSubject" | "mailBody" | "mailMode" | "mailSelfTo">;
  title?: string;
};

const MODES: { id: RecipientField; label: string; hint: string }[] = [
  { id: "bcc", label: "BCC", hint: "Recipients hidden from each other — best for outreach" },
  { id: "to", label: "To", hint: "Everyone sees all addresses" },
  { id: "cc", label: "CC", hint: "Visible copy — use for small groups" },
];

export function BulkMailCompose({ recipients, settings, title = "Send to hits" }: Props) {
  const { push } = useToast();
  const emails = useMemo(() => uniqueEmails(recipients), [recipients]);
  const first = recipients[0];

  const [mode, setMode] = useState<RecipientField>(settings?.mailMode ?? "bcc");
  const [subject, setSubject] = useState(settings?.mailSubject ?? "");
  const [body, setBody] = useState(settings?.mailBody ?? "");
  const [selfTo, setSelfTo] = useState(settings?.mailSelfTo ?? "");
  const [expanded, setExpanded] = useState(true);

  const filled = useMemo(
    () => ({
      subject: fillTemplate(subject, {
        name: first?.name,
        email: first?.email,
        query: first?.query,
      }),
      body: fillTemplate(body, {
        name: first?.name,
        email: first?.email,
        query: first?.query,
      }),
    }),
    [subject, body, first]
  );

  const batches = chunkEmails(emails);
  const batchCount = batches.length;

  if (!emails.length) return null;

  const copyBcc = () => {
    void navigator.clipboard.writeText(emails.join(", "));
    push(`Copied ${emails.length} addresses`);
  };

  const openGmail = () => {
    const n = openGmailBatches(emails, mode, filled.subject, filled.body, selfTo);
    push(n > 1 ? `Opened ${n} Gmail tabs (${GMAIL_BATCH_SIZE}/tab)` : "Opened Gmail");
  };

  const openMailApp = () => {
    if (emails.length > 15) {
      push("Mail app works best under 15 — use Gmail for bulk");
      return;
    }
    openMailtoCompose(
      buildComposeOptions(emails, mode, filled.subject, filled.body, selfTo)
    );
  };

  return (
    <section className="mail-bar glass-surface" aria-label="Bulk email compose">
      <header className="mail-bar__head">
        <div>
          <h3 className="mail-bar__title">{title}</h3>
          <p className="mail-bar__sub">
            {emails.length} recipient{emails.length === 1 ? "" : "s"}
            {batchCount > 1 ? ` · opens ${batchCount} Gmail drafts` : ""}
          </p>
        </div>
        <button
          type="button"
          className="glass-btn glass-btn--sm mail-bar__toggle"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </header>

      {expanded && (
        <>
          <div className="mail-bar__modes" role="group" aria-label="Recipient field">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                className={`mail-bar__mode${mode === m.id ? " mail-bar__mode--on" : ""}`}
                onClick={() => setMode(m.id)}
                title={m.hint}
              >
                {m.label}
              </button>
            ))}
          </div>
          <p className="mail-bar__mode-hint">{MODES.find((m) => m.id === mode)?.hint}</p>

          {mode !== "to" && (
            <label className="compose__label">
              Your email (To — optional)
              <input
                className="compose__input"
                type="email"
                value={selfTo}
                onChange={(e) => setSelfTo(e.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
              />
            </label>
          )}

          <label className="compose__label">
            Subject
            <input
              className="compose__input"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Partnership idea — {{name}}"
            />
          </label>

          <label className="compose__label">
            Body
            <textarea
              className="compose__textarea"
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder={
                "Hi {{name}},\n\nI found your work email and wanted to reach out about…\n\nBest,"
              }
            />
          </label>

          <p className="compose__hint">
            Bulk uses one message for all. First hit fills {"{{name}}"} / {"{{domain}}"} in preview
            only.
          </p>

          <div className="mail-bar__actions">
            <button
              type="button"
              className="glass-btn glass-btn--primary compose__btn compose__btn--gmail"
              onClick={openGmail}
            >
              <GmailIcon size={17} />
              <span>Open in Gmail</span>
            </button>
            <button type="button" className="glass-btn glass-btn--sm compose__btn" onClick={openMailApp}>
              <MailIcon size={16} />
              <span>Mail app</span>
            </button>
            <button type="button" className="glass-btn glass-btn--sm" onClick={copyBcc}>
              Copy {mode.toUpperCase()} list
            </button>
          </div>
        </>
      )}
    </section>
  );
}
