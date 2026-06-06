import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { SupportDock } from "./components/SupportDock";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import "./index.css";
import "./scrollbars.css";
import "./motion.css";
import "./crazy.css";
import "./glass.css";
import "./compact.css";
import "./safe-ui.css";
import { initAnalytics } from "./lib/analytics";
import { initScrollbarReveal } from "./lib/scrollbarReveal";
import { initTheme } from "./theme";

initTheme();
initScrollbarReveal();
initAnalytics();

createRoot(document.getElementById("root")!).render(
  <AuthProvider>
    <ToastProvider>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
      <SupportDock />
    </ToastProvider>
  </AuthProvider>
);
