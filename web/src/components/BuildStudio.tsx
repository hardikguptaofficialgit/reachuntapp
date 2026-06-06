import { useCallback, useEffect, useState } from "react";
import {
  fetchBuildPrompt,
  fetchBuildPromptQuota,
  fetchBuildPromptTypes,
  type BuildPromptQuota,
  type BuildPromptType,
  type BuildContext,
} from "../api";
import { BUILD_TOOLS, openBuildTool } from "../lib/buildTools";
import { useToast } from "../context/ToastContext";
import { BrandIcon } from "./BrandIcon";

type Props = {
  context: BuildContext | null;
  defaultQuery?: string;
  onContextChange?: (ctx: Partial<BuildContext>) => void;
};

export function BuildStudio({ context, defaultQuery = "", onContextChange }: Props) {
  const { push } = useToast();
  const [query, setQuery] = useState(
    defaultQuery ||
      (context ? `${context.founderName || ""} — ${context.domain}`.replace(/^ — /, "") : "")
  );
  const [types, setTypes] = useState<BuildPromptType[]>([]);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [quota, setQuota] = useState<BuildPromptQuota | null>(null);
  const [promptType, setPromptType] = useState("landing");
  const [prompt, setPrompt] = useState("");
  const [promptSource, setPromptSource] = useState<"ai" | "template" | null>(null);
  const [meta, setMeta] = useState<{ company: string; domain: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshQuota = useCallback(() => {
    void fetchBuildPromptQuota().then(setQuota).catch(() => setQuota(null));
  }, []);

  useEffect(() => {
    void fetchBuildPromptTypes()
      .then(({ types: t, ai_enabled }) => {
        setTypes(t);
        setAiEnabled(ai_enabled);
      })
      .catch(() => setTypes([]));
    refreshQuota();
  }, [refreshQuota]);

  useEffect(() => {
    if (context?.domain) {
      setQuery(
        context.founderName
          ? `${context.founderName} — ${context.domain}`
          : context.domain
      );
    }
  }, [context]);

  const canGenerate =
    query.trim().length > 0 &&
    !loading &&
    (quota?.unlimited || !aiEnabled || (quota?.remaining ?? 0) > 0);

  const generate = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    if (aiEnabled && quota && !quota.unlimited && quota.remaining <= 0) {
      push(`Daily limit reached (${quota.limit} AI prompts per day).`);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchBuildPrompt({
        query: q,
        promptType,
        founderName: context?.founderName ?? "",
        founderEmail: context?.founderEmail ?? "",
      });
      setPrompt(res.prompt);
      setPromptSource(res.source ?? "template");
      setMeta({ company: res.company, domain: res.domain });
      if (res.quota) setQuota(res.quota);
      else refreshQuota();
      onContextChange?.({
        company: res.company,
        domain: res.domain,
        founderName: res.founder_name,
      });
      if (res.source === "ai") {
        push("AI prompt ready");
      }
    } catch (err) {
      push(err instanceof Error ? err.message : "Could not generate prompt.");
    } finally {
      setLoading(false);
    }
  }, [
    query,
    promptType,
    context,
    push,
    onContextChange,
    aiEnabled,
    quota,
    refreshQuota,
  ]);

  const copyPrompt = async () => {
    if (!prompt) return;
    await navigator.clipboard.writeText(prompt);
    push("Prompt copied");
  };

  const launch = async (tool: (typeof BUILD_TOOLS)[0]) => {
    if (!prompt) {
      push("Generate a prompt first");
      return;
    }
    await navigator.clipboard.writeText(prompt);
    const url = openBuildTool(tool, prompt);
    window.open(url, "_blank", "noopener,noreferrer");
    push(`Copied · opening ${tool.name}`);
  };

  const quotaLabel = quota
    ? quota.unlimited
      ? "Unlimited AI prompts (dev)"
      : aiEnabled
        ? `${quota.remaining} of ${quota.limit} AI prompts left today`
        : "AI prompts unavailable — add GROQ_API_KEY on server"
    : null;

  return (
    <section className="build">
      {meta?.company && (
        <p className="build__intro">
          Target: <strong>{meta.company}</strong> — paste the prompt into Lovable, v0, or Bolt.
        </p>
      )}

      {quotaLabel && <p className="build__quota">{quotaLabel}</p>}

      <div className="command__field build__query">
        <input
          className="command__input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Name — company.com or company name"
          aria-label="Company for build prompt"
        />
        <button
          type="button"
          className="glass-btn glass-btn--primary command__go"
          disabled={!canGenerate}
          onClick={() => void generate()}
        >
          {loading ? "···" : "Gen"}
        </button>
      </div>

      {meta && (
        <p className="build__meta">
          <BrandIcon domain={meta.domain} size={14} className="parse__icon" />
          <span>{meta.company}</span>
          <span className="parse__dot">·</span>
          <span>{meta.domain}</span>
        </p>
      )}

      <div className="build__types">
        {types.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`build__type${promptType === t.id ? " build__type--on" : ""}`}
            onClick={() => setPromptType(t.id)}
            title={t.hint}
          >
            {t.label}
          </button>
        ))}
      </div>

      {prompt && (
        <>
          {promptSource === "ai" && (
            <p className="build__badge">AI-generated · formatted for Lovable / v0 / Bolt</p>
          )}

          <div className="build__prompt-wrap">
            <textarea
              className="build__prompt"
              readOnly
              value={prompt}
              rows={14}
              aria-label="Generated build prompt"
            />
          </div>

          <div className="build__actions">
            <button
              type="button"
              className="glass-btn glass-btn--primary build__copy"
              onClick={() => void copyPrompt()}
            >
              Copy prompt
            </button>
          </div>

          <p className="build__tools-label">Open in builder</p>
          <div className="build__tools">
            {BUILD_TOOLS.map((tool) => (
              <button
                key={tool.id}
                type="button"
                className="build__tool"
                onClick={() => void launch(tool)}
              >
                <span className="build__tool-head">
                  <BrandIcon toolId={tool.id} size={22} />
                  <span className="build__tool-name">{tool.name}</span>
                </span>
                <span className="build__tool-action">Copy + open →</span>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
