import { useEffect, useRef } from "react";
import { trackPageView, trackScreen } from "../lib/analytics";

/** Initial pageview once, then screen_view on tab/auth changes. */
export function useAnalyticsPage(screen: string) {
  const booted = useRef(false);

  useEffect(() => {
    if (!booted.current) {
      booted.current = true;
      trackPageView("/");
    }
    trackScreen(screen);
  }, [screen]);
}
