import { useMemo, useState } from "react";
import type { AppSettings } from "../hooks/useSettings";
import {
  buildComposeOptions,
  fillTemplate,
  openGmailCompose,
  openMailtoCompose,
} from "../lib/mailCompose";
import { GmailIcon } from "./icons/GmailIcon";
import { MailIcon } from "./icons/MailIcon";

type Props = {
  email: string;
  name?: string;
  query?: string;
  domain?: string;
  settings?: Pick<AppSettings, "mailSubject" | "mailBody">;
};

export function ComposeMailActions({ email, name, query, domain, settings }: Props) {
  const [subject, setSubject] = useState(settings?.mailSubject ?? "");
  const [body, setBody] = useState(settings?.mailBody ?? "");
  const [open, setOpen] = useState(false);

  const filled = useMemo(
    () => ({
      subject: fillTemplate(subject, { name, email, query, domain }),
      body: fillTemplate(body, { name, email, query, domain }),
    }),
    [subject, body, name, email, query, domain]
  );

  const sendGmail = () => {
    openGmailCompose(
      buildComposeOptions([email], "to", filled.subject, filled.body)
    );
  };

  const sendMailto = () => {
    openMailtoCompose(
      buildComposeOptions([email], "to", filled.subject, filled.body)
    );
  };

  return (
    <div className="compose compose--single">
      <div className="compose__quick">
        <button
          type="button"
          className="glass-btn glass-btn--sm compose__btn compose__btn--gmail"
          onClick={sendGmail}
          title="Open Gmail compose"
        >
          <GmailIcon size={16} />
          <span>Gmail</span>
        </button>
        <button
          type="button"
          className="glass-btn glass-btn--sm compose__btn"
          onClick={sendMailto}
          title="Open default mail app"
        >
          <MailIcon size={16} />
          <span>Mail</span>
        </button>
        <button
          type="button"
          className="glass-btn glass-btn--sm compose__btn compose__btn--ghost"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Hide" : "Edit draft"}
        </button>
      </div>
      {open && (
        <div className="compose__draft glass-surface">
          <label className="compose__label">
            Subject
            <input
              className="compose__input"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Quick intro — {{name}}"
            />
          </label>
          <label className="compose__label">
            Body
            <textarea
              className="compose__textarea"
              rows={4}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder={"Hi {{name}},\n\nI noticed your work at {{domain}}…"}
            />
          </label>
          <p className="compose__hint">
            Tags: {"{{name}}"} · {"{{email}}"} · {"{{domain}}"} · {"{{query}}"}
          </p>
        </div>
      )}
    </div>
  );
}
