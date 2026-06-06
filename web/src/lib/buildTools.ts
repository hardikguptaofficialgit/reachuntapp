export type BuildTool = {
  id: string;
  name: string;
  url: string;
  /** If set, append encoded prompt as query param when opening */
  promptParam?: "q" | "prompt";
};

export const BUILD_TOOLS: BuildTool[] = [
  { id: "lovable", name: "Lovable", url: "https://lovable.dev/" },
  { id: "v0", name: "v0", url: "https://v0.dev/chat", promptParam: "q" },
  { id: "bolt", name: "Bolt", url: "https://bolt.new/", promptParam: "prompt" },
  { id: "replit", name: "Replit", url: "https://replit.com/ai" },
  { id: "cursor", name: "Cursor", url: "https://cursor.com/" },
];

export function openBuildTool(tool: BuildTool, prompt: string): string {
  if (!tool.promptParam || !prompt.trim()) {
    return tool.url;
  }
  const sep = tool.url.includes("?") ? "&" : "?";
  return `${tool.url}${sep}${tool.promptParam}=${encodeURIComponent(prompt)}`;
}
