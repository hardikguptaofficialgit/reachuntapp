import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { UserAvatar } from "./UserAvatar";
import type { UserAccount } from "../api";

type Props = {
  account: UserAccount;
  focusOn: boolean;
  onOpenPalette: () => void;
  onToggleFocus: () => void;
  onOpenAccount: () => void;
};

export function ShellBar({
  account,
  focusOn,
  onOpenPalette,
  onToggleFocus,
  onOpenAccount,
}: Props) {
  const label = account.display_name || account.email.split("@")[0];

  return (
    <header className="bar">
      <Logo size={28} />
      <div className="bar__end">
        <button
          type="button"
          className={`glass-btn glass-btn--sm icon-btn--text${focusOn ? " icon-btn--on" : ""}`}
          onClick={onToggleFocus}
          title="Focus mode"
        >
          Focus
        </button>
        <button type="button" className="glass-btn glass-btn--sm icon-btn--text" onClick={onOpenPalette}>
          Ctrl K
        </button>
        <button
          type="button"
          className="bar__account"
          onClick={onOpenAccount}
          title={`${label} - Account settings`}
          aria-label="Account settings"
        >
          <UserAvatar style={account.avatar_style} seed={account.avatar_seed} size={32} />
          <span className="bar__account-name">{label}</span>
        </button>
        <ThemeToggle />
      </div>
    </header>
  );
}
