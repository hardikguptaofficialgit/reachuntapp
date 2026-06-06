import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ToastVibe = "default" | "hit" | "wild";

type Toast = { id: number; text: string; vibe: ToastVibe };

type ToastCtx = {
  push: (text: string, vibe?: ToastVibe) => void;
};

const ToastContext = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const push = useCallback((text: string, vibe: ToastVibe = "default") => {
    const id = Date.now();
    setItems((prev) => [...prev, { id, text, vibe }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 2400);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((t) => (
          <div
            key={t.id}
            className={`toast${t.vibe === "hit" ? " toast--hit" : ""}${t.vibe === "wild" ? " toast--wild" : ""}`}
          >
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast requires ToastProvider");
  return ctx;
}
