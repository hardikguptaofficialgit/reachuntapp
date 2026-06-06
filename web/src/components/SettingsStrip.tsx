import type { AppSettings } from "../hooks/useSettings";
import type { SearchMode } from "./SearchForm";

type Props = {
  settings: AppSettings;
  onChange: (patch: Partial<AppSettings>) => void;
};

export function SettingsStrip({ settings, onChange }: Props) {
  return (
    <div className="settings">
      <p className="settings__section-label">Preferences</p>
      <label className="settings__row">
        <span>Notify when done</span>
        <input
          type="checkbox"
          checked={settings.notifyOnComplete}
          onChange={(e) => onChange({ notifyOnComplete: e.target.checked })}
        />
      </label>
      <label className="settings__row">
        <span>Default input</span>
        <select
          className="settings__select"
          value={settings.defaultMode}
          onChange={(e) => onChange({ defaultMode: e.target.value as SearchMode })}
        >
          <option value="quick">Quick</option>
          <option value="split">Split</option>
        </select>
      </label>
      <p className="settings__section-label">Email drafts</p>
      <label className="settings__row settings__row--stack">
        <span>Default subject</span>
        <input
          className="settings__input"
          value={settings.mailSubject}
          onChange={(e) => onChange({ mailSubject: e.target.value })}
          placeholder="Intro — {{name}}"
        />
      </label>
      <label className="settings__row settings__row--stack">
        <span>Default body</span>
        <textarea
          className="settings__textarea"
          rows={3}
          value={settings.mailBody}
          onChange={(e) => onChange({ mailBody: e.target.value })}
        />
      </label>
      <label className="settings__row">
        <span>Bulk recipients</span>
        <select
          className="settings__select"
          value={settings.mailMode}
          onChange={(e) =>
            onChange({ mailMode: e.target.value as AppSettings["mailMode"] })
          }
        >
          <option value="bcc">BCC</option>
          <option value="to">To</option>
          <option value="cc">CC</option>
        </select>
      </label>
    </div>
  );
}
