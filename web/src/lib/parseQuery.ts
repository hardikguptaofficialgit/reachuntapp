import type { ParseResult } from "../api";

const DOMAIN_RE =
  /^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i;

const COMPANY_HINTS =
  /\b(ai|labs?|inc|llc|ltd|corp|app|tech|hq|health|data|cloud|software|studio|group)\b/i;

const ORG_NAME_HINTS =
  /\b(ventures?|capital|partners?|combinator|holdings|systems|solutions|technologies|software|digital|global|media|health|bank|insurance|university|foundation)\b/i;

const NAME_SEPARATORS = [" - ", " – ", " — ", " | ", ","] as const;

const KNOWN_COMPANY_DOMAINS: Record<string, string> = {
  notion: "notion.so",
  stripe: "stripe.com",
  linkit: "linkitapp.in",
  linkitapp: "linkitapp.in",
  linear: "linear.app",
  vercel: "vercel.com",
  figma: "figma.com",
  openai: "openai.com",
  anthropic: "anthropic.com",
};

const TLDS = [".com", ".so", ".io", ".co", ".in", ".app", ".ai", ".dev"] as const;

function cleanDomain(value: string): string {
  let d = value.trim().replace(/^["'“”‘’]+|["'“”‘’]+$/g, "").toLowerCase();
  d = d.replace(/^https?:\/\//, "").split("/")[0]?.split("?")[0] ?? "";
  if (d.startsWith("www.")) d = d.slice(4);
  return d;
}

function companySlug(label: string): string {
  return label.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function labelFromDomain(domain: string): string {
  const base = domain.split(".")[0] ?? domain;
  return base.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function meaningfulPersonName(name: string): boolean {
  return Boolean(name.trim().replace(/[\s\-–—|,.]+/g, ""));
}

function looksLikePersonName(text: string): boolean {
  const parts = text.trim().split(/\s+/).filter(Boolean);
  if (parts.length < 2 || parts.length > 4) return false;
  if (COMPANY_HINTS.test(text) || ORG_NAME_HINTS.test(text)) return false;
  if (KNOWN_COMPANY_DOMAINS[companySlug(text)]) return false;
  return parts.every((p) => /^[a-zA-Z][a-zA-Z.'-]*$/.test(p));
}

function classifyCompanyInput(raw: string): "company_domain" | "company_name" | null {
  const text = raw.trim();
  if (!text) return null;
  if (looksLikePersonName(text)) return null;

  const lone = cleanDomain(text);
  if (DOMAIN_RE.test(lone) && !text.includes(" ")) return "company_domain";

  const slug = companySlug(text);
  if (!slug) return null;
  if (KNOWN_COMPANY_DOMAINS[slug]) return "company_name";
  if (COMPANY_HINTS.test(text)) return "company_name";
  return null;
}

function domainCandidates(label: string): string[] {
  const cleaned = cleanDomain(label);
  if (DOMAIN_RE.test(cleaned)) return [cleaned];

  const slug = companySlug(label);
  if (!slug) return [];

  const known = KNOWN_COMPANY_DOMAINS[slug];
  const out: string[] = known ? [known] : [];

  for (const tld of TLDS) {
    const candidate = `${slug}${tld}`;
    if (DOMAIN_RE.test(candidate) && !out.includes(candidate)) out.push(candidate);
  }
  return out;
}

function guessPrimaryDomain(label: string): string {
  const slug = companySlug(label);
  if (KNOWN_COMPANY_DOMAINS[slug]) return KNOWN_COMPANY_DOMAINS[slug];
  const candidates = domainCandidates(label);
  if (!candidates.length) {
    throw new Error("Could not infer a company domain from that name.");
  }
  return candidates[0];
}

function okCompany(
  domain: string,
  company_label: string,
  query_kind: "company_domain" | "company_name",
): ParseResult {
  return {
    ok: true,
    name: "",
    domain,
    company_only: true,
    company_label,
    query_kind,
  };
}

/** Parse locally (preview + fallback when API is stale). Mirrors backend rules. */
export function parseQueryLocal(text: string): ParseResult {
  const raw = text.trim().replace(/^["'“”‘’]+|["'“”‘’]+$/g, "");
  if (!raw) {
    return {
      ok: false,
      error: "Enter full name - company domain.",
    };
  }

  for (const sep of NAME_SEPARATORS) {
    const idx = raw.indexOf(sep);
    if (idx === -1) continue;
    const name = raw.slice(0, idx).trim();
    const domain = cleanDomain(raw.slice(idx + sep.length));
    if (meaningfulPersonName(name) && DOMAIN_RE.test(domain)) {
      return {
        ok: true,
        name,
        domain,
        company_only: false,
        query_kind: "person",
      };
    }
    const companyLabel = raw.slice(idx + sep.length).trim();
    if (meaningfulPersonName(name) && companyLabel) {
      try {
        return {
          ok: true,
          name,
          domain: guessPrimaryDomain(companyLabel),
          company_only: false,
          query_kind: "person",
        };
      } catch {
        // Keep parsing so the final error message stays simple.
      }
    }
  }

  if (raw.includes("@")) {
    const [name, dom] = raw.split("@");
    const domain = cleanDomain(dom);
    if (meaningfulPersonName(name) && DOMAIN_RE.test(domain)) {
      return {
        ok: true,
        name: name.trim(),
        domain,
        company_only: false,
        query_kind: "person",
      };
    }
  }

  const parts = raw.split(/\s+/);
  if (parts.length >= 2) {
    const maybe = cleanDomain(parts[parts.length - 1]);
    if (DOMAIN_RE.test(maybe)) {
      const name = parts.slice(0, -1).join(" ").trim();
      if (meaningfulPersonName(name)) {
        return {
          ok: true,
          name,
          domain: maybe,
          company_only: false,
          query_kind: "person",
        };
      }
    }
  }

  const lone = cleanDomain(raw);
  if (DOMAIN_RE.test(lone) && parts.length <= 1) {
    return okCompany(lone, labelFromDomain(lone), "company_domain");
  }

  if (looksLikePersonName(raw)) {
    return {
      ok: false,
      error: "Add their company domain, like Arushi Gupta - notion.so.",
    };
  }

  const kind = classifyCompanyInput(raw);
  if (!kind) {
    return {
      ok: false,
      error: "Use full name - company domain, or enter a company domain.",
    };
  }

  try {
    const domain = guessPrimaryDomain(raw);
    const company_label = kind === "company_name" ? raw : labelFromDomain(domain);
    return okCompany(domain, company_label, kind);
  } catch {
    return { ok: false, error: "Could not infer a company domain from that name." };
  }
}
