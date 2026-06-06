import { useState } from "react";
import { getTheme, toggleTheme, type Theme } from "../theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => getTheme());

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setTheme(toggleTheme())}
      aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
      title={theme === "light" ? "Dark mode" : "Light mode"}
    >
      <span className="theme-toggle__icon" aria-hidden>
        {theme === "light" ? "◐" : "◑"}
      </span>
    </button>
  );
}
