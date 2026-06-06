const IDLE_MS = 720;

let hideTimer = 0;
let bound = false;

function onScroll() {
  document.documentElement.classList.add("is-scrolling");
  window.clearTimeout(hideTimer);
  hideTimer = window.setTimeout(() => {
    document.documentElement.classList.remove("is-scrolling");
  }, IDLE_MS);
}

/** Shows slim scrollbars while scrolling; fades out after idle. */
export function initScrollbarReveal() {
  if (bound || typeof window === "undefined") return;
  bound = true;
  document.addEventListener("scroll", onScroll, { passive: true, capture: true });
}
