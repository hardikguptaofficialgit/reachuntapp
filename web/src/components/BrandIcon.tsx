import { useEffect, useMemo, useState } from "react";
import { brandIconUrl, searchSvglIcon, svglRouteForDomain } from "../lib/svgl";
import { getTheme, type Theme } from "../theme";
import { faviconUrl } from "../utils/domain";

type Props = {
  domain?: string;
  toolId?: string;
  size?: number;
  className?: string;
};

export function BrandIcon({ domain, toolId, size = 16, className = "" }: Props) {
  const [theme, setTheme] = useState<Theme>(() => getTheme());
  const [fallback, setFallback] = useState(false);
  const [resolved, setResolved] = useState<string | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const sync = () =>
      setTheme(root.getAttribute("data-theme") === "dark" ? "dark" : "light");
    const obs = new MutationObserver(sync);
    obs.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  const staticSrc = useMemo(
    () => brandIconUrl({ domain, toolId, theme }),
    [domain, toolId, theme],
  );

  useEffect(() => {
    setFallback(false);
    setResolved(staticSrc);
    if (staticSrc || toolId || !domain) return;

    const base = domain.split(".")[0]?.replace(/^www\./, "") ?? "";
    if (svglRouteForDomain(domain)) return;

    let cancelled = false;
    void searchSvglIcon(base, theme).then((url) => {
      if (!cancelled && url) setResolved(url);
    });
    return () => {
      cancelled = true;
    };
  }, [domain, toolId, theme, staticSrc]);

  const src =
    fallback && domain
      ? faviconUrl(domain)
      : resolved ?? (domain ? faviconUrl(domain) : null);

  if (!src) return null;

  return (
    <img
      className={`brand-icon${className ? ` ${className}` : ""}`}
      src={src}
      alt=""
      width={size}
      height={size}
      decoding="async"
      onError={() => {
        if (domain && !fallback) setFallback(true);
      }}
    />
  );
}
