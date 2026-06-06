export function faviconUrl(domain: string): string {
  const d = domain.replace(/^https?:\/\//, "").split("/")[0].replace(/^www\./, "");
  if (!d) return "";
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=32`;
}
