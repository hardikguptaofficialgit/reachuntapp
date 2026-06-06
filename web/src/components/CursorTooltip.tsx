import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type TooltipState = {
  text: string;
  x: number;
  y: number;
};

const LINKIT_URL = "https://linkitapp.in";
const BACKGROUND_TOOLTIP = "Right-click to open Linkit";

function tooltipTarget(node: EventTarget | null): HTMLElement | null {
  if (!(node instanceof Element)) return null;
  const match = node.closest("[data-cursor-tooltip], [title]");
  return match instanceof HTMLElement ? match : null;
}

function targetText(el: HTMLElement): string {
  const custom = el.getAttribute("data-cursor-tooltip")?.trim();
  if (custom) return custom;
  const stored = el.getAttribute("data-original-title")?.trim();
  if (stored) return stored;
  const title = el.getAttribute("title")?.trim();
  if (title) {
    el.setAttribute("data-original-title", title);
    el.removeAttribute("title");
  }
  return title || "";
}

function isInsideMainContainer(node: EventTarget | null): boolean {
  return node instanceof Element && Boolean(node.closest(".shell"));
}

function isOutsideAppBackground(node: EventTarget | null): boolean {
  if (!(node instanceof Element)) return false;
  if (node.closest(".shell, .support-dock, .cursor-tooltip, .toast-stack")) return false;
  return true;
}

export function CursorTooltip() {
  const [tip, setTip] = useState<TooltipState | null>(null);
  const [active, setActive] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const show = (el: HTMLElement, e: PointerEvent) => {
      const text = targetText(el);
      if (!text) return;
      setActive(el);
      setTip({ text, x: e.clientX, y: e.clientY });
    };

    const onPointerOver = (e: PointerEvent) => {
      const el = tooltipTarget(e.target);
      if (el) show(el, e);
    };

    const onPointerMove = (e: PointerEvent) => {
      const el = tooltipTarget(e.target);
      if (el) {
        if (el !== active) show(el, e);
        else setTip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : prev));
        return;
      }
      if (isOutsideAppBackground(e.target)) {
        setActive(null);
        setTip({ text: BACKGROUND_TOOLTIP, x: e.clientX, y: e.clientY });
        return;
      }
      if (active && !isInsideMainContainer(e.target)) {
        setTip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : prev));
        return;
      }
      setActive(null);
      setTip(null);
    };

    const onPointerOut = (e: PointerEvent) => {
      if (!active) return;
      const next = e.relatedTarget;
      if (next instanceof Node && active.contains(next)) return;
      if (next instanceof Element && !isInsideMainContainer(next)) return;
      setActive(null);
      setTip(null);
    };

    const onBlur = () => {
      setActive(null);
      setTip(null);
    };

    const openLinkit = () => {
      const opened = window.open(LINKIT_URL, "_blank", "noopener,noreferrer");
      if (opened) opened.opener = null;
    };

    const onContextMenu = (e: MouseEvent) => {
      if (!isOutsideAppBackground(e.target)) return;
      e.preventDefault();
      openLinkit();
    };

    document.addEventListener("pointerover", onPointerOver, true);
    document.addEventListener("pointermove", onPointerMove, true);
    document.addEventListener("pointerout", onPointerOut, true);
    document.addEventListener("contextmenu", onContextMenu, true);
    window.addEventListener("blur", onBlur);
    return () => {
      document.removeEventListener("pointerover", onPointerOver, true);
      document.removeEventListener("pointermove", onPointerMove, true);
      document.removeEventListener("pointerout", onPointerOut, true);
      document.removeEventListener("contextmenu", onContextMenu, true);
      window.removeEventListener("blur", onBlur);
    };
  }, [active]);

  if (!tip) return null;

  const style = {
    "--tooltip-x": `${tip.x}px`,
    "--tooltip-y": `${tip.y}px`,
  } as CSSProperties;

  return (
    <div className="cursor-tooltip" style={style} role="status" aria-live="polite">
      {tip.text}
    </div>
  );
}
