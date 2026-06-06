import { useRef, useState, type FormEvent } from "react";
import { useRotatingText } from "../hooks/useRotatingText";
import { PLACEHOLDER_LINES } from "../utils/smartCopy";
import { SpinExamples } from "./SpinExamples";
import type { ParseResult } from "../api";
import { useParsePreview } from "../hooks/useParsePreview";
import { useDuplicateCheck } from "../hooks/useDuplicateCheck";
import { BrandIcon } from "./BrandIcon";

const EXAMPLES: { query: string; domain?: string }[] = [
  { query: "Hardik Gupta — linkitapp.in", domain: "linkitapp.in" },
  { query: "linkitapp.in", domain: "linkitapp.in" },
  { query: "Stripe", domain: "stripe.com" },
  { query: "Notion", domain: "notion.so" },
  { query: "notion.so", domain: "notion.so" },
];

export type SearchMode = "quick" | "split";

type Props = {
  value: string;
  name: string;
  domain: string;
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
  onChange: (value: string) => void;
  onNameChange: (name: string) => void;
  onDomainChange: (domain: string) => void;
  onSubmit: () => void;
  busy: boolean;
  disabled?: boolean;
  inputRef?: React.RefObject<HTMLInputElement | null>;
  suggestions?: string[];
  onMultiPaste?: (text: string) => void;
};

export function SearchForm({
  value,
  name,
  domain,
  mode,
  onModeChange,
  onChange,
  onNameChange,
  onDomainChange,
  onSubmit,
  busy,
  disabled,
  inputRef,
  suggestions = [],
  onMultiPaste,
}: Props) {
  const localRef = useRef<HTMLInputElement>(null);
  const ref = inputRef ?? localRef;
  const { preview, previewQuery } = useParsePreview(mode, value, name, domain);
  const duplicate = useDuplicateCheck(previewQuery);
  const [goLaunch, setGoLaunch] = useState(false);
  const placeholder = useRotatingText(PLACEHOLDER_LINES, 3400, mode === "quick" && !busy);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setGoLaunch(true);
    window.setTimeout(() => setGoLaunch(false), 420);
    onSubmit();
  };

  const canGo =
    mode === "split"
      ? name.trim().length > 0 && domain.trim().length > 0
      : value.trim().length > 0;

  const parseBlocked = Boolean(previewQuery.trim() && preview && !preview.ok);
  const armed = canGo && !busy && !disabled && !parseBlocked;

  return (
    <form
      className={`command${armed ? " command--armed" : ""}${busy ? " command--hunt" : ""}`}
      onSubmit={handleSubmit}
    >
      <div className="command__toolbar">
        <button
          type="button"
          className={`command__tab${mode === "quick" ? " command__tab--on" : ""}`}
          onClick={() => onModeChange("quick")}
        >
          Quick
        </button>
        <button
          type="button"
          className={`command__tab${mode === "split" ? " command__tab--on" : ""}`}
          onClick={() => onModeChange("split")}
        >
          Split
        </button>
        <span className="command__keys">⌘↵</span>
      </div>

      {mode === "quick" ? (
        <div
          className={`command__field${armed ? " command__field--armed" : ""}${busy ? " command__field--hunt" : ""}`}
        >
          <input
            ref={ref}
            id="lookup-query"
            className="command__input"
            type="text"
            list="query-suggestions"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onPaste={(e) => {
              const pasted = e.clipboardData.getData("text");
              if (pasted.includes("\n") && onMultiPaste) {
                e.preventDefault();
                onMultiPaste(pasted);
              }
            }}
            placeholder={placeholder}
            autoComplete="off"
            spellCheck={false}
            disabled={busy || disabled}
            aria-label="Person name, company name, or company domain"
          />
          {suggestions.length > 0 && (
            <datalist id="query-suggestions">
              {suggestions.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          )}
          {value && !busy && (
            <button
              type="button"
              className="command__clear"
              onClick={() => onChange("")}
              aria-label="Clear"
            >
              ×
            </button>
          )}
          <button
            type="submit"
            className={`glass-btn glass-btn--primary command__go${goLaunch ? " command__go--launch" : ""}`}
            disabled={busy || disabled || !canGo || parseBlocked}
          >
            {busy ? "···" : "Go"}
          </button>
        </div>
      ) : (
        <div
          className={`command__split${armed ? " command__split--armed" : ""}${busy ? " command__split--hunt" : ""}`}
        >
          <input
            className="command__input command__input--split"
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="Full name"
            disabled={busy || disabled}
            aria-label="Full name"
          />
          <span className="command__dash">—</span>
          <input
            className="command__input command__input--split"
            type="text"
            value={domain}
            onChange={(e) => onDomainChange(e.target.value)}
            placeholder="domain.com"
            disabled={busy || disabled}
            aria-label="Company domain"
          />
          <button
            type="submit"
            className={`glass-btn glass-btn--primary command__go command__go--split${goLaunch ? " command__go--launch" : ""}`}
            disabled={busy || disabled || !canGo || parseBlocked}
          >
            {busy ? "···" : "Go"}
          </button>
        </div>
      )}

      <ParsePreview preview={preview} duplicate={duplicate} />

      <div className="examples">
        <SpinExamples
          onPick={(ex) => {
            onModeChange("quick");
            onChange(ex);
            ref.current?.focus();
          }}
        />
        {EXAMPLES.map((ex) => (
          <button
            key={ex.query}
            type="button"
            className="examples__chip"
            disabled={busy || disabled}
            onClick={() => {
              onModeChange("quick");
              onChange(ex.query);
              ref.current?.focus();
            }}
          >
            {ex.domain ? <BrandIcon domain={ex.domain} size={14} /> : null}
            <span>{ex.query.split(" — ")[0]}</span>
          </button>
        ))}
      </div>
    </form>
  );
}

function ParsePreview({
  preview,
  duplicate,
}: {
  preview: ParseResult | null;
  duplicate: boolean;
}) {
  if (duplicate) {
    return <p className="parse parse--warn">Already in your history</p>;
  }
  if (!preview) return null;

  if (!preview.ok) {
    return <p className="parse parse--err">{preview.error}</p>;
  }

  if (preview.company_only) {
    const label = preview.company_label?.trim() || preview.domain;
    return (
      <p className="parse parse--ok">
        <BrandIcon domain={preview.domain} size={14} className="parse__icon" />
        <span>{label}</span>
        <span className="parse__dot">·</span>
        <span>{preview.domain}</span>
      </p>
    );
  }

  return (
    <p className="parse parse--ok">
      <BrandIcon domain={preview.domain} size={14} className="parse__icon" />
      <span>{preview.name}</span>
      <span className="parse__dot">·</span>
      <span>{preview.domain}</span>
    </p>
  );
}
