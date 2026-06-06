import { useCallback, useEffect, useState } from "react";
import { updateAccount, type UserAccount } from "../api";
import type { AppSettings } from "../hooks/useSettings";
import { requestNotifyPermission } from "../hooks/useSettings";
import type { SearchMode } from "./SearchForm";
import { UserAvatar } from "./UserAvatar";
import { AVATAR_STYLE_OPTIONS } from "../lib/avatarStyles";
import { dicebearUrl, randomAvatarSeed } from "../lib/dicebear";

type Props = {
  open: boolean;
  account: UserAccount;
  avatarStyles?: string[];
  settings: AppSettings;
  onSettingsChange: (patch: Partial<AppSettings>) => void;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onLogout: () => void | Promise<void>;
  savingDisabled?: boolean;
};

export function AccountSettingsModal({
  open,
  account,
  avatarStyles,
  settings,
  onSettingsChange,
  onClose,
  onSaved,
  onLogout,
  savingDisabled,
}: Props) {
  const [displayName, setDisplayName] = useState(account.display_name);
  const [avatarStyle, setAvatarStyle] = useState(account.avatar_style);
  const [avatarSeed, setAvatarSeed] = useState(account.avatar_seed);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setDisplayName(account.display_name);
    setAvatarStyle(account.avatar_style);
    setAvatarSeed(account.avatar_seed);
    setError(null);
  }, [open, account]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const styleOptions =
    avatarStyles && avatarStyles.length > 0
      ? AVATAR_STYLE_OPTIONS.filter((s) => avatarStyles.includes(s.id))
      : AVATAR_STYLE_OPTIONS;

  const handleSave = useCallback(async () => {
    if (savingDisabled) {
      onClose();
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateAccount({
        display_name: displayName.trim() || account.display_name,
        avatar_style: avatarStyle,
        avatar_seed: avatarSeed,
      });
      await onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save account.");
    } finally {
      setSaving(false);
    }
  }, [
    savingDisabled,
    displayName,
    avatarStyle,
    avatarSeed,
    account.display_name,
    onSaved,
    onClose,
  ]);

  if (!open) return null;

  return (
    <div
      className="account-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="account-sheet"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="account-sheet-title"
        aria-modal="true"
      >
        <header className="account-sheet__profile">
          <UserAvatar
            style={avatarStyle}
            seed={avatarSeed}
            size={64}
            className="user-avatar--lg"
          />
          <div className="account-sheet__who">
            <h2 id="account-sheet-title" className="account-sheet__name">
              {displayName || account.email}
            </h2>
            <p className="account-sheet__email">{account.email}</p>
            {account.linkit_uid ? (
              <span className="account-sheet__badge">Linkit</span>
            ) : null}
          </div>
        </header>

        <div className="account-sheet__main">
          <label className="account-sheet__field">
            <span className="account-sheet__label">Display name</span>
            <input
              className="account-sheet__input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={80}
              autoComplete="nickname"
            />
          </label>

          <div className="account-sheet__field">
            <div className="account-sheet__field-head">
              <span className="account-sheet__label">Avatar</span>
              <button
                type="button"
                className="account-sheet__text-btn"
                onClick={() => setAvatarSeed(randomAvatarSeed())}
              >
                Randomize
              </button>
            </div>
            <div className="account-avatars" role="listbox" aria-label="Avatar style">
              {styleOptions.map((opt) => {
                const selected = opt.id === avatarStyle;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    aria-label={opt.label}
                    className={`account-avatars__btn${selected ? " account-avatars__btn--on" : ""}`}
                    title={opt.label}
                    onClick={() => setAvatarStyle(opt.id)}
                  >
                    <img
                      src={dicebearUrl(opt.id, avatarSeed, 72)}
                      alt=""
                      width={44}
                      height={44}
                    />
                  </button>
                );
              })}
            </div>
            <p className="account-sheet__avatar-hint">
              {styleOptions.find((s) => s.id === avatarStyle)?.label ?? "Style"}
            </p>
          </div>

          <div className="account-sheet__divider" />

          <p className="account-sheet__label account-sheet__label--block">Preferences</p>
          <div className="account-sheet__prefs">
            <label className="account-sheet__pref">
              <span>Notify when done</span>
              <input
                type="checkbox"
                checked={settings.notifyOnComplete}
                onChange={(e) => {
                  if (e.target.checked) requestNotifyPermission();
                  onSettingsChange({ notifyOnComplete: e.target.checked });
                }}
              />
            </label>
            <label className="account-sheet__pref">
              <span>Default input</span>
              <select
                className="account-sheet__select"
                value={settings.defaultMode}
                onChange={(e) =>
                  onSettingsChange({ defaultMode: e.target.value as SearchMode })
                }
              >
                <option value="quick">Quick</option>
                <option value="split">Split</option>
              </select>
            </label>
          </div>

          {error ? <p className="account-sheet__error">{error}</p> : null}
          {savingDisabled ? (
            <p className="account-sheet__hint">
              Dev bypass — sign in with Linkit to save profile changes.
            </p>
          ) : null}
        </div>

        <footer className="account-sheet__footer">
          <button
            type="button"
            className="account-sheet__text-btn account-sheet__text-btn--muted"
            onClick={() => void onLogout()}
          >
            Sign out
          </button>
          <div className="account-sheet__footer-actions">
            <button type="button" className="account-sheet__text-btn" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="glass-btn glass-btn--sm glass-btn--primary"
              disabled={saving}
              onClick={() => void handleSave()}
            >
              {saving ? "Saving…" : savingDisabled ? "Close" : "Save"}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
