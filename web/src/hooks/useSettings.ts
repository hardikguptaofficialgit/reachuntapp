import { useEffect, useState } from "react";
import type { SearchMode } from "../components/SearchForm";
import type { RecipientField } from "../lib/mailCompose";

export interface AppSettings {
  notifyOnComplete: boolean;
  defaultMode: SearchMode;
  mailSubject: string;
  mailBody: string;
  mailMode: RecipientField;
  mailSelfTo: string;
}

const KEY = "fe-settings";

const DEFAULTS: AppSettings = {
  notifyOnComplete: false,
  defaultMode: "quick",
  mailSubject: "",
  mailBody: "Hi {{name}},\n\n",
  mailMode: "bcc",
  mailSelfTo: "",
};

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      ...DEFAULTS,
      notifyOnComplete: Boolean(parsed.notifyOnComplete),
      defaultMode:
        parsed.defaultMode === "split" || parsed.defaultMode === "quick"
          ? parsed.defaultMode
          : DEFAULTS.defaultMode,
      mailSubject: typeof parsed.mailSubject === "string" ? parsed.mailSubject : DEFAULTS.mailSubject,
      mailBody: typeof parsed.mailBody === "string" ? parsed.mailBody : DEFAULTS.mailBody,
      mailMode:
        parsed.mailMode === "to" || parsed.mailMode === "cc" || parsed.mailMode === "bcc"
          ? parsed.mailMode
          : DEFAULTS.mailMode,
      mailSelfTo: typeof parsed.mailSelfTo === "string" ? parsed.mailSelfTo : DEFAULTS.mailSelfTo,
    };
  } catch {
    return DEFAULTS;
  }
}

export function saveSettings(next: AppSettings) {
  localStorage.setItem(KEY, JSON.stringify(next));
}

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(() => loadSettings());

  const update = (patch: Partial<AppSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveSettings(next);
      return next;
    });
  };

  return { settings, update };
}

export function notifyComplete(query: string, email: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  const body = email ? email : "No email found";
  new Notification("Lookup complete", { body: `${query}\n${body}`, silent: true });
}

export function requestNotifyPermission() {
  if ("Notification" in window && Notification.permission === "default") {
    void Notification.requestPermission();
  }
}

export function useNotifyPermission() {
  useEffect(() => {
    requestNotifyPermission();
  }, []);
}
