/** DiceBear 7.x avatar URLs (no API key). */
export function dicebearUrl(style: string, seed: string, size = 96): string {
  const params = new URLSearchParams({
    seed: seed || "founder",
    size: String(size),
    backgroundColor: "e8e8e8,1a1a1a",
  });
  return `https://api.dicebear.com/7.x/${encodeURIComponent(style)}/svg?${params}`;
}

export function randomAvatarSeed(): string {
  return `fe-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
