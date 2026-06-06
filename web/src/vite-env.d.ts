/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_UMAMI_WEBSITE_ID?: string;
  readonly VITE_UMAMI_SCRIPT_URL?: string;
  readonly VITE_PLAUSIBLE_DOMAIN?: string;
  readonly VITE_PLAUSIBLE_SCRIPT_URL?: string;
  readonly VITE_GA_MEASUREMENT_ID?: string;
  readonly VITE_ANALYTICS_DISABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface KofiWidget2 {
  init: (text: string, color: string, id: string) => void;
  draw: (containerId?: string) => void;
}

interface KofiWidget2 {
  init: (text: string, color: string, id: string) => void;
  draw: (containerId?: string) => void;
}

interface Window {
  umami?: (event?: string | ((props: Record<string, unknown>) => Record<string, unknown>), data?: Record<string, unknown>) => void;
  kofiwidget2?: KofiWidget2;
}
