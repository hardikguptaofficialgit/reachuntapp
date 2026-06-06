import { CoffeeIcon } from "./icons/CoffeeIcon";
import { XIcon } from "./icons/XIcon";

const X_URL = "https://x.com/stryker_inside";
const KOFI_URL = "https://ko-fi.com/I6E220P89N";

export function SupportDock() {
  return (
    <aside className="support-dock" aria-label="Support and social">
      <a
        className="support-dock__x"
        href={X_URL}
        target="_blank"
        rel="noopener noreferrer"
        title="@stryker_inside on X"
        aria-label="Follow @stryker_inside on X"
      >
        <XIcon />
      </a>
      <div className="support-dock__kofi-shell">
        <span className="support-dock__kofi-orbit support-dock__kofi-orbit--outer" aria-hidden />
        <span className="support-dock__kofi-orbit support-dock__kofi-orbit--inner" aria-hidden />
        <a
          className="support-dock__kofi"
          href={KOFI_URL}
          target="_blank"
          rel="noopener noreferrer"
          title="Buy me a coffee on Ko-fi"
          aria-label="Buy me a coffee on Ko-fi"
        >
          <CoffeeIcon />
          <span className="support-dock__kofi-label">Buy me a coffee</span>
        </a>
      </div>
    </aside>
  );
}
